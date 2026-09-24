/**
 * 数字人调度中心 — 静态导航、快捷指令与数字员工功能预览数据。
 * 实时系统、线索与 CRM 数据统一由 lib/dashboard-api.ts 读取。
 */
import type {
  Agent,
  DepartmentNav,
  QuickCommand,
} from './dashboard-types';

/* ── 侧边栏：4 组 14 模块（路由与现有 app/ 目录一一对应） ─────────── */
export const DASHBOARD_DEPARTMENTS: DepartmentNav[] = [
  {
    key: 'growth',
    title: '增长中心',
    modules: [
      { id: 'optimize', label: '内容工场', href: '/optimize', iconKey: 'pen', tint: 'growth' },
      { id: 'geo', label: '全域洞察', href: '/geo', iconKey: 'radar', tint: 'growth' },
      { id: 'marketing', label: '投放参谋', href: '/marketing', iconKey: 'target', tint: 'growth' },
    ],
  },
  {
    key: 'revenue',
    title: '营收中心',
    modules: [
      { id: 'digital-human', label: '数字人直播', href: '/digital-human', iconKey: 'mic', tint: 'revenue' },
      { id: 'service', label: '智能接待', href: '/service/sessions', iconKey: 'message', tint: 'revenue' },
      { id: 'leads', label: '本地线索池', href: '/leads', iconKey: 'briefcase', tint: 'revenue' },
      { id: 'service-stats', label: '服务质检', href: '/service/stats', iconKey: 'activity', tint: 'revenue' },
      { id: 'service-rules', label: '质检规则', href: '/service/rules', iconKey: 'shield', tint: 'revenue' },
    ],
  },
  {
    key: 'decision',
    title: '决策中心',
    modules: [
      { id: 'diagnosis', label: '竞争诊断', href: '/diagnosis', iconKey: 'compass', tint: 'decision' },
      { id: 'scan', label: '市场扫描', href: '/diagnosis', iconKey: 'globe', tint: 'decision' },
      { id: 'research', label: '深度调研', href: '/diagnosis', iconKey: 'flask', tint: 'decision' },
    ],
  },
  {
    key: 'ops',
    title: '运营中心',
    modules: [
      { id: 'knowledge', label: '企业知识库', href: '/knowledge', iconKey: 'brain', tint: 'ops' },
      { id: 'organization', label: '组织编排', href: '/organization', iconKey: 'network', tint: 'ops' },
      { id: 'ops', label: '系统运维', href: '/ops', iconKey: 'terminal', tint: 'ops' },
    ],
  },
];

/* ── 指挥台快捷指令 ───────────────────────────────────────────────── */
export const DASHBOARD_QUICK_COMMANDS: QuickCommand[] = [
  { id: 'qc1', label: '盘点本周新询盘', prompt: '盘点本周新入库询盘，按意向度分组并给出跟进建议' },
  { id: 'qc2', label: '为新品写 10 条小红书文案', prompt: '为下周上市的新品写 10 条小红书文案，风格贴近爆款笔记' },
  { id: 'qc3', label: '生成竞品红黑榜', prompt: '生成本周竞品红黑榜，重点对比价格策略与内容投放' },
  { id: 'qc4', label: '复盘昨日直播数据', prompt: '复盘昨日数字人直播数据，输出转化率与改进点' },
];

