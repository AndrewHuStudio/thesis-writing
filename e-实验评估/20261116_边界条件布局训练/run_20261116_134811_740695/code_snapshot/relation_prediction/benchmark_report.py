"""Write local experiment findings and bounded source and relation review tasks."""
import argparse
import json
from pathlib import Path

import numpy as np


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def percentage(value):
    return f'{100 * value:.2f}%'


def cell(value):
    return str(value).replace('|', '\\|').replace('\n', ' ')


def source_review(output, audit):
    lines = ['# 医院来源分组核对', '',
             '当前分组依据医院名称与源文件哈希。名称相同的医院采用保守合组，'
             '同源关系仍需要结合项目背景确认。', '',
             '| 当前合组 | 依据 | 需要核对的事项 | 你的反馈 |',
             '| --- | --- | --- | --- |']
    for group in audit['groups']:
        if len(group['plans']) > 1:
            plans = '、'.join(group['plans'])
            lines.append(f'| {plans} | 医院名称相同 | 是否属于同院或同源项目，继续合组是否合适 | 待填写 |')
    lines.extend(['', '请补充名称不同但实际同源的样本，例如同一项目的不同命名、裁剪图或衍生图。', '',
                  '| 样本 | 当前来源组 | 分折编号 | 节点数 |', '| --- | --- | --- | --- |'])
    for row in audit['plans']:
        lines.append(f"| {row['plan_id']} | {row['group_id']} | {row['fold']} | {row['nodes']} |")
    (output / '来源分组核对.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def scope_inventory(output, audit):
    lines = ['# 现有功能分区字段清单', '',
             '未来使用条件已确定为建筑边界与空间清单。原始scope字段保留为辅助监督候选，'
             '本轮训练沿用原有50维输入。', '',
             '下表供后续统一标签含义时核查。明确的同义项可由程序提出映射，'
             '方向性名称、未分类项和待确认项需要结合图面解释。', '',
             '| 原始字段 | 节点数 | 涉及图数 | 含不确定标记 |', '| --- | --- | --- | --- |']
    for row in audit['scope_inventory']:
        lines.append(f"| {cell(row['scope_original'])} | {row['nodes']} | {len(row['plans'])} | "
                     f"{'是' if row['contains_uncertainty_marker'] else '否'} |")
    (output / '分区字段清单.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def relation_review(root, output, audit):
    ordered = sorted(audit['plans'], key=lambda row: row['nodes'])
    indexes = np.linspace(0, len(ordered) - 1, 5, dtype=int)
    generator = np.random.default_rng(20261116)
    lines = ['# 空间关系核对清单', '',
             '从不同规模的5张图中选取30对未参与正负监督的空间关系。每张图包含3对留出预测高分候选，'
             '以及3对从其余未参与正负监督空间对中均匀抽取的候选。请按既有access标注口径填写连接、'
             '不连接或无法判断，并简述证据。', '',
             '这批候选用于排查标注缺口和典型错误。高分抽样影响样本分布，后续正式精确率评价'
             '需要预先确定覆盖范围与抽样方式。', '']
    review_records = []
    for index in indexes:
        row = ordered[index]
        plan = row['plan_id']
        path = output / f"fold_{row['fold']}_gcn_seed_7" / (plan + '.npz')
        if not path.exists():
            continue
        sample_path = root / 'p-平面标注与数据处理/训练数据/单层医院_v1/samples' / (plan + '.json')
        source = read_json(sample_path)
        with np.load(path, allow_pickle=False) as predictions:
            scores = predictions['scores']
            pairs = predictions['pairs']
            unlabeled = np.flatnonzero(predictions['labels'] == -1)
            shuffled = generator.permutation(unlabeled)
            ranked = shuffled[np.argsort(-scores[shuffled], kind='stable')]
            high = ranked[:3]
            rest = np.setdiff1d(unlabeled, high)
            random = generator.choice(rest, size=min(3, len(rest)), replace=False)
            choices = [(int(i), '高分候选') for i in high]
            choices.extend((int(i), '随机候选') for i in random)
            annotation = (root / row['source_annotation']).resolve()
            images = sorted(p for p in annotation.parent.iterdir()
                            if p.suffix.lower() in {'.jpg', '.jpeg', '.png'} and '原图' in p.stem)
            lines.extend([f'## {plan}', ''])
            if images:
                lines.extend([f'[查看原图](<{images[0].as_posix()}>)', ''])
            lines.extend(['| 空间甲 | 空间乙 | 抽样方式 | 核对结果 | 依据 |',
                          '| --- | --- | --- | --- | --- |'])
            for pair_index, method in choices:
                left, right = map(int, pairs[pair_index])
                existing = [relation['id'] for relation in source['targets']['relations']
                            if relation['type'] == 'access' and
                            sorted((relation['source_index'], relation['target_index'])) == [left, right]]
                first = source['node_ids'][left] + ' ' + source['metadata'][left]['name']
                second = source['node_ids'][right] + ' ' + source['metadata'][right]['name']
                evidence = '原access记录已屏蔽 ' + '、'.join(existing) if existing else '待填写'
                lines.append(f'| {cell(first)} | {cell(second)} | {method} | 待填写 | {evidence} |')
                review_records.append({'plan_id': plan, 'source': source['node_ids'][left],
                                       'target': source['node_ids'][right], 'sampling_method': method,
                                       'predicted_score_uncalibrated': float(scores[pair_index]),
                                       'existing_masked_access_record_ids': existing,
                                       'review_result': None, 'evidence': None})
            lines.append('')
    (output / '关系核对清单.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    (output / 'relation_review.json').write_text(json.dumps(review_records, ensure_ascii=False, indent=2)
                                                + '\n', encoding='utf-8')
    return len(review_records)


def report(root, output):
    status = read_json(output / 'status.json')
    if status['status'] != 'complete':
        raise ValueError('Only completed comparisons can be reported')
    audit = read_json(output / 'source_audit.json')
    summary = read_json(output / 'summary.json')
    config = read_json(output / 'config.json')
    if not all(row['all_plans_evaluated_once'] for row in summary['per_seed']):
        raise ValueError('Full report requires every plan to have one held-out prediction per model and seed')
    source_review(output, audit)
    scope_inventory(output, audit)
    review_count = relation_review(root, output, audit)
    names = {'frequency': '关系统计', 'mlp': '空间对MLP', 'gcn': '当前GCN'}
    lines = ['# 关系模型分组实验与工作分工', '',
             '已按暂定医院来源分组完成关系模型对照。用户确定未来提供建筑边界与空间清单，'
             '后续模型以这两项作为设计条件。', '',
             f"当前共{len(audit['plans'])}图、{audit['node_count']}个节点，暂分{len(audit['groups'])}个来源组。"
             '医院名称相同及源文件哈希一致的样本合组。来源身份核对后，可用同一入口重新生成分组并复跑。', '',
             f"采用{audit['fold_count']}折轮换，每折使用一折测试、下一折验证，其余折训练。"
             '各折训练、验证与测试来源组互斥。神经网络以验证集按来源组平均的固定预算召回选择权重，'
             '统计先验仅由该折训练数据建立。', '',
             f"本轮完成{status['neural_runs']}次神经网络训练与{status['frequency_folds']}折统计对照。"
             f"最长训练{config['epochs']}轮，隐藏维度{config['hidden']}，学习率{config['learning_rate']}，"
             f"PU比例倍数{config['prior_multiplier']}。连续{config['patience_checks']}次检查未改善后触发早停，"
             '检查间隔10轮，最早在第40轮停止。', '',
             '每张图按空间节点数n保留前n对候选，并列分数按比例分摊。表中按来源组平均，'
             f"神经网络报告{len(config['seeds'])}个随机种子的均值与样本标准差。"
             '指标衡量已标注连接的召回，未知关系保持未标注状态。', '',
             '| 方法 | 固定n候选的召回 | 随机种子波动 | 已标注正例数量预算的诊断召回 |',
             '| --- | --- | --- | --- |']
    for comparison in summary['comparisons']:
        metric = comparison['metrics']['group_macro_recall_at_n']
        diagnostic = comparison['metrics']['group_macro_recall_at_observed_positive_budget']
        deviation = metric['seed_standard_deviation']
        variability = '确定性统计' if comparison['model'] == 'frequency' else '单次运行'
        if deviation is not None:
            variability = f"{100 * deviation:.2f}个百分点"
        lines.append(f"| {names[comparison['model']]} | {percentage(metric['mean'])} | {variability} | "
                     f"{percentage(diagnostic['mean'])} |")
    random_metric = summary['comparisons'][0]['metrics']['group_macro_random_recall_at_n']['mean']
    lines.extend(['', f'相同固定预算下，均匀随机排序的来源组平均召回期望为{percentage(random_metric)}。'])
    lines.extend(['', '这些结果采用暂定来源分组，适用于当前探索性比较。原有14%左右的数值采用全部53图训练、'
                  '逐图平均及已标注正例数量预算，解读时需保留各自的训练与评价口径。', '',
                  '本轮对照沿用50维功能与层级输入。建筑边界的条件编码、多个布局候选生成、'
                  '等价房间匹配和几何约束仍属于后续实现。', '',
                  f"同图内存在相同输入特征的节点为{audit['duplicate_feature_node_count']}个，"
                  f"占{percentage(audit['duplicate_feature_node_fraction'])}。"
                  '对于需求完全相同的房间，后续布局模型需要允许交换实例，并探索多个合理方案。', '',
                  f"现有scope原始字段共{audit['scope_vocabulary_count']}种，已整理到分区字段清单。"
                  '它们可作为辅助监督的候选，统一语义和不确定性掩码后再实验。', '',
                  '| 工作 | 由我完成的内容 | 你需要参与的内容 |', '| --- | --- | --- |',
                  '| 来源分组与评价 | 已建立暂定来源组、分折和完整留出评价 | 核对三组合组，并补充跨名称同源关系 |',
                  '| 对照训练 | 已完成统计、MLP、GCN对照，保存权重、日志与重载校验 | 阅读主要结果即可 |',
                  '| 输入条件 | 已记录建筑边界加空间清单 | 已确认，后续补充特殊需求时再更新 |',
                  '| 关系标签质量 | 已生成可编辑清单，可继续逐图核查并记录依据 | 确认图面核查后仍有疑问的关系 |',
                  '| 分区辅助监督 | 已整理原始字段与不确定标记 | 后续仅需处理程序和图面均无法确认的语义 |',
                  '| 参数和结构实验 | 可继续实现验证集调参、边界条件模型与消融比较 | 对研究目标有变化时说明设计用途 |',
                  '| 布局生成与评价 | 可实现候选生成、等价房间匹配和几何检查 | 对候选方案的设计合理性作专业评价 |', '',
                  f"当前优先核对来源分组与{review_count}对空间关系。关系清单用于错误排查，"
                  '后续正式评价还需预先界定完整核对区域或抽样方案。', '',
                  '[来源分组核对](来源分组核对.md)　[关系核对清单](关系核对清单.md)　'
                  '[分区字段清单](分区字段清单.md)　[原始汇总数据](summary.json)', '',
                  '训练输入的55项文件哈希在运行前后保持一致。每份模型权重已重新加载，'
                  '留出预测分数与保存前完全一致。'])
    (output / '结果与分工.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--project-root', type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    report(args.project_root.resolve(), args.output.resolve())
