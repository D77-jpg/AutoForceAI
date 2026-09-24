/**
 * 数字人调度中心 — 真实数据接入层。
 *
 * 当前接入：系统监控、本地线索、CRM 概览、CRM worker 健康。
 * 数字员工聚合接口尚未提供，花名册使用明确标注的预览数据。
 */
import api from './api';
import type {
  ActivityEvent,
  DashboardData,
  InboxItem,
  KpiMetric,
  PipelineTask,
  SystemStatus,
} from './dashboard-types';
import { PREVIEW_AGENTS } from './dashboard-mock';

interface MonitorResponse {
  status?: string;
  cpu_usage?: number;
  memory_usage?: { percent?: number };
}

interface LeadSummaryResponse {
  total?: number;
  today?: number;
  by_status?: Partial<Record<'new' | 'contacted' | 'converted' | 'dropped', number>>;
}

interface CrmOverviewResponse {
  config?: {
    enabled?: boolean;
    last_health_status?: string | null;
  } | null;
  queue?: Partial<Record<'pending' | 'leased' | 'retrying' | 'succeeded' | 'dead' | 'cancelled', number>>;
  local?: {
    synced_total?: number;
    won?: number;
    lost?: number;
  };
  recent_synced?: Array<{
    lead_id: number;
    name?: string | null;
    company?: string | null;
    remote_status?: string | null;
    synced_at?: string | null;
  }>;
  genesis_error?: string | null;
}

interface WorkerHealthResponse {
  worker_enabled?: boolean;
  dispatcher?: { last_success_at?: string | null };
  poller?: { last_success_at?: string | null };
  last_error?: string | null;
  last_error_at?: string | null;
}

const EMPTY_STATUS: SystemStatus = {
  state: 'loading',
  label: '正在连接实时数据',
  cpuUsage: null,
  memoryUsage: null,
};

const EMPTY_KPIS: KpiMetric[] = [
  { id: 'leads-total', label: '本地线索', value: '—', caption: '正在读取线索池' },
  { id: 'leads-today', label: '今日新增', value: '—', caption: '正在读取今日数据' },
  { id: 'crm-synced', label: 'CRM 已交接', value: '—', caption: '正在读取 Genesis 集成' },
  { id: 'crm-active', label: '待同步任务', value: '—', caption: '正在读取投递队列' },
];

export const INITIAL_DASHBOARD_DATA: DashboardData = {
  status: EMPTY_STATUS,
  inbox: [],
  kpis: EMPTY_KPIS,
  activities: [],
  pipeline: [],
  agents: PREVIEW_AGENTS,
  newLeadCount: 0,
  sources: {
    loading: true,
    liveSections: [],
    unavailableSections: [],
    previewSections: ['数字员工'],
  },
};

function valueOf(
  queue: CrmOverviewResponse['queue'],
  key: keyof NonNullable<CrmOverviewResponse['queue']>
) {
  return Number(queue?.[key] || 0);
}

function formatTime(value?: string | null) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return new Intl.DateTimeFormat('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(date);
}

function isRecent(value?: string | null, withinMinutes = 15) {
  if (!value) return false;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return false;
  const age = Date.now() - date.getTime();
  return age >= 0 && age <= withinMinutes * 60 * 1000;
}

function crmStatusLabel(status?: string | null) {
  const labels: Record<string, string> = {
    pending: '待开发',
    contacted: '已联系',
    replied: '已回复',
    interested: '有意向',
    quoting: '报价中',
    negotiating: '谈判中',
    won: '已成交',
    lost: '已流失',
  };
  return status ? labels[status] || status : '已同步';
}

