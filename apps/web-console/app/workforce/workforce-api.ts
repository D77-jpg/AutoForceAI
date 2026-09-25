import axios from 'axios';
import api from '@/lib/api';

export type WorkforceProject = { id: number; name: string; organization_id: number };
export type RoleTemplate = {
  key: string; name: string; role: string; description: string; goal: string;
  prohibitions: string[]; allowed_tools: string[]; unavailable_capabilities: string[];
  data_scope: { organization: string; project: string; cross_project: boolean }; max_steps: number; timeout_seconds: number; max_cost_usd: number;
  requires_human_approval_for_external_actions: boolean;
  prompt_version: string; template_version: string; system_prompt: string;
};
export type Employee = {
  id: number; project_id: number; name: string; role: string; description: string;
  system_prompt: string; capabilities: string[];
  skills?: { tool_name: string; config: Record<string, unknown> }[];
  template_key?: string | null; template_version?: string | null; prompt_version?: string | null;
  allowed_tools?: string[]; data_scope?: { organization: string; project: string; cross_project: boolean } | null;
  max_steps?: number; timeout_seconds?: number; max_cost_usd?: number;
  requires_human_approval_for_external_actions?: boolean;
  avatar_url?: string | null;
  created_by?: number | null; updated_by?: number | null;
  created_at?: string | null; updated_at?: string | null;
};

export async function fetchProjects(): Promise<WorkforceProject[]> {
  const { data } = await api.get<WorkforceProject[]>('/agents/projects');
  if (!Array.isArray(data)) throw new Error('项目列表响应格式不正确');
  return data;
}

export function errorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    return typeof detail === 'string' ? detail : error.message;
  }
  return error instanceof Error ? error.message : '未知错误';
}

export function projectQuery(id: number): string {
  return `?project_id=${encodeURIComponent(id)}`;
}
