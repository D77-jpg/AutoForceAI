"use client";
import React, { useState, useEffect } from 'react';
import { 
  Building2, 
  Search, 
  Loader2, 
  RefreshCw, 
  Plus, 
  Trash2, 
  Settings,
  Users,
  Check
} from 'lucide-react';
import { useToast } from '@/contexts/ToastContext';
import { useAuth } from '@/contexts/AuthContext';
import { PageHeader } from '@/components/PageHeader';
import { EmptyState } from '@/components/ui/empty-state';
import { Modal } from '@/components/ui/modal';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

interface Organization {
    id: number;
    name: string;
    description?: string;
    created_at: string;
    user_count: number;
    admin_username?: string;
    invite_code?: string;
}

interface User {
    id: number;
    username: string;
    nickname?: string;
    email?: string;
    organization_name?: string;
    role?: string;
}

export default function EnterprisesPage() {
    const { token } = useAuth();
    const { showToast } = useToast();
    const [orgs, setOrgs] = useState<Organization[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [isCreating, setIsCreating] = useState(false);
    
    // Create Org State
    const [newOrgName, setNewOrgName] = useState('');
    const [newOrgDesc, setNewOrgDesc] = useState('');
    
    // Edit / Select Org State
    const [selectedOrg, setSelectedOrg] = useState<Organization | null>(null);
    const [editName, setEditName] = useState('');
    const [editDesc, setEditDesc] = useState('');
    const [adminUserId, setAdminUserId] = useState(''); // Keep for fallback or remove later

    // User Selector State
    const [isUserSelectorOpen, setIsUserSelectorOpen] = useState(false);
    const [users, setUsers] = useState<User[]>([]);
    const [searchUserQuery, setSearchUserQuery] = useState('');
    const [pendingAdmin, setPendingAdmin] = useState<User | null>(null);

    // Members Modal State
    const [isMembersModalOpen, setIsMembersModalOpen] = useState(false);
    const [orgUsers, setOrgUsers] = useState<User[]>([]);
    
    // Member Delete Confirmation State
    const [memberToDelete, setMemberToDelete] = useState<User | null>(null);

    const API_BASE = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8010'}/api/v1/admin`;

    const fetchOrgUsers = async (orgId: number) => {
        try {
            const res = await fetch(`${API_BASE}/organizations/${orgId}/users`, {
                 headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            if (res.ok) {
                const data = await res.json();
                setOrgUsers(data);
            }
        } catch (e) {
            showToast("获取成员列表失败", "error");
        }
    };

    const handleManageMembers = (org: Organization) => {
        setSelectedOrg(org);
        setIsMembersModalOpen(true);
        fetchOrgUsers(org.id);
    };

    const handleRemoveMemberClick = (user: User) => {
        setMemberToDelete(user);
    };

    const confirmRemoveMember = async () => {
        if (!selectedOrg || !memberToDelete) return;

        try {
            const res = await fetch(`${API_BASE}/organizations/${selectedOrg.id}/users/${memberToDelete.id}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            if (res.ok) {
                showToast("用户已移出", "success");
                fetchOrgUsers(selectedOrg.id); // Refresh user list
                fetchOrgs(); // Refresh counts
                setMemberToDelete(null); // Close confirmation
            } else {
                showToast("移出失败", "error");
            }
        } catch (e) {
            showToast("操作失败", "error");
        }
    };

    const fetchOrgs = async () => {
        setLoading(true);
        if (!token) return; // Wait for token
        try {
            const res = await fetch(`${API_BASE}/organizations?limit=100`, {
                 headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            if (res.ok) {
                const data = await res.json();
                setOrgs(data);
            } else {
                showToast("获取企业列表失败", "error");
            }
        } catch (e) {
            console.error(e);
            showToast("网络连接错误", "error");
        } finally {
            setLoading(false);
            setIsRefreshing(false);
        }
    };

    const fetchUsers = async () => {
        if (!token) return;
        try {
            const res = await fetch(`${API_BASE}/users?limit=100`, {
                 headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            if (res.ok) {
                const data = await res.json();
                setUsers(data);
            }
        } catch (e) {
            console.error("Failed to fetch users", e);
        }
    };

    useEffect(() => {
        if (token) {
            fetchOrgs();
            fetchUsers();
        }
    }, [token]);

    const handleRefresh = () => {
        setIsRefreshing(true);
        fetchOrgs();
    };

    const handleCreateOrg = async () => {
        if (!newOrgName) return showToast("请输入企业名称", "error");
        
        try {
            const res = await fetch(`${API_BASE}/organizations`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ name: newOrgName, description: newOrgDesc })
            });

            if (res.ok) {
                showToast("企业创建成功", "success");
                setIsCreating(false);
                setNewOrgName('');
                setNewOrgDesc('');
                fetchOrgs();
            } else {
                const err = await res.json();
                showToast(err.detail || "创建失败", "error");
            }
        } catch (e) {
            showToast("网络请求失败", "error");
        }
    };

    const handleRefreshInviteCode = async (org: Organization, e: React.MouseEvent) => {
        e.stopPropagation();
        try {
            const res = await fetch(`${API_BASE}/organizations/${org.id}/invite-code`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            if (res.ok) {
                const data = await res.json();
                showToast(`邀请码已刷新: ${data.invite_code}`, "success");
                
                // Update local state without full reload
                setOrgs(orgs.map(o => o.id === org.id ? { ...o, invite_code: data.invite_code } : o));
            } else {
                showToast("刷新邀请码失败", "error");
            }
        } catch (e) {
            showToast("网络请求失败", "error");
        }
    };

    const handleSaveOrg = async () => {
        if (!selectedOrg) return;
        
        try {
            // 1. Update Org Info
            const res = await fetch(`${API_BASE}/organizations/${selectedOrg.id}`, {
                method: 'PATCH',
                headers: { 
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ name: editName, description: editDesc })
            });

            if (!res.ok) {
                const err = await res.json();
                return showToast(err.detail || "更新信息失败", "error");
            }

            // 2. Update Admin (if changed)
            if (pendingAdmin) {
                const adminRes = await fetch(`${API_BASE}/organizations/${selectedOrg.id}/admin`, {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify({ user_id: pendingAdmin.id })
                });
                
                if (!adminRes.ok) {
                    const err = await adminRes.json();
                    return showToast(err.detail || "设置管理员失败", "error");
                }
            }

            showToast("保存成功", "success");
            setSelectedOrg(null);
            setPendingAdmin(null);
            fetchOrgs();
        } catch (e) {
            showToast("保存失败: 网络错误", "error");
        }
    };

    const openEditModal = (org: Organization) => {
        setEditName(org.name);
        setEditDesc(org.description || '');
        setPendingAdmin(null);
        setSelectedOrg(org);
    };

    const filteredOrgs = orgs.filter(o => 
        o.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (o.description && o.description.toLowerCase().includes(searchQuery.toLowerCase()))
    );

    return (
        <div className="h-full flex flex-col bg-bg overflow-hidden relative">
             {/* Header */}
             <div className="flex-none px-6 pt-6">
                <PageHeader
                    title="企业管理"
                    description="创建与管理多租户企业及管理员"
                    className="mb-0"
                    actions={
                        <>
                            <div className="relative w-64">
                                <Search strokeWidth={1.75} className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-tertiary pointer-events-none" />
                                <Input
                                    placeholder="搜索企业名称..."
                                    className="pl-9"
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                />
                            </div>
                            <Button
                                variant="outline"
                                size="icon"
                                onClick={handleRefresh}
                                title="刷新"
                            >
                                <RefreshCw size={16} strokeWidth={1.75} className={isRefreshing ? "animate-spin" : ""} />
                            </Button>
                            <Button onClick={() => setIsCreating(true)}>
                                <Plus size={16} strokeWidth={1.75} className="mr-2" /> 新建企业
                            </Button>
                        </>
                    }
                />
            </div>

            {/* Content */}
            <div className="flex-1 overflow-auto p-6">
                {loading ? (
                     <div className="flex flex-col items-center justify-center text-text-secondary min-h-[400px]">
                        <Loader2 className="animate-spin text-accent" size={32} strokeWidth={1.75} />
                        <p className="mt-4 text-sm">正在加载企业数据...</p>
                    </div>
                ) : filteredOrgs.length === 0 ? (
                    <EmptyState
                        icon={Building2}
                        title="暂无企业数据"
                        description="创建第一个企业，开始多租户组织管理"
                        actionLabel="新建企业"
                        onAction={() => setIsCreating(true)}
                        size="lg"
                    />
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {filteredOrgs.map(org => (
                            <div key={org.id} className="bg-surface rounded-lg shadow-card hover:shadow-popover overflow-hidden transition-all group relative flex flex-col">
                                <div className="p-6 flex-1 overflow-hidden">
                                    <div className="flex justify-between items-start mb-4">
                                        <div className="w-12 h-12 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center">
                                            <span className="text-xl font-bold text-accent">{org.name[0]}</span>
                                        </div>
                                        <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                             <button 
                                                className="p-1.5 hover:bg-text/5 rounded text-text-secondary hover:text-text transition-colors" 
                                                title="成员管理"
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    handleManageMembers(org);
                                                }}
                                            >
                                                <Users size={16} strokeWidth={1.75}/>
                                            </button>
                                             <button 
                                                className="p-1.5 hover:bg-text/5 rounded text-text-secondary hover:text-text transition-colors" 
                                                title="设置"
                                                onClick={() => openEditModal(org)}
                                            >
                                                <Settings size={16} strokeWidth={1.75}/>
                                            </button>
                                        </div>
                                    </div>
                                    
                                    <h3 className="text-lg font-bold text-text mb-2 truncate" title={org.name}>{org.name}</h3>
                                    <p className="text-sm text-text-secondary line-clamp-2 h-10 mb-4">
                                        {org.description || "暂无描述"}
                                    </p>
                                    
                                    <div className="space-y-3">
                                        <div className="flex items-center justify-between text-sm py-2 border-t border-separator">
                                            <span className="text-text-secondary">成员数量</span>
                                            <span className="text-text font-mono tabular-nums">{org.user_count} 人</span>
                                        </div>
                                        <div className="flex items-center gap-2 text-sm py-2 border-t border-separator">
                                            <span className="text-text-secondary whitespace-nowrap">管理员:</span>
                                            <div className="flex items-center justify-between gap-2 flex-1 min-w-0">
                                                <span className="text-text font-medium truncate shrink-0 max-w-[100px]" title={org.admin_username || "未设置"}>
                                                    {org.admin_username || <span className="text-text-tertiary italic">未设置</span>}
                                                </span>
                                                <div className="flex-1 flex justify-end">
                                                    {org.invite_code ? (
                                                        <div className="flex items-center gap-1 bg-accent/10 border border-accent/20 rounded px-1.5 py-0.5 max-w-full overflow-hidden" onClick={(e) => e.stopPropagation()}>
                                                            <span className="text-xs text-accent font-mono select-all cursor-pointer whitespace-nowrap truncate" 
                                                                title="点击复制" 
                                                                onClick={(e) => {
                                                                    e.stopPropagation();
                                                                    navigator.clipboard.writeText(org.invite_code || '')
                                                                    showToast("邀请码已复制", "success");
                                                                }}
                                                            >
                                                                企业邀请码：{org.invite_code}
                                                            </span>
                                                            <button 
                                                                className="text-accent hover:text-accent p-0.5 rounded-full hover:bg-accent-hover/20 transition-colors shrink-0"
                                                                title="刷新邀请码"
                                                                onClick={(e) => handleRefreshInviteCode(org, e)}
                                                            >
                                                                <RefreshCw size={10} strokeWidth={1.75} />
                                                            </button>
                                                        </div>
                                                    ) : (
                                                        <button 
                                                            className="text-xs text-accent hover:text-accent hover:bg-accent-hover/10 px-2 py-1 rounded transition-colors"
                                                            onClick={(e) => handleRefreshInviteCode(org, e)}
                                                        >
                                                            生成邀请码
                                                        </button>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Create Modal */}
            <Modal
                open={isCreating}
                onClose={() => setIsCreating(false)}
                title="新建企业"
                footer={
                    <>
                        <Button variant="outline" onClick={() => setIsCreating(false)}>
                            取消
                        </Button>
                        <Button onClick={handleCreateOrg}>
                            立即创建
                        </Button>
                    </>
                }
            >
                <div className="space-y-4">
                    <div>
                        <label className="apple-section-label block mb-1.5">企业名称</label>
                        <Input 
                            placeholder="例如：星之光年"
                            value={newOrgName}
                            onChange={e => setNewOrgName(e.target.value)}
                            autoFocus
                        />
                    </div>
                    <div>
                        <label className="apple-section-label block mb-1.5">描述（可选）</label>
                        <textarea 
                            className="w-full h-24 bg-surface-2 border border-transparent rounded-md px-3.5 py-2 text-[15px] text-text placeholder:text-text-tertiary focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-accent/30 focus-visible:border-accent/50 transition-all resize-none"
                            placeholder="企业简介..."
                            value={newOrgDesc}
                            onChange={e => setNewOrgDesc(e.target.value)}
                        />
                    </div>
                </div>
            </Modal>

            {/* Detail / Edit Modal */}
            {selectedOrg && !isMembersModalOpen && (
                <Modal
                    open
                    onClose={() => setSelectedOrg(null)}
                    title="企业详情"
                    footer={
                        <>
                            <Button variant="outline" onClick={() => setSelectedOrg(null)}>
                                关闭
                            </Button>
                            <Button onClick={handleSaveOrg}>
                                保存修改
                            </Button>
                        </>
                    }
                >
                    <div className="space-y-4">
                        <div>
                            <label className="apple-section-label block mb-1.5">企业名称</label>
                            <Input 
                                value={editName}
                                onChange={e => setEditName(e.target.value)}
                            />
                        </div>
                        <div>
                            <label className="apple-section-label block mb-1.5">描述</label>
                            <textarea 
                                className="w-full h-24 bg-surface-2 border border-transparent rounded-md px-3.5 py-2 text-[15px] text-text placeholder:text-text-tertiary focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-accent/30 focus-visible:border-accent/50 transition-all resize-none"
                                value={editDesc}
                                onChange={e => setEditDesc(e.target.value)}
                            />
                        </div>
                         <div className="grid grid-cols-2 gap-4 pt-2">
                            <div className="p-3 bg-surface-2 rounded-lg border border-separator relative group cursor-pointer" onClick={() => setIsUserSelectorOpen(true)}>
                                <span className="block text-xs text-text-secondary mb-1">管理员</span>
                                <div className="flex items-center justify-between">
                                    <span className="text-sm font-medium truncate max-w-[120px] text-accent">
                                        {pendingAdmin ? (pendingAdmin.nickname || pendingAdmin.username) : (selectedOrg.admin_username || "未设置")}
                                    </span>
                                    <div className="p-1 rounded bg-text/10 text-text opacity-0 group-hover:opacity-100 transition-opacity">
                                        <Settings size={12} strokeWidth={1.75}/>
                                    </div>
                                </div>
                                {pendingAdmin && <span className="text-[10px] text-accent absolute top-1 right-2">待保存</span>}
                            </div>
                            <div className="p-3 bg-surface-2 rounded-lg border border-separator">
                                <span className="block text-xs text-text-secondary mb-1">成员数</span>
                                <span className="text-sm text-text font-mono tabular-nums">
                                    {selectedOrg.user_count}
                                </span>
                            </div>
                         </div>
                         <div className="p-3 bg-surface-2 rounded-lg border border-separator">
                            <span className="block text-xs text-text-secondary mb-1">创建时间</span>
                            <span className="text-sm text-text-secondary font-mono tabular-nums">
                                {new Date(selectedOrg.created_at).toLocaleString('zh-CN')}
                            </span>
                         </div>
                    </div>
                </Modal>
            )}

            {/* User Selector Modal */}
            <Modal
                open={isUserSelectorOpen}
                onClose={() => setIsUserSelectorOpen(false)}
                title="选择管理员"
            >
                <div className="space-y-4">
                    <div className="relative">
                        <Search strokeWidth={1.75} className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-tertiary pointer-events-none" />
                        <Input
                            placeholder="搜索用户..."
                            className="pl-9"
                            value={searchUserQuery}
                            onChange={(e) => setSearchUserQuery(e.target.value)}
                            autoFocus
                        />
                    </div>

                    <div className="h-[320px] overflow-y-auto space-y-1 pr-1">
                        {users.filter(u => 
                            (u.username && u.username.toLowerCase().includes(searchUserQuery.toLowerCase())) || 
                            (u.nickname && u.nickname.toLowerCase().includes(searchUserQuery.toLowerCase()))
                        ).map(user => (
                            <div 
                                key={user.id}
                                onClick={() => {
                                    setPendingAdmin(user);
                                    setIsUserSelectorOpen(false);
                                }}
                                className={`flex items-center gap-3 p-2 rounded-lg cursor-pointer transition-colors ${
                                    (pendingAdmin?.id === user.id || (!pendingAdmin && selectedOrg?.admin_username === user.username))
                                        ? 'bg-accent/10 border border-accent/40' 
                                        : 'hover:bg-text/5 border border-transparent'
                                }`}
                            >
                                <div className="w-8 h-8 rounded-pill bg-surface-2 flex items-center justify-center overflow-hidden shrink-0">
                                    <Users size={14} strokeWidth={1.75} className="text-text-secondary" />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm font-medium text-text truncate">{user.nickname || user.username || '未命名'}</p>
                                    <div className="flex items-center gap-2">
                                        <p className="text-xs text-text-secondary truncate">{user.email || user.username}</p>
                                        {user.organization_name && (
                                            <span className="text-[10px] bg-surface-2/50 text-text-secondary px-1.5 py-0.5 rounded border border-separator">
                                                {user.organization_name}
                                            </span>
                                        )}
                                    </div>
                                </div>
                                {(pendingAdmin?.id === user.id || (!pendingAdmin && selectedOrg?.admin_username === user.username)) && (
                                    <Check size={14} strokeWidth={1.75} className="text-accent"/>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            </Modal>

            {/* Members Management Modal */}
            {isMembersModalOpen && selectedOrg && (
                <Modal
                    open
                    onClose={() => { setIsMembersModalOpen(false); setSelectedOrg(null); }}
                    title="成员管理"
                    description={`管理 ${selectedOrg.name} 的成员列表`}
                    className="max-w-2xl"
                    footer={
                        <Button variant="outline" onClick={() => { setIsMembersModalOpen(false); setSelectedOrg(null); }}>
                            关闭
                        </Button>
                    }
                >
                    <div className="h-[400px] overflow-y-auto space-y-2">
                        {orgUsers.length === 0 ? (
                            <EmptyState
                                icon={Users}
                                title="该企业暂无成员"
                                description="分享企业邀请码，邀请成员加入"
                                size="sm"
                            />
                        ) : (
                            orgUsers.map((user) => (
                                <div 
                                    key={user.id} 
                                    className="flex items-center justify-between p-3 rounded-lg bg-surface-2 border border-separator hover:bg-surface-2/70 transition-colors group"
                                >
                                    <div className="flex items-center gap-3">
                                        <div className="w-10 h-10 rounded-pill bg-surface flex items-center justify-center text-text-secondary font-bold border border-separator">
                                            {user.nickname?.[0] || user.username?.[0] || '?'}
                                        </div>
                                        <div>
                                            <div className="flex items-center gap-2">
                                                <span className="text-text font-medium">
                                                    {user.nickname || user.username}
                                                </span>
                                                {user.role === 'enterprise_admin' && (
                                                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-accent/10 text-accent border border-accent/20">
                                                        管理员
                                                    </span>
                                                )}
                                            </div>
                                            <div className="text-xs text-text-secondary flex items-center gap-2 mt-0.5">
                                                <span className="tabular-nums">ID: {user.id}</span>
                                                <span>•</span>
                                                <span>{user.email}</span>
                                            </div>
                                        </div>
                                    </div>

                                    <button
                                        onClick={() => handleRemoveMemberClick(user)}
                                        className="opacity-0 group-hover:opacity-100 p-2 text-danger hover:text-danger hover:bg-danger/10 rounded-lg transition-all"
                                        title="移出企业"
                                    >
                                        <Trash2 size={16} strokeWidth={1.75} />
                                    </button>
                                </div>
                            ))
                        )}
                    </div>
                </Modal>
            )}

            {/* Delete Confirmation Modal */}
            {memberToDelete && (
                <Modal
                    open
                    onClose={() => setMemberToDelete(null)}
                    title="确认移出成员？"
                    footer={
                        <>
                            <Button variant="outline" onClick={() => setMemberToDelete(null)}>
                                取消
                            </Button>
                            <Button variant="destructive" onClick={confirmRemoveMember}>
                                确认移出
                            </Button>
                        </>
                    }
                >
                    <p className="text-sm text-text-secondary">
                        您确定要将 <span className="text-text font-medium">{memberToDelete.nickname || memberToDelete.username}</span> 从企业中移出吗？
                        此操作无法撤销。
                    </p>
                </Modal>
            )}
        </div>
    );
}
