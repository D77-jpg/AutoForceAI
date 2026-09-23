"use client";
import React, { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, PlugZap, ShieldCheck } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";
function auth() {
  return { Authorization: "Bearer " + (localStorage.getItem("token") || "") };
}

interface CrmConfig {
  provider: string;
  base_url: string;
  project_id: string;
  project_name?: string | null;
  token_preview?: string | null;
  has_token: boolean;
  contract_version: string;
  enabled: boolean;
  last_health_status?: string | null;
  last_health_detail?: string | null;
  last_health_checked_at?: string | null;
}

interface TestResult {
  ok: boolean;
  detail: string;
  scopes?: string[] | null;
  project_name?: string | null;
  contract_version?: string | null;
}

export default function CrmIntegrationSettingsPage() {
  const [config, setConfig] = useState<CrmConfig | null>(null);
  const [baseUrl, setBaseUrl] = useState("");
  const [projectId, setProjectId] = useState("");
  const [token, setToken] = useState("");
  const [enabled, setEnabled] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [forbidden, setForbidden] = useState(false);

  const load = async () => {
    const res = await fetch(API + "/api/v1/crm/integration/config", { headers: auth() });
    if (res.status === 403) { setForbidden(true); return; }
    const data = await res.json();
    const cfg: CrmConfig | null = data.config;
    setConfig(cfg);
    if (cfg) {
      setBaseUrl(cfg.base_url || "");
      setProjectId(cfg.project_id || "");
      setEnabled(!!cfg.enabled);
    }
  };
  useEffect(() => { load(); }, []);

  const save = async () => {
    setSaving(true); setError(null);
    try {
      const body: Record<string, unknown> = { base_url: baseUrl, project_id: projectId, enabled };
      if (token.trim()) body.service_token = token.trim(); // 留空 = 保留原 token
      const res = await fetch(API + "/api/v1/crm/integration/config", {
        method: "PUT",
        headers: { ...auth(), "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "保存失败");
      setToken("");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存失败");
    } finally {
      setSaving(false);
    }
  };

  const test = async () => {
    setTesting(true); setTestResult(null);
    try {
      const res = await fetch(API + "/api/v1/crm/integration/test", { method: "POST", headers: auth() });
      setTestResult(await res.json());
      await load();
    } finally {
      setTesting(false);
    }
  };

  if (forbidden) {
    return (
      <div className="min-h-screen bg-bg text-text p-8">
        <PageHeader title="CRM 集成设置" description="仅企业管理员可管理 Genesis_CRM 连接配置。" />
        <p className="text-text-secondary">当前账号无权限访问此页面。</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-bg text-text p-8">
      <PageHeader
        title="CRM 集成设置"
        description="配置本企业与 Genesis_CRM 项目的连接。服务凭证只保存在服务端，此处永不回显明文。"
        actions={
          <Link href="/crm">
            <Button variant="outline"><ArrowLeft size={16} className="mr-2" />返回 CRM 门户</Button>
          </Link>
        }
      />

      <div className="max-w-2xl space-y-6">
        <div className="bg-surface border border-border rounded-lg p-6 space-y-4 shadow-card">
          <div>
            <label className="text-sm text-text-secondary block mb-1">Genesis API 地址</label>
            <Input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder="http://localhost:5000/api" />
          </div>
          <div>
            <label className="text-sm text-text-secondary block mb-1">绑定项目 ID（Genesis projectId，必填，无默认回退）</label>
            <Input value={projectId} onChange={(e) => setProjectId(e.target.value)} placeholder="6aa2360776ab59e92117bb18" />
            {config?.project_name && (
              <p className="text-xs text-text-secondary mt-1">最近校验项目：{config.project_name}</p>
            )}
          </div>
          <div>
            <label className="text-sm text-text-secondary block mb-1">
              服务凭证 Token {config?.has_token ? `（已配置 ${config.token_preview}，留空保持不变）` : ""}
            </label>
            <Input
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder={config?.has_token ? "留空保持不变" : "gci_…（由 Genesis 管理员签发）"}
            />
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
            允许新线索投递到 Genesis_CRM
          </label>
          <div className="flex gap-2 pt-2">
            <Button onClick={save} disabled={saving}>{saving ? "保存中…" : "保存配置"}</Button>
            <Button variant="outline" onClick={test} disabled={testing || !config}>
              <PlugZap size={16} className="mr-2" />{testing ? "测试中…" : "测试连接"}
            </Button>
          </div>
          {error && <p className="text-sm text-red-500">{error}</p>}
        </div>

        {testResult && (
          <div className={`border rounded-lg p-4 ${testResult.ok ? "border-green-500/40 bg-green-500/5" : "border-red-500/40 bg-red-500/5"}`}>
            <div className="flex items-center gap-2 mb-1">
              <ShieldCheck size={16} className={testResult.ok ? "text-green-500" : "text-red-500"} />
              <span className="font-medium">{testResult.ok ? "连接正常" : "连接失败"}</span>
            </div>
            <p className="text-sm text-text-secondary">{testResult.detail}</p>
            {testResult.ok && (
              <p className="text-xs text-text-secondary mt-2">
                项目：{testResult.project_name} · 契约版本：{testResult.contract_version} · scope：[{(testResult.scopes || []).join(", ")}]
              </p>
            )}
          </div>
        )}

        {config && (
          <div className="bg-surface border border-border rounded-lg p-4 text-sm text-text-secondary">
            最近连接测试：{config.last_health_checked_at ? new Date(config.last_health_checked_at).toLocaleString() : "从未"}
            {config.last_health_status && ` · ${config.last_health_status}`}
            {config.last_health_detail ? ` · ${config.last_health_detail}` : ""}
          </div>
        )}
      </div>
    </div>
  );
}