/* ── 数字员工花名册（14 名，等待 workforce 聚合接口） ─────────────── */
export const PREVIEW_AGENTS: Agent[] = [
  {
    id: 'alpha', name: 'Alpha', initial: 'A', role: '行业分析师', moduleLabel: '深度调研', tint: 'decision',
    status: 'running',
    currentTask: { name: '整合 Q3 行业趋势报告', progress: 86, stepDone: 5, stepTotal: 6 },
    workSummary: '整合 Q3 行业趋势报告', todayOutput: '23',
    outputValue: 23, outputUnit: '篇', adoptionRate: 91,
    trend: [30, 42, 38, 55, 50, 68, 78],
  },
  {
    id: 'beta', name: 'Beta', initial: 'B', role: '创作者', moduleLabel: '内容工场', tint: 'growth',
    status: 'needs_action',
    pending: { waitMinutes: 8, title: '12 条小红书文案待你审核', note: '其中 3 条命中敏感词规则，建议优先查看' },
    workSummary: '12 条小红书文案等待审核', todayOutput: '41',
    outputValue: 41, outputUnit: '条', adoptionRate: 64,
    trend: [45, 52, 60, 48, 66, 72, 80],
  },
  {
    id: 'emma', name: 'Emma', initial: 'E', role: '金牌主播', moduleLabel: '数字人直播', tint: 'revenue',
    status: 'running',
    currentTask: { name: '北美场直播中', progress: 64, stepDone: 7, stepTotal: 11 },
    workSummary: '北美场 · 在线 1,204 人', todayOutput: '6.2h',
    outputValue: 6, outputUnit: 'h', adoptionRate: 88,
    trend: [40, 40, 48, 46, 52, 55, 58],
  },
  {
    id: 'ray', name: 'Ray', initial: 'R', role: '销售代表', moduleLabel: '智能接待', tint: 'revenue',
    status: 'running',
    currentTask: { name: '同时接待 9 位访客', progress: 72, stepDone: 3, stepTotal: 4 },
    workSummary: '同时接待 9 位访客', todayOutput: '87',
    outputValue: 87, outputUnit: '通', adoptionRate: 76,
    trend: [20, 45, 35, 60, 42, 68, 55],
  },
  {
    id: 'outbox', name: 'Outbox', initial: 'O', role: '线索管家', moduleLabel: '本地线索池', tint: 'revenue',
    status: 'needs_action',
    pending: { waitMinutes: 21, title: '8 条疑似重复询盘待合并', note: '已按公司名与邮箱指纹聚类，合并后预计净增 38 条' },
    workSummary: '8 条疑似重复询盘待合并', todayOutput: '46',
    outputValue: 46, outputUnit: '条', adoptionRate: 82,
    trend: [55, 62, 42, 58, 36, 52, 44],
  },
  {
    id: 'gamma', name: 'Gamma', initial: 'G', role: '守卫者', moduleLabel: '系统运维', tint: 'ops',
    status: 'idle',
    idleInfo: { lastRun: '上次巡检 17:12', nextPlan: '下次自动巡检 18:00', suggestions: ['立即巡检', '生成周报'] },
    workSummary: '上次巡检 17:12 · 无异常', todayOutput: '4',
    outputValue: 4, outputUnit: '次', adoptionRate: 100,
    trend: [50, 50, 52, 50, 50, 52, 50],
  },
  {
    id: 'leo', name: 'Leo', initial: 'L', role: '首席内容官', moduleLabel: '内容工场', tint: 'growth',
    status: 'running',
    currentTask: { name: '撰写 LinkedIn 新品发布系列', progress: 66, stepDone: 4, stepTotal: 6 },
    workSummary: '撰写 LinkedIn 新品发布系列', todayOutput: '32',
    outputValue: 32, outputUnit: '篇', adoptionRate: 78,
    trend: [28, 38, 34, 48, 44, 60, 72],
  },
  {
    id: 'sophie', name: 'Sophie', initial: 'S', role: '品牌经理', moduleLabel: '全域洞察', tint: 'growth',
    status: 'running',
    currentTask: { name: '监测品牌舆情与心智份额', progress: 41, stepDone: 2, stepTotal: 5 },
    workSummary: '监测 6 大平台品牌提及', todayOutput: '18',
    outputValue: 18, outputUnit: '条', adoptionRate: 85,
    trend: [35, 42, 38, 50, 46, 58, 62],
  },
  {
    id: 'max', name: 'Max', initial: 'M', role: '投放专员', moduleLabel: '投放参谋', tint: 'growth',
    status: 'idle',
    idleInfo: { lastRun: '上次调优 16:40', nextPlan: '下次自动调优 明早 09:00', suggestions: ['立即调优', '导出 ROI 周报'] },
    workSummary: '上次调优 16:40 · ROI +12%', todayOutput: '9',
    outputValue: 9, outputUnit: '次', adoptionRate: 90,
    trend: [60, 55, 62, 58, 66, 61, 68],
  },
  {
    id: 'arthur', name: 'Arthur', initial: 'A', role: '行业分析师', moduleLabel: '竞争诊断', tint: 'decision',
    status: 'running',
    currentTask: { name: '拆解竞品 Q3 价格策略', progress: 33, stepDone: 1, stepTotal: 3 },
    workSummary: '拆解竞品 Q3 价格策略', todayOutput: '12',
    outputValue: 12, outputUnit: '份', adoptionRate: 88,
    trend: [22, 30, 44, 38, 52, 48, 60],
  },
  {
    id: 'scout', name: 'Data Scout', initial: 'D', role: '情报员', moduleLabel: '市场扫描', tint: 'decision',
    status: 'running',
    currentTask: { name: '扫描东南亚市场信号', progress: 58, stepDone: 7, stepTotal: 12 },
    workSummary: '扫描东南亚市场信号', todayOutput: '56',
    outputValue: 56, outputUnit: '条', adoptionRate: 71,
    trend: [48, 52, 46, 60, 55, 64, 70],
  },
  {
    id: 'judge', name: 'AI Judge', initial: 'J', role: '裁判', moduleLabel: '服务质检', tint: 'revenue',
    status: 'needs_action',
    pending: { waitMinutes: 63, title: '2 通接待评分低于 60', note: '均为售后投诉场景，建议复核话术合规性' },
    workSummary: '2 通低分接待待复核', todayOutput: '132',
    outputValue: 132, outputUnit: '通', adoptionRate: 95,
    trend: [70, 74, 68, 78, 72, 80, 76],
  },
  {
    id: 'doc', name: 'Doc', initial: 'D', role: '知识总管', moduleLabel: '企业知识库', tint: 'ops',
    status: 'idle',
    idleInfo: { lastRun: '上次索引 15:30', nextPlan: '增量索引 每晚 23:00', suggestions: ['立即索引', '清理失效文档'] },
    workSummary: '上次索引 15:30 · 1.2TB 在库', todayOutput: '7',
    outputValue: 7, outputUnit: '次', adoptionRate: 97,
    trend: [52, 55, 50, 58, 54, 60, 58],
  },
  {
    id: 'monica', name: 'Monica', initial: 'M', role: 'HRBP', moduleLabel: '组织编排', tint: 'ops',
    status: 'idle',
    idleInfo: { lastRun: '上次权限审计 昨天', nextPlan: '下次审计 下周一 10:00', suggestions: ['权限审计', '编排新团队'] },
    workSummary: '上次权限审计 昨天 · 无风险', todayOutput: '2',
    outputValue: 2, outputUnit: '项', adoptionRate: 100,
    trend: [40, 42, 40, 44, 42, 46, 44],
  },
];

/** 花名册统计（派生值，避免各组件重复计算） */
export function countByStatus(agents: Agent[]) {
  return {
    all: agents.length,
    running: agents.filter((a) => a.status === 'running').length,
    needs_action: agents.filter((a) => a.status === 'needs_action').length,
    idle: agents.filter((a) => a.status === 'idle').length,
  };
}
