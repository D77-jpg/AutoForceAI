/**
 * 数字人调度中心 — 数据接入层
 * 组件只调用本文件的函数；有真实接口的走 lib/api.ts，没有的返回 mock 并标 TODO。
 * 后续接接口时只改这里，组件零改动。
 */
import type {
  Agent,
  ActivityEvent,
  InboxItem,
  KpiMetric,
  PipelineTask,
  SystemStatus,
} from './dashboard-types';
import {
  MOCK_ACTIVITIES,
  MOCK_AGENTS,
  MOCK_INBOX,
  MOCK_KPIS,
  MOCK_PIPELINE,
  MOCK_SYSTEM_STATUS,
} from './dashboard-mock';

// TODO: GET /api/v1/system/health → SystemStatus
export async function fetchSystemStatus(): Promise<SystemStatus> {
  return MOCK_SYSTEM_STATUS;
}

// TODO: GET /api/v1/dashboard/inbox → InboxItem[]
export async function fetchInbox(): Promise<InboxItem[]> {
  return MOCK_INBOX;
}

// TODO: GET /api/v1/dashboard/kpis → KpiMetric[]
export async function fetchKpis(): Promise<KpiMetric[]> {
  return MOCK_KPIS;
}

// TODO: GET /api/v1/dashboard/activity → ActivityEvent[]（后续可换 SSE/WebSocket 推送）
export async function fetchActivities(): Promise<ActivityEvent[]> {
  return MOCK_ACTIVITIES;
}

// TODO: GET /api/v1/tasks/pipeline → PipelineTask[]
export async function fetchPipeline(): Promise<PipelineTask[]> {
  return MOCK_PIPELINE;
}

// TODO: GET /api/v1/workforce/roster → Agent[]（含状态/产出/趋势聚合）
export async function fetchAgents(): Promise<Agent[]> {
  return MOCK_AGENTS;
}

// TODO: POST /api/v1/tasks/dispatch { prompt, assignee, useKnowledge }
export async function dispatchTask(payload: {
  prompt: string;
  assignee: string;
  useKnowledge: boolean;
}): Promise<{ ok: boolean }> {
  void payload;
  return { ok: true };
}
