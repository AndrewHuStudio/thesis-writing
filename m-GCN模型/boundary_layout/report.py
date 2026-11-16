"""Summarize complete held-out layout results and draw representative comparisons."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon, box
from shapely.ops import unary_union
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from boundary_layout.data import prepare_inputs, ProgramMeanBaseline
from room_layout_pilot.evaluate import boxes


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def plot_comparison(source, baseline, prediction, output):
    inputs = prepare_inputs(source)
    extent = inputs['extent'].numpy()
    valid = np.asarray(source['masks']['layout']) & np.asarray(source['masks']['function'])
    fine = np.asarray(source['masks']['known_single_room']) & valid
    panel_width, margin = 600, 32
    width = panel_width * 3
    factor = (panel_width - margin * 2) / extent[0]
    height = int(extent[1] * factor) + 155
    image = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(image)
    font_path = Path('C:/Windows/Fonts/msyh.ttc')
    font = ImageFont.truetype(str(font_path), 23) if font_path.exists() else ImageFont.load_default(size=23)
    small_font = ImageFont.truetype(str(font_path), 18) if font_path.exists() else ImageFont.load_default(size=18)
    layouts = [('参考标注', None), ('训练来源统计基线', baseline), ('边界条件模型', prediction)]
    for panel, (title, values) in enumerate(layouts):
        panel_left = panel * panel_width
        draw.text((panel_left + margin, 15), title, fill='#172033', font=font)

        def transform(points):
            return [(float(x * factor + panel_left + margin), float((extent[1] - y) * factor + 65)) for x, y in points]

        shapes = []
        bounds = boxes(values) if values is not None else None
        for index in sorted(np.flatnonzero(valid), key=lambda i: bool(fine[i])):
            if values is None:
                points = source['targets']['polygons'][index]
            else:
                x0, y0, x1, y1 = bounds[index]
                points = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]
            color = '#dceafe' if fine[index] else '#f1f3f5'
            draw.polygon(transform(points), fill=color, outline='#6b7e95', width=1)
            if fine[index]:
                shapes.append(Polygon(points))
        if values is not None:
            intersections = []
            for index, first_shape in enumerate(shapes):
                for second_shape in shapes[index + 1:]:
                    intersection = first_shape.intersection(second_shape)
                    if intersection.area > 1e-10:
                        intersections.append(intersection)
            overlap = unary_union(intersections)
            polygons = [overlap] if overlap.geom_type == 'Polygon' else list(getattr(overlap, 'geoms', []))
            for polygon in polygons:
                if polygon.geom_type == 'Polygon':
                    draw.polygon(transform(polygon.exterior.coords), fill='#f9a5a5', outline='#dc6868')
        for part in source['inputs']['boundary']:
            draw.line(transform(part['outer'] + [part['outer'][0]]), fill='#172033', width=3)
            for hole in part.get('holes', []):
                draw.line(transform(hole + [hole[0]]), fill='#172033', width=2)
    draw.text((margin, height - 65), '蓝色为有效单间，灰色为其他有效空间，红色为单间重叠区域。',
              fill='#526071', font=small_font)
    draw.text((margin, height - 35), '同类空间按当前输入编码匹配后显示，当前输出采用矩形近似。',
              fill='#526071', font=small_font)
    image.save(output)


def make_report(root, output):
    status, summary = read_json(output / 'status.json'), read_json(output / 'summary.json')
    config, audit = read_json(output / 'config.json'), read_json(output / 'source_audit.json')
    if status['status'] != 'complete' or not all(r['all_plans_evaluated_once'] for r in summary['per_seed']):
        raise ValueError('A full held-out report requires complete source coverage')
    names = {'boundary_gcn': '边界条件GCN', 'program_mean': '训练来源统计均值'}
    lines = ['# 建筑边界与空间清单条件下的布局测试', '',
             f"已完成53图、{len(audit['groups'])}个暂定来源组的5折留出布局测试。"
             f"边界条件模型使用{len(config['seeds'])}个随机种子，每次最长{config['epochs']}轮，"
             '由验证集目标选择权重。统计对照仅使用每折训练来源中的几何标签。', '',
             '输入为已知建筑边界及50维功能类别、空间层级和功能已知编码。模型根据边界内部随机槽位'
             f"输出每个空间的中心、宽和高。每次生成{config['candidates']}个候选，"
             '按软重叠与越界代价选择，候选选择与参考布局隔离。', '',
             f"本轮共覆盖{summary['total_test_rooms']}个有效且功能明确的单间几何标签，每个随机种子分别评价一次。"
             '房间与其他有效空间分别汇总。表中先按医院来源组平均，再对随机种子取均值。', '',
             '| 方法 | 房间位置误差占建筑长边 | 房间框IoU | 房间轮廓IoU | 房间面积相对误差 | 房间重叠占地 | 房间越界面积 |',
             '| --- | --- | --- | --- | --- | --- | --- |']
    for kind, row in summary['comparisons'].items():
        metrics = row['metrics']
        means = {k: v['mean'] for k, v in metrics.items()}
        lines.append(f"| {names[kind]} | {means['fine_rooms_center_error_pct_long_side']:.2f}% | "
                     f"{means['fine_rooms_box_iou']:.3f} | {means['fine_rooms_polygon_iou']:.3f} | "
                     f"{100 * means['fine_rooms_area_relative_error']:.2f}% | "
                     f"{100 * means['fine_rooms_overlap_area_fraction']:.2f}% | "
                     f"{100 * means['fine_rooms_outside_area_fraction']:.2f}% |")
    lines.extend(['', 'IoU越高表示越接近参考轮廓。其余表内误差和冲突比例越低越好。'
                  '面积真值取原标注多边形，预测采用矩形。重叠区域按面积计一次，分母为预测房间占地并集。', '',
                  '匹配在几何监督有效且50维输入完全相同的空间之间进行，属于当前编码粒度下的实例对应假设。'
                  '房间名称、科室归属、真实位置、真实面积、原图access和门位均作为输入之外的信息处理。'
                  '名称不同但被编码为同一类的空间，仍需在后续语义建模与专业核查中区分。', '',
                  '来源身份分组仍为暂定，参考轮廓为概念图近似。测试给出与参考方案的接近程度和几何冲突情况，'
                  '多个合理方案的设计质量还需要结合功能组织判断。', '',
                  '| 方法 | 其他有效空间位置误差占建筑长边 | 其他有效空间轮廓IoU | 其他有效空间面积相对误差 |',
                  '| --- | --- | --- | --- |'])
    for kind, row in summary['comparisons'].items():
        means = {k: v['mean'] for k, v in row['metrics'].items()}
        lines.append(f"| {names[kind]} | {means['other_valid_spaces_center_error_pct_long_side']:.2f}% | "
                     f"{means['other_valid_spaces_polygon_iou']:.3f} | {100 * means['other_valid_spaces_area_relative_error']:.2f}% |")
    lines.extend(['', '其他有效空间包括功能块、公共空间和按现有掩码保留的组合空间。其面积与位置监督按实际层级使用，'
                  '不对跨层级包含关系统一计算互斥重叠。', '',
                  '已计算标注access端点在生成布局中的矩形几何间隔，逐图结果保存在result.json中。'
                  '原access包含概念联系，端点间隔仅用于诊断。实际门洞、走廊行走路径和交通组织评价仍待后续生成模块。', '',
                  '预测文件保存在各折各随机种子的predictions目录。权重保存在weights.pt，history.json记录训练与验证目标，'
                  'result.json保存逐图、逐空间指标及匹配对应。每份权重已重新加载并核验固定随机种子预测完全一致。', '',
                  '[汇总数值](summary.json)　[实验配置](config.json)', '', '以下每折选取一张有房间监督的图，固定使用首个随机种子展示。', ''])
    pictures = output / 'comparisons'
    pictures.mkdir(exist_ok=True)
    first_seed = config['seeds'][0]
    for fold in range(audit['fold_count']):
        result = read_json(output / f'fold_{fold}_seed_{first_seed}/result.json')
        candidates = [r for r in result['test_rows'] if r['metrics']['fine_rooms_count'] > 0]
        selected = sorted(candidates, key=lambda r: r['plan_id'])[0]
        plan = selected['plan_id']
        source = read_json(root / 'p-平面标注与数据处理/训练数据/单层医院_v1/samples' / (plan + '.json'))
        prediction = read_json(output / f'fold_{fold}_seed_{first_seed}/predictions' / (plan + '.json'))
        aligned = np.asarray(prediction['predicted_boxes'])[selected['prediction_index_for_reference']]
        statistics = read_json(output / f'fold_{fold}_program_mean_statistics.json')
        baseline = ProgramMeanBaseline()
        baseline.default = np.asarray(statistics['default'])
        baseline.means = {tuple(row['features']): np.asarray(row['mean_box_fraction']) for row in statistics['patterns']}
        baseline_boxes = baseline.predict(prepare_inputs(source)).numpy()
        baseline_result = read_json(output / f'fold_{fold}_program_mean_result.json')
        matched_baseline = next(r for r in baseline_result['test_rows'] if r['plan_id'] == plan)
        baseline_boxes = baseline_boxes[matched_baseline['prediction_index_for_reference']]
        filename = f'fold_{fold}.png'
        plot_comparison(source, baseline_boxes, aligned, pictures / filename)
        lines.extend([f'## {plan}', '', f'![参考与预测对照](comparisons/{filename})', ''])
    (output / '布局测试结果.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--project-root', type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    make_report(args.project_root.resolve(), args.output.resolve())
