"use client";
import React, { useState, useEffect } from 'react';
import { 
  Search, 
  Plus, 
  Settings, 
  Trash2, 
  CheckCircle2,
  Box
} from 'lucide-react';
import api from '../../../lib/api';
import { useToast } from '../../../contexts/ToastContext';
import { PageHeader } from '@/components/PageHeader';
import { EmptyState } from '@/components/ui/empty-state';
import { Modal } from '@/components/ui/modal';
import { Table, TableHead, TableBody, TableRow, TableHeaderCell, TableCell } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

interface Model {
  id: number;
  name: string;
  display_name: string;
  provider_name?: string;
  provider_id?: number;
  type: string;
  context_window: string;
  is_active: boolean;
  supports_geo: boolean;
  supports_chat: boolean;
  api_key?: string;
  base_url?: string;
  is_default: boolean;
  is_kb_search_default?: boolean;
}

interface Provider {
    id: number;
    name: string;
}

const PRESETS: any = {
    'openai': 'https://api.openai.com/v1',
    'azure': 'https://{resource}.openai.azure.com',
    'zhipu': 'https://open.bigmodel.cn/api/paas/v4',
    'aliyun': 'https://dashscope.aliyuncs.com/compatible-mode/v1'
};

const MODEL_PRESETS = [
    { label: 'OpenAI GPT-4o', value: 'gpt-4o', base_url: 'https://api.openai.com/v1', context: '128k' },
    { label: 'OpenAI GPT-4 Turbo', value: 'gpt-4-turbo', base_url: 'https://api.openai.com/v1', context: '128k' },
    { label: 'Aliyun Qwen-Max', value: 'qwen-max', base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1', context: '32k' },
    { label: 'Aliyun Qwen-Turbo', value: 'qwen-turbo', base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1', context: '32k' },
    { label: 'Aliyun Qwen-Plus', value: 'qwen-plus', base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1', context: '128k' },
    { label: 'Zhipu GLM-4', value: 'glm-4', base_url: 'https://open.bigmodel.cn/api/paas/v4', context: '128k' },
    { label: 'Zhipu GLM-4-Flash', value: 'glm-4-flash', base_url: 'https://open.bigmodel.cn/api/paas/v4', context: '128k' },
    { label: 'DeepSeek V3', value: 'deepseek-chat', base_url: 'https://api.deepseek.com', context: '64k' },
    { label: 'DeepSeek R1', value: 'deepseek-reasoner', base_url: 'https://api.deepseek.com', context: '64k' },
    { label: 'SiliconFlow DeepSeek R1', value: 'deepseek-ai/DeepSeek-R1', base_url: 'https://api.siliconflow.cn/v1', context: '64k' },
    { label: 'SiliconFlow DeepSeek V3', value: 'deepseek-ai/DeepSeek-V3', base_url: 'https://api.siliconflow.cn/v1', context: '64k' },
    { label: 'Volcengine Doubao Pro 32k', value: 'doubao-pro-32k', base_url: 'https://ark.cn-beijing.volces.com/api/v3', context: '32k' },
    { label: 'Volcengine Doubao Lite 32k', value: 'doubao-lite-32k', base_url: 'https://ark.cn-beijing.volces.com/api/v3', context: '32k' },
    { label: 'Volcengine Doubao Pro 128k', value: 'doubao-pro-128k', base_url: 'https://ark.cn-beijing.volces.com/api/v3', context: '128k' },
    { label: 'Volcengine Doubao 1.5 Pro 32k', value: 'doubao-1-5-pro-32k-250115', base_url: 'https://ark.cn-beijing.volces.com/api/v3', context: '32k' },
    { label: 'Custom / Other', value: 'custom', base_url: '', context: '' }
];

export default function ModelsPage() {
  const [models, setModels] = useState<Model[]>([]);
  const { showToast } = useToast();
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingModel, setEditingModel] = useState<Model | null>(null);
  const [providers, setProviders] = useState<Provider[]>([]);

  // Fetch Models
  useEffect(() => {
    fetchModels();
  }, []);

  const fetchModels = async () => {
        setLoading(true);
        try {
          const res = await api.get('/api/v1/platform/models');
          setModels(res.data);
        } catch (err) {
          console.error(err);
          showToast("加载模型列表失败", "error");
        } finally {
          setLoading(false);
        }
      };
    
      const fetchProviders = async () => {
          try {
              const res = await api.get('/api/v1/platform/providers');
              setProviders(res.data);
          } catch (err) {
              console.error(err);
          }
      }

      // Add state for delete confirmation
      const [deleteTargetId, setDeleteTargetId] = useState<number | null>(null);

      const confirmDelete = async () => {
        if (!deleteTargetId) return;
        try {
          await api.delete(`/api/v1/platform/models/${deleteTargetId}`);
          showToast("模型已删除", "success");
          fetchModels();
        } catch (err) {
          showToast("操作失败", "error");
        } finally {
          setDeleteTargetId(null);
        }
      }
    
      const openCreateModal = () => {
          setEditingModel(null);
          // fetchProviders(); // Providers hidden
          setShowModal(true);
      }
    
      const openEditModal = (model: Model) => {
          setEditingModel(model);
          // fetchProviders();
          setShowModal(true);
      }
    
      return (
        <div className="h-full flex flex-col p-6 text-text">
            <PageHeader
                title="模型纳管"
                description="管理与配置您的 AI 模型资产与路由。"
                actions={
                    <Button onClick={openCreateModal} className="gap-2">
                        <Plus size={16} /> 接入新模型
                    </Button>
                }
            />
    
            {/* Filters */}
            <div className="flex items-center gap-4 mb-6">
                <div className="relative flex-1 max-w-md">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-text-tertiary z-10" size={16} />
                    <Input 
                        type="text" 
                        placeholder="搜索模型..." 
                        className="pl-10"
                    />
                </div>
                <div className="flex items-center gap-2">
                     <FilterButton label="全部类型" active />
                     <FilterButton label="仅活跃" />
                </div>
            </div>
    
            {/* Content Area */}
            {loading ? (
                 <div className="glass-panel min-h-0 flex-1 border border-separator bg-surface rounded-xl p-12 text-center text-text-secondary">正在加载模型配置...</div>
            ) : models.length === 0 ? (
                <EmptyState
                    icon={Box}
                    size="lg"
                    title="还没有接入任何模型"
                    description="接入您的第一个 AI 模型，即可在聊天与业务技能中使用。"
                    actionLabel="接入新模型"
                    onAction={openCreateModal}
                    className="flex-1"
                />
            ) : (
            <div className="glass-panel min-h-0 flex-1 flex flex-col overflow-hidden border border-separator bg-surface rounded-xl">
                    <div className="flex-1 overflow-auto">
                        <Table>
                            <TableHead className="bg-surface sticky top-0 z-10">
                                <TableRow>
                                    <TableHeaderCell className="pl-6">显示名称</TableHeaderCell>
                                    <TableHeaderCell>类型</TableHeaderCell>
                                    <TableHeaderCell>上下文</TableHeaderCell>
                                    <TableHeaderCell>GEO 搜索</TableHeaderCell>
                                    <TableHeaderCell>状态</TableHeaderCell>
                                    <TableHeaderCell className="text-right pr-6">操作</TableHeaderCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {models.map((model) => (
                                    <TableRow key={model.id} className="group">
                                        <TableCell className="pl-6 font-medium">
                                            <div className="flex items-center gap-2">
                                                {model.display_name}
                                                {model.is_default && (
                                                    <span className="px-1.5 py-0.5 rounded bg-accent/15 text-accent text-[10px] border border-accent/25">
                                                        默认
                                                    </span>
                                                )}
                                                {model.is_kb_search_default && (
                                                    <span className="px-1.5 py-0.5 rounded bg-warning/20 text-warning text-[10px] border border-warning/30">
                                                        KB默认
                                                    </span>
                                                )}
                                            </div>
                                        </TableCell>
                                        <TableCell>
                                            <span className="px-2 py-0.5 rounded border border-separator text-xs bg-text/5 font-mono text-text">{model.type}</span>
                                        </TableCell>
                                        <TableCell className="text-text-secondary font-mono tabular-nums">{model.context_window}</TableCell>
                                        <TableCell>
                                            {model.supports_geo ? (
                                                <span className="text-success text-xs flex items-center gap-1"><CheckCircle2 size={12}/> 支持</span>
                                            ) : (
                                                <span className="text-text-tertiary text-xs">-</span>
                                            )}
                                        </TableCell>
                                        <TableCell>
                                            <StatusBadge active={model.is_active !== false} />
                                        </TableCell>
                                        <TableCell className="text-right pr-6">
                                            <div className="flex items-center justify-end gap-2 text-text-secondary opacity-0 group-hover:opacity-100 transition-opacity">
                                                <button 
                                                    onClick={() => openEditModal(model)}
                                                    className="p-1.5 hover:bg-text/10 rounded text-text-secondary hover:text-text transition-colors" title="配置"
                                                >
                                                    <Settings size={14} />
                                                </button>
                                                <button 
                                                    onClick={() => setDeleteTargetId(model.id)}
                                                    className="p-1.5 hover:bg-danger/10 hover:text-danger rounded text-text-secondary transition-colors" title="下线"
                                                >
                                                    <Trash2 size={14} />
                                                </button>
                                            </div>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </div>
            </div>
            )}
    
            {showModal && (
                <ModelModal 
                    model={editingModel} 
                    providers={providers}
                    onClose={() => setShowModal(false)}
                    onSuccess={() => {
                        setShowModal(false);
                        fetchModels();
                    }}
                />
            )}

            {/* Delete Confirmation Modal */}
            <Modal
                open={!!deleteTargetId}
                onClose={() => setDeleteTargetId(null)}
                title="确认删除"
                footer={
                    <>
                        <Button variant="outline" onClick={() => setDeleteTargetId(null)}>取消</Button>
                        <Button variant="destructive" onClick={confirmDelete}>确认删除</Button>
                    </>
                }
            >
                <p className="text-sm text-text-secondary">确定要删除此模型配置吗？此操作不可恢复。</p>
            </Modal>
        </div>
      );
    }
function ModelModal({ model, providers, onClose, onSuccess }: { model: Model | null, providers: Provider[], onClose: () => void, onSuccess: () => void }) {
    const { showToast } = useToast();
    const [loading, setLoading] = useState(false);
    // Auto-detect provider or use first available (hidden from user)
    const defaultProviderId = providers.length > 0 ? providers[0].id : undefined;

    const [formData, setFormData] = useState({
        provider_id: model?.provider_id || defaultProviderId, 
        name: model?.name || '',
        display_name: model?.display_name || '',
        type: model?.type || 'LLM',
        context_window: model?.context_window || '4k',
        supports_geo: model?.supports_geo || false,
        supports_chat: model?.supports_chat ?? true,
        // Set default active status for NEW models to false (per user request: "default is unchecked")
        // But keep existing model's status if editing
        is_active: model ? (model.is_active ?? true) : false,
        api_key: model?.api_key || '',
        base_url: model?.base_url || '',
        is_default: model?.is_default || false,
        is_kb_search_default: model?.is_kb_search_default || false
    });

    const isEdit = !!model;

    const handlePresetChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
        const val = e.target.value;
        const preset = MODEL_PRESETS.find(p => p.value === val);
        if (preset) {
            if (val === 'custom') {
                 // Don't fully reset, just allow editing name
                 setFormData(prev => ({ ...prev, name: '', display_name: '' }));
            } else {
                 setFormData(prev => ({
                     ...prev,
                     name: preset.value,
                     display_name: preset.label,
                     base_url: preset.base_url,
                     context_window: preset.context,
                     // Reset API key or keep? Usually API key is unique per provider, but if switching preset within same provider, might want to keep. 
                     // Safe to keep existing input if user already typed it.
                 }));
            }
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        
        let submitData = { ...formData };
        
        // Validation for Custom
        if (!submitData.display_name) {
            showToast("请填写模型名称", "error");
            setLoading(false);
            return;
        }

        // Auto-generate ID if not present (logic: slugify display name)
        if (!submitData.name && submitData.display_name) {
             submitData.name = submitData.display_name
                .toLowerCase()
                .trim()
                .replace(/[\s_]+/g, '-')
                .replace(/[^a-z0-9-]/g, '');
        }

        try {
            if (isEdit && model) {
                await api.put(`/api/v1/platform/models/${model.id}`, submitData);
            } else {
                await api.post('/api/v1/platform/models', submitData);
            }
            showToast(isEdit ? "更新成功" : "创建成功", "success");
            onSuccess();
        } catch (err) {
            console.error(err);
            showToast("操作失败", "error");
        } finally {
            setLoading(false);
        }
    };

    return (
        <Modal
            open
            onClose={onClose}
            title={isEdit ? '编辑模型配置' : '接入新模型'}
            className="max-w-3xl"
        >
            <form onSubmit={handleSubmit} className="max-h-[70vh] overflow-y-auto -m-1 p-1">
                    {/* Hidden Provider Select - Auto Handled */}
                    <input type="hidden" value={formData.provider_id} />

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                        {/* Left Column: Basic Info */}
                        <div className="space-y-4">
                            {!isEdit && (
                                <div className="space-y-1.5">
                                    <label className="text-xs font-medium text-text-secondary">选择预设</label>
                                    <div className="relative">
                                        <select
                                            onChange={handlePresetChange}
                                            className="w-full bg-surface-2 border border-transparent rounded-lg pl-3 pr-8 py-2.5 text-sm text-text focus:border-accent/50 outline-none appearance-none transition-colors"
                                            defaultValue=""
                                        >
                                            <option value="" disabled>请选择模型</option>
                                            {MODEL_PRESETS.map(p => (
                                                <option key={p.value} value={p.value}>{p.label}</option>
                                            ))}
                                        </select>
                                        <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-text-secondary">
                                            <Search size={14} />
                                        </div>
                                    </div>
                                </div>
                            )}

                            <div className="space-y-1.5">
                                <label className="text-xs font-medium text-text-secondary">
                                    模型ID / Endpoint ID <span className="text-danger">*</span>
                                </label>
                                <input 
                                    type="text" 
                                    value={formData.name}
                                    onChange={e => setFormData({...formData, name: e.target.value})}
                                    className="w-full bg-surface-2 border border-transparent rounded-lg p-2.5 text-sm text-text font-mono focus:border-accent/50 outline-none transition-colors"
                                    placeholder="e.g. gpt-4, ep-202406..."
                                    required
                                />
                                <p className="text-[10px] text-text-secondary leading-tight">
                                    OpenAI等标准协议填写模型名(如 gpt-4)；火山引擎等私有部署填写 Endpoint ID。
                                </p>
                            </div>

                            <div className="space-y-1.5">
                                <label className="text-xs font-medium text-text-secondary">
                                    显示名称 <span className="text-danger">*</span>
                                </label>
                                <input 
                                    type="text" 
                                    value={formData.display_name}
                                    onChange={e => setFormData({...formData, display_name: e.target.value})}
                                    className="w-full bg-surface-2 border border-transparent rounded-lg p-2.5 text-sm text-text focus:border-accent/50 outline-none transition-colors"
                                    placeholder="e.g. GPT-4 Turbo"
                                    required
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-1.5">
                                    <label className="text-xs font-medium text-text-secondary">上下文窗口</label>
                                    <input 
                                        type="text" 
                                        value={formData.context_window}
                                        onChange={e => setFormData({...formData, context_window: e.target.value})}
                                        className="w-full bg-surface-2 border border-transparent rounded-lg p-2.5 text-sm text-text"
                                        placeholder="e.g. 128k"
                                    />
                                </div>
                                <div className="space-y-1.5">
                                    <label className="text-xs font-medium text-text-secondary">模型类型</label>
                                    <div className="relative">
                                        <select
                                            value={formData.type}
                                            onChange={e => setFormData({...formData, type: e.target.value})}
                                            className="w-full bg-surface-2 border border-transparent rounded-lg pl-3 pr-8 py-2.5 text-sm text-text focus:border-accent/50 outline-none appearance-none"
                                        >
                                            <option value="LLM">LLM</option>
                                            <option value="Embedding">Embedding</option>
                                        </select>
                                        <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-text-secondary">
                                            <svg width="10" height="6" viewBox="0 0 10 6" fill="none" xmlns="http://www.w3.org/2000/svg">
                                                <path d="M1 1L5 5L9 1" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                                            </svg>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Right Column: API & Config */}
                        <div className="space-y-4">
                            <div className="space-y-1.5">
                                <label className="text-xs font-medium text-text-secondary">API 地址</label>
                                <input 
                                    type="text" 
                                    value={formData.base_url}
                                    onChange={e => setFormData({...formData, base_url: e.target.value})}
                                    className="w-full bg-surface-2 border border-transparent rounded-lg p-2.5 text-sm text-text font-mono focus:border-accent/50 outline-none transition-colors"
                                    placeholder="https://api.openai.com/v1"
                                />
                            </div>
                            
                            <div className="space-y-1.5">
                                <label className="text-xs font-medium text-text-secondary">API Key</label>
                                <textarea 
                                    value={formData.api_key}
                                    onChange={e => setFormData({...formData, api_key: e.target.value})}
                                    className="w-full h-[120px] bg-surface-2 border border-transparent rounded-lg p-2.5 text-sm text-text font-mono focus:border-accent/50 outline-none transition-colors resize-none"
                                    placeholder="sk-..."
                                />
                            </div>

                            <div className="bg-text/5 rounded-lg p-3 space-y-2">
                                <label className="flex items-start gap-3 cursor-pointer p-1.5 rounded hover:bg-text/5 transition-colors border-b border-separator pb-2 mb-2">
                                    <input 
                                        type="checkbox" 
                                        checked={formData.is_active}
                                        onChange={e => setFormData({...formData, is_active: e.target.checked})}
                                        className="w-4 h-4 mt-0.5 rounded border-separator bg-surface-2 text-success focus:ring-offset-0 focus:ring-0"
                                    />
                                    <div className="flex flex-col">
                                        <span className="text-sm text-text">启用模型</span>
                                        <span className="text-[10px] text-text-secondary">禁用后将无法在聊天中使用</span>
                                    </div>
                                </label>

                                <label className="flex items-center gap-3 cursor-pointer p-1.5 rounded hover:bg-text/5 transition-colors">
                                    <input 
                                        type="checkbox" 
                                        checked={formData.supports_geo}
                                        onChange={e => setFormData({...formData, supports_geo: e.target.checked})}
                                        className="w-4 h-4 rounded border-separator bg-surface-2 text-accent focus:ring-offset-0 focus:ring-0"
                                    />
                                    <span className="text-sm text-text">支持 GEO 搜索</span>
                                </label>
                                
                                <label className="flex items-start gap-3 cursor-pointer p-1.5 rounded hover:bg-text/5 transition-colors">
                                    <input 
                                        type="checkbox" 
                                        checked={formData.is_default}
                                        onChange={e => setFormData({...formData, is_default: e.target.checked})}
                                        className="w-4 h-4 mt-0.5 rounded border-separator bg-surface-2 text-accent focus:ring-offset-0 focus:ring-0"
                                    />
                                    <div className="flex flex-col">
                                        <span className="text-sm text-text">设为默认模型</span>
                                        <span className="text-[10px] text-text-secondary">未指定模型时优先使用</span>
                                    </div>
                                </label>

                                <label className="flex items-start gap-3 cursor-pointer p-1.5 rounded hover:bg-text/5 transition-colors">
                                    <input 
                                        type="checkbox" 
                                        checked={formData.is_kb_search_default}
                                        onChange={e => setFormData({...formData, is_kb_search_default: e.target.checked})}
                                        className="w-4 h-4 mt-0.5 rounded border-separator bg-surface-2 text-accent focus:ring-offset-0 focus:ring-0"
                                    />
                                    <div className="flex flex-col">
                                        <span className="text-sm text-text">默认知识库搜索</span>
                                        <span className="text-[10px] text-text-secondary">知识库相关任务优先使用</span>
                                    </div>
                                </label>
                            </div>
                        </div>
                    </div>

                    <div className="flex justify-end gap-2 pt-4 border-t border-separator">
                        <Button 
                            type="button" 
                            variant="outline"
                            onClick={onClose}
                        >
                            取消
                        </Button>
                        <Button 
                            type="submit" 
                            disabled={loading}
                        >
                            {loading ? '保存中...' : '保存配置'}
                        </Button>
                    </div>
                </form>
        </Modal>
    )
}

function StatusBadge({ active }: { active: boolean }) {
    return (
        <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium ${active ? 'bg-success/10 text-success' : 'bg-danger/10 text-danger'}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${active ? 'bg-success' : 'bg-danger'}`}></span>
            {active ? '已启用' : '已禁用'}
        </span>
    )
}

function FilterButton({ label, active }: any) {
    return (
        <button className={`px-3 h-10 rounded-md text-xs font-medium border transition-colors ${active ? 'bg-accent/15 text-accent border-accent/25' : 'bg-text/5 text-text-secondary border-separator hover:bg-text/10'}`}>
            {label}
        </button>
    )
}
