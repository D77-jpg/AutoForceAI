/**
 * 数字人调度中心 — 数据类型定义
 * 所有区块的数据结构集中在此，便于后续 mock → 真实接口的替换。
 */

/** 数字员工状态：运行中 / 需要我处理 / 待机 */
export type AgentStatus = 'running' | 'needs_action' | 'idle';

/** 侧边栏模块分组 */
export type DepartmentKey = 'growth' | 'revenue' | 'decision' | 'ops';

/** 侧边栏单个模块入口 */
export interface ModuleNav {
  id: string;
  label: string;
  href: string;
  /** lucide 图标名由侧边栏组件内映射，避免类型文件依赖组件库 */
  iconKey: string;
  tint: DepartmentKey;
  /** 待办徽标：数字或纯红点；暂无接口，预留字段（TODO） */
  badge?: number | 'dot';
}

export interface DepartmentNav {
  key: DepartmentKey;
  title: string;
  modules: ModuleNav[];
}

/** 顶栏系统状态：只展示可由监控接口直接证明的指标 */
export interface SystemStatus {
  state: 'loading' | 'online' | 'degraded' | 'unavailable';
  label: string;
  cpuUsage: number | null;
  memoryUsage: number | null;
}

/** 首页数据来源状态，避免把预览数据误认为实时生产数据 */
export interface DashboardSourceState {
  loading: boolean;
  liveSections: string[];
  unavailableSections: string[];
  previewSections: string[];
}

/** 首页一次加载得到的完整视图模型 */
export interface DashboardData {
  status: SystemStatus;
  inbox: InboxItem[];
  kpis: KpiMetric[];
  activities: ActivityEvent[];
  pipeline: PipelineTask[];
  agents: Agent[];
  newLeadCount: number;
  sources: DashboardSourceState;
}

/** 指挥台快捷指令 */
export interface QuickCommand {
  id: string;
  label: string;
  /** 点击后填入输入框的完整文案 */
  prompt: string;
}

/** 待我处理事项 */
export interface InboxItem {
  id: string;
  /** 状态色点语义 */
  tone: 'warning' | 'accent' | 'danger';
  title: string;
  agentName: string;
  moduleLabel: string;
  /** 相对时间文案，如 "8 分钟前"（mock 阶段直接给文案，接接口后换时间戳） */
  timeAgo: string;
  actionLabel: string; // 审核 / 处理 / 查看
  href: string;
}

/** 核心指标（KPI 四格之一） */
export interface KpiMetric {
  id: string;
  label: string;
  value: string;         // 大号数字，如 "32.4%"
  suffix?: string;       // 如 "/17"
  delta?: { value: string; direction: 'up' | 'down' };
  /** 迷你趋势线数据点（0–100 归一化） */
  spark?: number[];
  /** 说明行 */
  caption: string;
  /** 仅"在线数字员工"使用：三段状态条 */
  segments?: { running: number; needsAction: number; idle: number };
}

/** 实时动态事件 */
export interface ActivityEvent {
  id: string;
  time: string; // "17:52"
  agentName: string;
  agentInitial: string;
  tint: DepartmentKey;
  description: string; // 含员工名的完整句子，渲染时加粗员工名前缀
}

/** 任务流水线条目 */
export type PipelineStatus = 'running' | 'review' | 'queued' | 'complete';

export interface PipelineTask {
  id: string;
  name: string;
  status: PipelineStatus;
  statusLabel: string;   // 生成中 / 待审核 / 排队中
  progress: number;      // 0–100
  agentName: string;
  detail: string;        // "正在整合 214 条来源" / "12/20 条已产出" / "预计 18:30 开始"
}

/** 花名册 / AgentCard 共用的员工模型 */
export interface Agent {
  id: string;
  name: string;          // "Leo"
  initial: string;       // 头像字母 "L"
  role: string;          // "首席内容官"
  moduleLabel: string;   // "内容工场"
  tint: DepartmentKey;
  status: AgentStatus;
  /** running：当前任务 */
  currentTask?: {
    name: string;
    progress: number;    // 0–100
    stepDone: number;
    stepTotal: number;
  };
  /** needs_action：待处理 */
  pending?: {
    waitMinutes: number;
    title: string;
    note?: string;
  };
  /** idle：待机信息 */
  idleInfo?: {
    lastRun: string;     // "上次巡检 17:12"
    nextPlan: string;    // "下次自动巡检 18:00"
    suggestions: string[]; // "可以让他做"胶囊
  };
  /** 花名册行：当前工作一句话 */
  workSummary: string;
  /** 花名册行：今日产出（已格式化的展示值，如 "23" / "6.2h"） */
  todayOutput: string;
  /** AgentCard 指标 */
  outputValue: number;
  outputUnit: string;    // 篇 / 条 / 次
  adoptionRate: number;  // 采纳率 %
  /** 7 日趋势（0–100 归一化），花名册与卡片共用 */
  trend: number[];
}
