"""Persist candidate scores and readable training diagnostics."""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def write_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    temporary.replace(path)


def font(size=15):
    for path in ['/System/Library/Fonts/PingFang.ttc',
                 '/System/Library/Fonts/STHeiti Medium.ttc',
                 '/System/Library/Fonts/Hiragino Sans GB.ttc',
                 '/Library/Fonts/Arial Unicode.ttf',
                 '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def curve_image(history, output):
    image = Image.new('RGB', (1000, 530), 'white')
    draw = ImageDraw.Draw(image)
    draw.text((35, 20), '53-plan training | exact macro PU risk + known-negative loss',
              fill='#17212b', font=font(22))
    left, top, right, bottom = 85, 90, 960, 440
    draw.line([(left, top), (left, bottom), (right, bottom)], fill='#334155', width=2)
    maximum = max(row['macro_pu_risk_plus_known_negatives'] for row in history) * 1.05
    epochs = max(row['epoch'] for row in history) or 1
    for i in range(6):
        value = maximum * i / 5
        y = bottom - (bottom - top) * i / 5
        draw.line([(left, y), (right, y)], fill='#e2e8f0')
        draw.text((15, y - 9), f'{value:.3f}', fill='#334155', font=font())
    points = [(left + (right - left) * row['epoch'] / epochs,
               bottom - (bottom - top) * row['macro_pu_risk_plus_known_negatives'] / maximum)
              for row in history]
    if len(points) > 1:
        draw.line(points, fill='#2467a7', width=3)
    for epoch in range(0, epochs + 1, max(1, epochs // 6)):
        x = left + (right - left) * epoch / epochs
        draw.text((x - 10, bottom + 12), str(epoch), fill='#334155', font=font())
    draw.text((85, 490), 'All 53 plans are training data. Scores and recall are training diagnostics.',
              fill='#475569', font=font(17))
    image.save(output)


def comparison_image(sample, scores, output):
    source = json.loads(Path(sample['source_path']).read_text())
    boxes = np.asarray(source['targets']['boxes'])
    image = Image.new('RGB', (1200, 680), 'white')
    draw = ImageDraw.Draw(image)
    draw.text((25, 15), sample['plan_id'], fill='#17212b', font=font(22))
    positive_count = len(sample['positive_pairs'])
    selected = np.argsort(-scores, kind='stable')[:min(positive_count, 160)]
    candidate_pairs = sample['all_pairs'].numpy()[selected]
    labels = sample['pair_labels'][selected]
    xmax = max(1., float((boxes[:, 0] + boxes[:, 2] / 2).max()))
    ymax = max(1., float((boxes[:, 1] + boxes[:, 3] / 2).max()))
    scale = min(510 / xmax, 490 / ymax)
    panels = [(25, sample['positive_pairs'].numpy()[:160], None),
              (625, candidate_pairs, labels)]
    for offset, pairs, reference_labels in panels:
        title = 'Known access labels' if reference_labels is None else 'Highest candidate scores'
        draw.text((offset, 55), title + ' (display limit 160)', fill='#334155', font=font(18))
        centers = [(offset + 15 + scale * x, 580 - scale * y) for x, y, _, _ in boxes]
        for (x, y, width, height), center in zip(boxes, centers):
            cx, cy = center
            draw.rectangle((cx - width * scale / 2, cy - height * scale / 2,
                            cx + width * scale / 2, cy + height * scale / 2),
                           outline='#d5dce5')
        for index, (left, right) in enumerate(pairs):
            color = '#2467a7'
            if reference_labels is not None and reference_labels[index] == -1:
                color = '#d97706'
            if reference_labels is not None and reference_labels[index] == 0:
                color = '#b91c1c'
            draw.line((centers[left], centers[right]), fill=color, width=2)
        for cx, cy in centers:
            draw.ellipse((cx - 2, cy - 2, cx + 2, cy + 2), fill='#334155')
    draw.text((25, 610), 'Reference positions are used only for visualization. Display order within ties is arbitrary.',
              fill='#475569', font=font(17))
    draw.text((25, 642), 'Blue = known access; orange = unlabeled candidate; red = confirmed disconnection.',
              fill='#475569', font=font(17))
    image.save(output)


def save_predictions(output, samples, rows, predictions):
    directory = output / 'predictions'
    figures = output / 'figures'
    directory.mkdir()
    figures.mkdir()
    for sample, row, scores in zip(samples, rows, predictions):
        plan = sample['plan_id']
        pairs = sample['all_pairs'].numpy()
        labels = sample['pair_labels']
        np.savez_compressed(directory / f'{plan}.npz', pairs=pairs,
                            scores=scores, reference_labels=labels,
                            node_ids=np.asarray(sample['node_ids']))
        top = np.argsort(-scores, kind='stable')[:min(500, max(100, 3 * row['known_positives']))]
        candidates = []
        for index in top:
            left, right = pairs[index]
            label = int(labels[index])
            candidates.append({
                'source': sample['node_ids'][left], 'target': sample['node_ids'][right],
                'score_uncalibrated': float(scores[index]),
                'reference_status': {1: 'known_access', 0: 'confirmed_disconnected', -1: 'unlabeled'}[label],
            })
        write_json(directory / f'{plan}.json', {
            'plan_id': plan, 'split': 'train', 'diagnostics': row,
            'all_pair_scores': f'{plan}.npz',
            'tie_order_for_display': 'source_order_only_not_evidence_of_preference',
            'candidates': candidates,
        })
        comparison_image(sample, scores, figures / f'{plan}.png')


def write_report(output, configuration, initial, final, best_epoch, rows, history, checks):
    write_json(output / 'metrics.json', {'initial': initial, 'trained': final, 'plans': rows})
    write_json(output / 'verification.json', checks)
    curve_image(history, output / 'training_curve.png')
    report = f'''# 53图首轮GCN关系预测训练记录

本次以全部{final['plans']}图开展训练，使用{sum(row['nodes'] for row in rows):,}个空间节点、{final['known_positive_pairs']:,}对有效access正例和{final['known_negative_pairs']}对明确不连接记录。模型输出空间对候选分数。

训练种子为{configuration['seed']}，实际完成{configuration['epochs']}轮。以训练集精确宏平均风险选取第{best_epoch}轮权重，各图等权。

## 训练诊断

| 项目 | 初始化模型 | 保存模型 |
| --- | ---: | ---: |
| 宏平均PU风险及明确负例损失 | {initial['macro_pu_risk_plus_known_negatives']:.6f} | {final['macro_pu_risk_plus_known_negatives']:.6f} |
| 按已记录关系数作候选预算的正例召回 | {initial['macro_recall_at_observed_edge_budget']:.2%} | {final['macro_recall_at_observed_edge_budget']:.2%} |

以上数值描述训练集上的拟合与排序。召回预算使用各图已有正例数量，并列分数按比例均摊。实际设计时的候选数量需另行确定。

## 模型与监督

输入为现有50维类别、层级与功能已知标记。消息图由空间清单全连接构成，使用两层残差图卷积及对称空间对解码器。相同输入的节点具有相同表示。

训练采用非负PU风险，每图总体空间对均匀抽样。正类比例假设为该图已记录正例比例的{configuration['prior_multiplier']:g}倍，上限为0.5。该比例和正例代表性需要后续核实，候选分数尚未校准。

全部53图均用于本次训练。训练集排序结果支持流程与拟合诊断，后续泛化评价需要独立设计。尚未确认的候选连接供人工核对。

## 文件入口

- `weights.pt` 保存模型结构、参数和本轮配置。
- `config.json` 保存假设、超参数、环境与输入约定。
- `input_hashes.json` 和 `source_hashes.json` 保存实际数据及原交付物哈希。
- `history.json` 和 `progress.jsonl` 保存精确诊断与逐轮训练进度。
- `predictions/` 保存53份候选JSON及53份全空间对分数NPZ。
- `figures/` 保存53份原位置上的关系对照图，几何坐标仅在绘图时读取。
- `training_curve.png` 为本次训练曲线，`verification.json` 为重新加载和哈希核验结果。
- `code_snapshot/` 保存本次运行代码。

模型采用的GCN与PU风险分别参考以下论文。输入图、残差形式与先验倍数为本项目具体实验选择。

- https://arxiv.org/abs/1609.02907
- https://papers.nips.cc/paper/2017/file/7cce53cf90577442771720a370c3c723-Paper.pdf
'''
    (output / '结果说明.md').write_text(report)