/** 任一数据源失败时保留其它已成功的数据，不以 mock 冒充实时结果。 */
export async function fetchDashboardData(): Promise<DashboardData> {
  const [monitorResult, leadsResult, crmResult, workerResult] = await Promise.allSettled([
    api.get<MonitorResponse>('/api/v1/monitor/system'),
    api.get<LeadSummaryResponse>('/api/v1/leads/summary'),
    api.get<CrmOverviewResponse>('/api/v1/crm/integration/overview'),
    api.get<WorkerHealthResponse>('/api/v1/crm/integration/worker-health'),
  ]);

  const monitor = monitorResult.status === 'fulfilled' ? monitorResult.value.data : null;
  const leads = leadsResult.status === 'fulfilled' ? leadsResult.value.data : null;
  const crm = crmResult.status === 'fulfilled' ? crmResult.value.data : null;
  const worker = workerResult.status === 'fulfilled' ? workerResult.value.data : null;

  const liveSections: string[] = [];
  const unavailableSections: string[] = [];
  if (monitor) liveSections.push('系统'); else unavailableSections.push('系统');
  if (leads) liveSections.push('线索'); else unavailableSections.push('线索');
  if (crm) liveSections.push('CRM'); else unavailableSections.push('CRM');
  if (worker) liveSections.push('Worker'); else unavailableSections.push('Worker');

  const crmDegraded = Boolean(crm?.genesis_error);
  const workerDisabled = worker?.worker_enabled === false;
  const workerDegraded = Boolean(worker?.last_error && isRecent(worker.last_error_at));
  const status: SystemStatus = monitor
    ? {
        state: crmDegraded || workerDisabled || workerDegraded ? 'degraded' : 'online',
        label:
          crmDegraded || workerDisabled || workerDegraded
            ? '核心 API 在线，集成链路需关注'
            : '核心 API 在线',
        cpuUsage: typeof monitor.cpu_usage === 'number' ? Math.round(monitor.cpu_usage) : null,
        memoryUsage:
          typeof monitor.memory_usage?.percent === 'number'
            ? Math.round(monitor.memory_usage.percent)
            : null,
      }
    : {
        state: 'unavailable',
        label: '系统状态暂不可用',
        cpuUsage: null,
        memoryUsage: null,
      };

  const totalLeads = Number(leads?.total || 0);
  const newToday = Number(leads?.today || 0);
  const converted = Number(leads?.by_status?.converted || 0);

  const queue = crm?.queue;
  const pending = valueOf(queue, 'pending');
  const leased = valueOf(queue, 'leased');
  const retrying = valueOf(queue, 'retrying');
  const succeeded = valueOf(queue, 'succeeded');
  const dead = valueOf(queue, 'dead');
  const active = pending + leased + retrying;
  const syncedTotal = Number(crm?.local?.synced_total || 0);

  const kpis: KpiMetric[] = [
    {
      id: 'leads-total',
      label: '本地线索',
      value: leads ? String(totalLeads) : '—',
      caption: leads ? `已转化 ${converted}` : '线索接口暂不可用',
    },
    {
      id: 'leads-today',
      label: '今日新增',
      value: leads ? String(newToday) : '—',
      caption: leads ? '按本地日期统计' : '线索接口暂不可用',
    },
    {
      id: 'crm-synced',
      label: 'CRM 已交接',
      value: crm ? String(syncedTotal) : '—',
      caption: crm ? `成交 ${crm.local?.won || 0} · 流失 ${crm.local?.lost || 0}` : 'CRM 接口暂不可用',
    },
    {
      id: 'crm-active',
      label: '待同步任务',
      value: crm ? String(active) : '—',
      caption: crm ? `已同步 ${succeeded} · 死信 ${dead}` : 'CRM 接口暂不可用',
    },
  ];

  const inbox: InboxItem[] = [];
  if (dead > 0) {
    inbox.push({
      id: 'crm-dead',
      tone: 'danger',
      title: `${dead} 条 CRM 同步死信待处理`,
      agentName: 'CRM 集成',
      moduleLabel: '投递队列',
      timeAgo: '实时',
      actionLabel: '查看',
      href: '/crm',
    });
  }
  if (retrying > 0) {
    inbox.push({
      id: 'crm-retrying',
      tone: 'warning',
      title: `${retrying} 条 CRM 同步任务正在重试`,
      agentName: 'CRM 集成',
      moduleLabel: '投递队列',
      timeAgo: '实时',
      actionLabel: '查看',
      href: '/crm',
    });
  }
  if (crm?.genesis_error) {
    inbox.push({
      id: 'genesis-unavailable',
      tone: 'danger',
      title: 'Genesis CRM 当前不可达',
      agentName: 'CRM 集成',
      moduleLabel: '连接状态',
      timeAgo: '实时',
      actionLabel: '诊断',
      href: '/crm',
    });
  }
  if (worker?.last_error && isRecent(worker.last_error_at)) {
    inbox.push({
      id: 'worker-error',
      tone: 'warning',
      title: '后台同步 Worker 最近出现异常',
      agentName: '系统运维',
      moduleLabel: 'Worker 健康',
      timeAgo: formatTime(worker.last_error_at),
      actionLabel: '查看',
      href: '/crm/settings',
    });
  }
  if (workerDisabled) {
    inbox.push({
      id: 'worker-disabled',
      tone: 'warning',
      title: '后台同步 Worker 当前未启用',
      agentName: '系统运维',
      moduleLabel: 'Worker 配置',
      timeAgo: '实时',
      actionLabel: '查看',
      href: '/crm/settings',
    });
  }

  const activities: ActivityEvent[] = (crm?.recent_synced || []).slice(0, 5).map((item) => ({
    id: `crm-${item.lead_id}`,
    time: formatTime(item.synced_at),
    agentName: 'CRM',
    agentInitial: 'C',
    tint: 'revenue',
    description: `${item.company || item.name || `线索 #${item.lead_id}`} 已同步至 Genesis · ${crmStatusLabel(item.remote_status)}`,
  }));

  const cancelled = valueOf(queue, 'cancelled');
  const totalJobs = active + succeeded + dead + cancelled;
  const terminalJobs = succeeded + dead + cancelled;
  const pipeline: PipelineTask[] = crm
    ? [
        {
          id: 'crm-sync',
          name: 'Genesis CRM 线索交接',
          status: dead > 0 ? 'review' : active > 0 ? 'running' : 'complete',
          statusLabel: dead > 0 ? '需处理' : active > 0 ? '同步中' : '队列已清空',
          progress: totalJobs > 0 ? Math.round((terminalJobs / totalJobs) * 100) : 100,
          agentName: 'CRM Integration',
          detail: `${succeeded} 成功 · ${active} 处理中 · ${dead} 死信`,
        },
      ]
    : [];

  return {
    status,
    inbox,
    kpis,
    activities,
    pipeline,
    agents: PREVIEW_AGENTS,
    newLeadCount: Number(leads?.by_status?.new || 0),
    sources: {
      loading: false,
      liveSections,
      unavailableSections,
      previewSections: ['数字员工'],
    },
  };
}
