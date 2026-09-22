"use client";
import React, { useState, useEffect } from 'react';
import { 
  Building2, 
  Search, 
  Loader2, 
  RefreshCw, 
  Plus, 
  UserPlus, 
  MoreVertical, 
  Trash2, 
  Settings,
  Users,
  Check,
  X 
} from 'lucide-react';
import { useToast } from '@/contexts/ToastContext';
import { useAuth } from '@/contexts/AuthContext';

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
        <div className="h-full flex flex-col bg-black overflow-hidden relative">
             {/* Header */}
             <div className="flex-none p-6 border-b border-white/5 bg-[#1c1c1e] flex items-center justify-between z-20">
                <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-lg bg-[#0a84ff]/16 flex items-center justify-center border border-[#0a84ff]/25">
                        <Building2 className="text-[#0a84ff]" size={20} />
                    </div>
                    <div>
                        <h1 className="text-xl font-bold text-white">企业管理</h1>
                        <p className="text-xs text-slate-400 mt-1">
                            创建与管理多租户企业及管理员
                        </p>
                    </div>
                </div>

                <div className="flex items-center gap-3">
                     <div className="relative w-64">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
                        <input
                            placeholder="搜索企业名称..."
                            className="w-full pl-9 h-9 bg-white/5 border border-white/10 rounded-md text-sm text-slate-300 focus:outline-none focus:border-[#0a84ff]/50 transition-colors"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                        />
                    </div>
                     <button
                         onClick={handleRefresh}
                         className="p-2 text-slate-400 hover:text-white hover:bg-white/5 rounded-lg transition-colors"
                         title="刷新"
                    >
                        <RefreshCw size={18} className={isRefreshing ? "animate-spin" : ""} />
                    </button>
                    <button 
                        onClick={() => setIsCreating(true)}
                        className="flex items-center gap-2 px-4 py-2.5 bg-[#0071e3] hover:bg-[#0077ed] text-white rounded-full text-sm font-medium transition-colors shadow-apple"
                    >
                        <Plus size={16} /> 创建企业
                    </button>
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-auto p-6">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {loading ? (
                         <div className="col-span-full flex flex-col items-center justify-center text-slate-500 min-h-[400px]">
                            <Loader2 className="animate-spin text-[#0a84ff]" size={32} />
                            <p className="mt-4 text-sm">正在加载企业数据...</p>
                        </div>
                    ) : filteredOrgs.length === 0 ? (
                        <div className="col-span-full flex flex-col items-center justify-center text-slate-500 min-h-[400px]">
                             <Building2 size={48} className="opacity-20 mb-4" />
                             <p>暂无企业数据</p>
                        </div>
                    ) : (
                        filteredOrgs.map(org => (
                            <div key={org.id} className="bg-[#1c1c1e] border border-white/5 rounded-xl overflow-hidden hover:border-[#0a84ff]/30 transition-all group relative flex flex-col">
                                <div className="p-6 flex-1 overflow-hidden">
                                    <div className="flex justify-between items-start mb-4">
                                        <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-[#0a84ff]/10 to-[#bf5af2]/10 border border-white/5 flex items-center justify-center">
                                            <span className="text-xl font-bold text-[#0a84ff]">{org.name[0]}</span>
                                        </div>
                                        <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                             <button 
                                                className="p-1.5 hover:bg-white/5 rounded text-slate-400 hover:text-white transition-colors" 
                                                title="成员管理"
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    handleManageMembers(org);
                                                }}
                                            >
                                                <Users size={16}/>
                                            </button>
                                             <button 
                                                className="p-1.5 hover:bg-white/5 rounded text-slate-400 hover:text-white transition-colors" 
                                                title="设置"
                                                onClick={() => openEditModal(org)}
                                            >
                                                <Settings size={16}/>
                                            </button>
                                        </div>
                                    </div>
                                    
                                    <h3 className="text-lg font-bold text-white mb-2 truncate" title={org.name}>{org.name}</h3>
                                    <p className="text-sm text-slate-500 line-clamp-2 h-10 mb-4">
                                        {org.description || "暂无描述"}
                                    </p>
                                    
                                    <div className="space-y-3">
                                        <div className="flex items-center justify-between text-sm py-2 border-t border-white/5">
                                            <span className="text-slate-500">成员数量</span>
                                            <span className="text-slate-200 font-mono">{org.user_count} 人</span>
                                        </div>
                                        <div className="flex items-center gap-2 text-sm py-2 border-t border-white/5">
                                            <span className="text-slate-500 whitespace-nowrap">管理员:</span>
                                            <div className="flex items-center justify-between gap-2 flex-1 min-w-0">
                                                <span className="text-slate-200 font-medium truncate shrink-0 max-w-[100px]" title={org.admin_username || "未设置"}>
                                                    {org.admin_username || <span className="text-slate-600 italic">未设置</span>}
                                                </span>
                                                <div className="flex-1 flex justify-end">
                                                    {org.invite_code ? (
                                                        <div className="flex items-center gap-1 bg-[#0a84ff]/10 border border-[#0a84ff]/20 rounded px-1.5 py-0.5 max-w-full overflow-hidden" onClick={(e) => e.stopPropagation()}>
                                                            <span className="text-xs text-[#0a84ff] font-mono select-all cursor-pointer whitespace-nowrap truncate" 
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
                                                                className="text-[#0a84ff] hover:text-[#64d2ff] p-0.5 rounded-full hover:bg-[#0077ed]/20 transition-colors shrink-0"
                                                                title="刷新邀请码"
                                                                onClick={(e) => handleRefreshInviteCode(org, e)}
                                                            >
                                                                <RefreshCw size={10} />
                                                            </button>
                                                        </div>
                                                    ) : (
                                                        <button 
                                                            className="text-xs text-[#0a84ff] hover:text-[#64d2ff] hover:bg-[#0077ed]/10 px-2 py-1 rounded transition-colors"
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
                        ))
                    )}
                </div>
            </div>

            {/* Create Modal */}
            {isCreating && (
                <div className="absolute inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center animate-in fade-in duration-200">
                    <div className="bg-[#1c1c1e] border border-white/10 rounded-xl p-6 w-[400px] shadow-2xl scale-100 animate-in zoom-in-95 duration-200">
                        <div className="flex justify-between items-center mb-6">
                            <h3 className="text-lg font-bold text-white flex items-center gap-2">
                                <Plus size={20} className="text-[#0a84ff]"/>
                                创建新企业
                            </h3>
                            <button onClick={() => setIsCreating(false)} className="text-slate-500 hover:text-white transition-colors">
                                <X size={20} />
                            </button>
                        </div>
                        
                        <div className="space-y-4">
                            <div>
                                <label className="block text-xs font-bold text-slate-500 uppercase mb-2">企业名称</label>
                                <input 
                                    className="w-full bg-black border border-white/10 rounded-lg p-3 text-slate-200 text-sm focus:outline-none focus:border-[#0a84ff] transition-colors"
                                    placeholder="例如：星之光年"
                                    value={newOrgName}
                                    onChange={e => setNewOrgName(e.target.value)}
                                    autoFocus
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-bold text-slate-500 uppercase mb-2">描述 (可选)</label>
                                <textarea 
                                    className="w-full h-24 bg-black border border-white/10 rounded-lg p-3 text-slate-200 text-sm focus:outline-none focus:border-[#0a84ff] transition-colors resize-none"
                                    placeholder="企业简介..."
                                    value={newOrgDesc}
                                    onChange={e => setNewOrgDesc(e.target.value)}
                                />
                            </div>
                        </div>

                        <div className="flex justify-end gap-3 mt-8">
                            <button 
                                className="px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 transition-colors text-sm"
                                onClick={() => setIsCreating(false)}
                            >
                                取消
                            </button>
                            <button 
                                className="px-6 py-2 rounded-lg bg-[#0071e3] hover:bg-[#0077ed] text-white font-medium transition-colors text-sm shadow-apple"
                                onClick={handleCreateOrg}
                            >
                                立即创建
                            </button>
                        </div>
                    </div>
                </div>
            )}
            {/* Detail / Edit Modal */}
            {selectedOrg && !isMembersModalOpen && (
                <div className="absolute inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center animate-in fade-in duration-200">
                    <div className="bg-[#1c1c1e] border border-white/10 rounded-xl p-6 w-[480px] shadow-2xl scale-100 animate-in zoom-in-95 duration-200">
                        <div className="flex justify-between items-center mb-6">
                            <h3 className="text-lg font-bold text-white flex items-center gap-2">
                                <Building2 size={20} className="text-[#0a84ff]"/>
                                企业详情
                            </h3>
                            <button onClick={() => setSelectedOrg(null)} className="text-slate-500 hover:text-white transition-colors">
                                <X size={20} />
                            </button>
                        </div>
                        
                        <div className="space-y-4">
                            <div>
                                <label className="block text-xs font-bold text-slate-500 uppercase mb-2">企业名称</label>
                                <input 
                                    className="w-full bg-black border border-white/10 rounded-lg p-3 text-slate-200 text-sm focus:outline-none focus:border-[#0a84ff] transition-colors"
                                    value={editName}
                                    onChange={e => setEditName(e.target.value)}
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-bold text-slate-500 uppercase mb-2">描述</label>
                                <textarea 
                                    className="w-full h-24 bg-black border border-white/10 rounded-lg p-3 text-slate-200 text-sm focus:outline-none focus:border-[#0a84ff] transition-colors resize-none"
                                    value={editDesc}
                                    onChange={e => setEditDesc(e.target.value)}
                                />
                            </div>
                             <div className="grid grid-cols-2 gap-4 pt-2">
                                <div className="p-3 bg-white/5 rounded-lg border border-white/5 relative group cursor-pointer" onClick={() => setIsUserSelectorOpen(true)}>
                                    <span className="block text-xs text-slate-500 mb-1">管理员</span>
                                    <div className="flex items-center justify-between">
                                        <span className={`text-sm font-medium truncate max-w-[120px] ${pendingAdmin ? 'text-green-400' : 'text-[#64d2ff]'}`}>
                                            {pendingAdmin ? (pendingAdmin.nickname || pendingAdmin.username) : (selectedOrg.admin_username || "未设置")}
                                        </span>
                                        <div className="p-1 rounded bg-white/10 text-white opacity-0 group-hover:opacity-100 transition-opacity">
                                            <Settings size={12}/>
                                        </div>
                                    </div>
                                    {pendingAdmin && <span className="text-[10px] text-green-500 absolute top-1 right-2">待保存</span>}
                                </div>
                                <div className="p-3 bg-white/5 rounded-lg border border-white/5">
                                    <span className="block text-xs text-slate-500 mb-1">成员数</span>
                                    <span className="text-sm text-slate-200 font-mono">
                                        {selectedOrg.user_count}
                                    </span>
                                </div>
                             </div>
                             <div className="p-3 bg-white/5 rounded-lg border border-white/5">
                                <span className="block text-xs text-slate-500 mb-1">创建时间</span>
                                <span className="text-sm text-slate-400 font-mono">
                                    {new Date(selectedOrg.created_at).toLocaleString()}
                                </span>
                             </div>
                        </div>

                        <div className="flex justify-end gap-3 mt-8">
                            <button 
                                className="px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 transition-colors text-sm"
                                onClick={() => setSelectedOrg(null)}
                            >
                                关闭
                            </button>
                            <button 
                                className="px-6 py-2 rounded-lg bg-[#0071e3] hover:bg-[#0077ed] text-white font-medium transition-colors text-sm shadow-apple"
                                onClick={handleSaveOrg}
                            >
                                保存修改
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* User Selector Modal */}
            {isUserSelectorOpen && (
                <div className="absolute inset-0 bg-black/80 backdrop-blur-sm z-[60] flex items-center justify-center animate-in fade-in duration-200">
                    <div className="bg-[#1c1c1e] border border-white/10 rounded-xl p-6 w-[400px] h-[500px] flex flex-col shadow-2xl scale-100 animate-in zoom-in-95 duration-200">
                        <div className="flex justify-between items-center mb-4 flex-none">
                            <h3 className="text-lg font-bold text-white flex items-center gap-2">
                                <Users size={20} className="text-[#0a84ff]"/>
                                选择管理员
                            </h3>
                            <button onClick={() => setIsUserSelectorOpen(false)} className="text-slate-500 hover:text-white transition-colors">
                                <X size={20} />
                            </button>
                        </div>

                        <div className="relative mb-4 flex-none">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
                            <input
                                placeholder="搜索用户..."
                                className="w-full pl-9 h-9 bg-black border border-white/10 rounded-md text-sm text-slate-300 focus:outline-none focus:border-[#0a84ff] transition-colors"
                                value={searchUserQuery}
                                onChange={(e) => setSearchUserQuery(e.target.value)}
                                autoFocus
                            />
                        </div>

                        <div className="flex-1 overflow-y-auto space-y-1 pr-1">
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
                                            ? 'bg-[#0a84ff]/16 border border-[#0a84ff]/25' 
                                            : 'hover:bg-white/5 border border-transparent'
                                    }`}
                                >
                                    <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center overflow-hidden shrink-0">
                                        <Users size={14} className="text-slate-400" />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <p className="text-sm font-medium text-slate-200 truncate">{user.nickname || user.username || '未命名'}</p>
                                        <div className="flex items-center gap-2">
                                            <p className="text-xs text-slate-500 truncate">{user.email || user.username}</p>
                                            {user.organization_name && (
                                                <span className="text-[10px] bg-slate-700/50 text-slate-400 px-1.5 py-0.5 rounded border border-white/5">
                                                    {user.organization_name}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                    {(pendingAdmin?.id === user.id || (!pendingAdmin && selectedOrg?.admin_username === user.username)) && (
                                        <Check size={14} className="text-[#0a84ff]"/>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}
            {/* Members Management Modal */}
            {isMembersModalOpen && selectedOrg && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-[70] flex items-center justify-center p-4">
                    <div className="bg-[#1c1c1e] border border-white/10 rounded-xl w-[600px] h-[600px] flex flex-col shadow-2xl animate-in zoom-in-95 duration-200">
                        {/* Header */}
                        <div className="flex items-center justify-between p-6 border-b border-white/10">
                            <div>
                                <h3 className="text-xl font-bold text-white flex items-center gap-2">
                                    <Users className="text-[#0a84ff]" size={24}/>
                                    成员管理
                                </h3>
                                <p className="text-sm text-slate-400 mt-1">管理 {selectedOrg.name} 的成员列表</p>
                            </div>
                            <button 
                                onClick={() => { setIsMembersModalOpen(false); setSelectedOrg(null); }}
                                className="text-slate-500 hover:text-white transition-colors p-2 hover:bg-white/5 rounded-lg"
                            >
                                <X size={20} />
                            </button>
                        </div>

                        {/* Content */}
                        <div className="flex-1 overflow-y-auto p-4 space-y-2">
                            {orgUsers.length === 0 ? (
                                <div className="flex flex-col items-center justify-center py-20 text-slate-500 space-y-4">
                                    <Users size={48} className="opacity-20" />
                                    <p>该企业暂无成员</p>
                                </div>
                            ) : (
                                orgUsers.map((user) => (
                                    <div 
                                        key={user.id} 
                                        className="flex items-center justify-between p-3 rounded-lg bg-black/20 border border-white/5 hover:bg-black/40 transition-colors group"
                                    >
                                        <div className="flex items-center gap-3">
                                            <div className="w-10 h-10 rounded-full bg-[#2c2c2e] flex items-center justify-center text-slate-400 font-bold border border-white/5">
                                                {user.nickname?.[0] || user.username?.[0] || '?'}
                                            </div>
                                            <div>
                                                <div className="flex items-center gap-2">
                                                    <span className="text-slate-200 font-medium">
                                                        {user.nickname || user.username}
                                                    </span>
                                                    {user.role === 'enterprise_admin' && (
                                                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#0a84ff]/16 text-[#64d2ff] border border-[#0a84ff]/25">
                                                            管理员
                                                        </span>
                                                    )}
                                                </div>
                                                <div className="text-xs text-slate-500 flex items-center gap-2 mt-0.5">
                                                    <span>ID: {user.id}</span>
                                                    <span>•</span>
                                                    <span>{user.email}</span>
                                                </div>
                                            </div>
                                        </div>

                                        <button
                                            onClick={() => handleRemoveMemberClick(user)}
                                            className="opacity-0 group-hover:opacity-100 p-2 text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 rounded-lg transition-all"
                                            title="移出企业"
                                        >
                                            <Trash2 size={16} />
                                        </button>
                                    </div>
                                ))
                            )}
                        </div>

                        {/* Footer */}
                        <div className="flex items-center justify-end p-4 border-t border-white/10 bg-black/20 rounded-b-xl">
                            <button
                                onClick={() => { setIsMembersModalOpen(false); setSelectedOrg(null); }}
                                className="px-4 py-2 text-sm text-slate-400 hover:text-white transition-colors"
                            >
                                关闭
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Delete Confirmation Modal */}
            {memberToDelete && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-[80] flex items-center justify-center p-4 animate-in fade-in duration-200">
                    <div className="bg-[#1c1c1e] border border-white/10 rounded-xl p-6 w-[400px] shadow-2xl flex flex-col items-center text-center animate-in zoom-in-95 duration-200">
                        <div className="w-12 h-12 rounded-full bg-rose-500/10 flex items-center justify-center mb-4">
                            <Trash2 size={24} className="text-rose-500"/>
                        </div>
                        <h3 className="text-lg font-bold text-white mb-2">确认移出成员？</h3>
                        <p className="text-sm text-slate-400 mb-6">
                            您确定要将 <span className="text-slate-200 font-medium">{memberToDelete.nickname || memberToDelete.username}</span> 从企业中移出吗？
                            此操作无法撤销。
                        </p>
                        <div className="flex gap-3 w-full">
                            <button 
                                className="flex-1 px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 transition-colors text-sm"
                                onClick={() => setMemberToDelete(null)}
                            >
                                取消
                            </button>
                            <button 
                                className="flex-1 px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-medium transition-colors text-sm shadow-lg shadow-rose-500/20"
                                onClick={confirmRemoveMember}
                            >
                                确认移出
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
