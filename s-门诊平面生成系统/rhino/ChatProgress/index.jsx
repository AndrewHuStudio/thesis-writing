import React from 'react';
import { createRoot } from 'react-dom/client';
import { Think, ThoughtChain } from '@ant-design/x';
import { Descriptions } from 'antd';

const bridge = window.chrome.webview;
const root = createRoot(document.getElementById('root'));
const stages = {
  task: '需求分析智能体', gcn: '平面拓扑智能体',
  generation: '平面生成智能体', evaluation: '方案审查智能体',
};
const tools = {
  access_gcn: '连通关系预测', boundary_layout_gcn: '边界布局预测',
  apiyi_layout_advice: '模型拓扑建议', corridor_search: '走廊搜索',
  room_placement: '房间落位', geometry_audit: '几何质检', room_summary: '房间统计',
  route_graph: '路径分析', sight_line: '入口视线分析', flow_overlap: '流线重叠分析',
  read_brief: '读取任务书', draft_program: '拟定空间清单',
};
const states = {
  running: '执行中', completed: '已完成', awaiting_confirmation: '等待确认清单',
  retrying: '质检未通过，重新生成', degraded: '拓扑建议不可用，继续使用本地预测',
  failed: '未通过', abort: '已取消', error: '运行失败',
};
function describe(event) {
  const parts = [states[event.status] || event.status];
  if (event.attempt) parts.push('第 ' + event.attempt + ' 次');
  if (event.tools?.length) parts.push('阶段工具：' + event.tools.map(tool => tools[tool] || tool).join('、'));
  if (event.room_count != null) parts.push(event.room_count + ' 间房');
  if (event.score_count != null) parts.push(event.score_count + ' 个连通评分');
  if (event.unreachable_count != null) parts.push(event.unreachable_count + ' 间入口不可达');
  if (event.reason) parts.push(event.reason);
  if (event.issues) parts.push(...event.issues);
  return parts.join(' · ');
}
const space = id => ({'@entry': '入口', '@corridor': '走廊'}[id] || id);
const pairText = pair => pair.map(space).join(' ↔ ');
function StageOutput({ event }) {
  const rows = [];
  function row(label, children) { rows.push({ key: label, label, children }); }
  if (event.rooms) row('空间清单', event.rooms.map(r => r.id + ' ' + r.name).join('、'));
  for (const [field, label] of [['required', '必须直连'], ['forbidden', '禁止直连'], ['doors', '实际门洞']])
    if (event[field]) row(label, event[field].map(pairText).join('、') || '无');
  if (event.candidates) row('允许连接的 GCN 评分', event.candidates.map(c => pairText(c.pair) + '（' + c.score.toFixed(3) + '）').join('、') || '无候选');
  if (event.routes) {
    if (event.connection_checks?.length) row('直连要求核查', event.connection_checks.map(check =>
      <div key={check.pair.join('|')}>{pairText(check.pair)} · {check.requirement === 'required_connections' ? '必须直连' : '禁止直连'}
        {' · '}{check.door_present ? '有门洞' : '无门洞'} · {check.passed ? '满足' : '未满足'}</div>));
    for (const [key, label] of [['patient_route', '患者路线'], ['staff_route', '医护路线']]) {
      const route = event.routes[key];
      row(label, route.endpoints ? route.endpoints.map(space).join(' → ') + ' · ' +
        (route.status === 'reachable' ? route.length_m.toFixed(1) + ' m' : '不可达') : '未指定起终点');
    }
    row('入口不可达房间', event.unreachable.join('、') || '无');
  }
  return rows.length > 0 && <Descriptions column={1} size="small" items={rows}/>;
}
function Progress({ model }) {
  const nodes = new Map();
  for (const event of model.events) {
    if (!nodes.has(event.stage)) nodes.set(event.stage, []);
    nodes.get(event.stage).push(event);
  }
  const hasToolCall = model.events.some(event => event.tools?.length > 0);
  const items = Array.from(nodes, ([stage, events]) => {
    const last = events.at(-1);
    const status = {completed: 'success', failed: 'error', error: 'error', abort: 'abort'}[last.status];
    const called = [...new Set(events.flatMap(event => event.tools || []))];
    return {
      key: stage, title: stages[stage] || stage, description: [states[last.status], ...called.map(tool => tools[tool] || tool)].filter(Boolean).join(' · '),
      status: status || (last.status === 'awaiting_confirmation' ? undefined : 'loading'),
      collapsible: true, content: <ul className="events">{events.map((event, i) =>
        <li key={i}>{describe(event)}<StageOutput event={event}/></li>)}</ul>,
    };
  });
  const latest = model.events.at(-1);
  const title = model.title || (latest ? stages[latest.stage] + ' · ' + states[latest.status] : '正在处理');
  return <main>
    <Think expanded>
      {model.detail || (latest && describe(latest)) || title}
    </Think>
    {hasToolCall && <div className="chain"><ThoughtChain items={items}/></div>}
  </main>;
}
bridge.addEventListener('message', ({data}) => root.render(<Progress model={data}/>));
new ResizeObserver(([entry]) => bridge.postMessage({height: Math.ceil(entry.contentRect.height)}))
  .observe(document.getElementById('root'));
bridge.postMessage({ready: true});
