"use client";
import React, { useState, useEffect } from 'react';
import { 
  Users, 
  Search, 
  Loader2, 
  RefreshCw,
  ShieldAlert,
  Building2,
  User as UserIcon,
  Crown
} from 'lucide-react';
import { useToast } from '@/contexts/ToastContext';
import { useAuth } from '@/contexts/AuthContext';
import { PageHeader } from '@/components/PageHeader';
import { EmptyState } from '@/components/ui/empty-state';
import { Modal } from '@/components/ui/modal';
import { Table, TableHead, TableBody, TableRow, TableHeaderCell, TableCell } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

interface User {
    id: number;
    username: string;
    nickname?: string;
    email?: string;
    avatar?: string;
    role: string;
    organization_id?: number;
    organization_name?: string;
    created_at: string;
    is_active: boolean;
}

export default function UsersPage() {
    const { token } = useAuth();
    const { showToast } = useToast();
    const [users, setUsers] = useState<User[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [selectedUser, setSelectedUser] = useState<User | null>(null);

    // Edit form state
    const [editNickname, setEditNickname] = useState('');
    const [editEmail, setEditEmail] = useState('');
    const [editRole, setEditRole] = useState('user');
    const [editActive, setEditActive] = useState(true);
    const [saving, setSaving] = useState(false);

    const API_BASE = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8010'}/api/v1/admin`;

    const fetchUsers = async () => {
        if (!token) return;
        setLoading(true);
        try {
            const res = await fetch(`${API_BASE}/users?limit=100`, {
                headers: { 
                    'Authorization': `Bearer ${token}` 
                }
            });
            if (res.ok) {
                const data = await res.json();
                setUsers(data);
            } else {
                showToast("获取用户列表失败", "error");
            }
        } catch (e) {
            console.error(e);
            showToast("网络连接错误", "error");
        } finally {
            setLoading(false);
            setIsRefreshing(false);
        }
    };

    useEffect(() => {
        if (token) fetchUsers();
    }, [token]);

    const handleRefresh = () => {
        setIsRefreshing(true);
        fetchUsers();
    };

    const openUserDetail = (user: User) => {
        setSelectedUser(user);
        setEditNickname(user.nickname || '');
        setEditEmail(user.email || '');
        setEditRole(user.role || 'user');
        setEditActive(user.is_active !== false);
    };

    const handleSave = async () => {
        if (!selectedUser || !token) return;
        setSaving(true);
        try {
            const res = await fetch(`${API_BASE}/users/${selectedUser.id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({
                    nickname: editNickname || null,
                    email: editEmail || null,
                    role: editRole,
                    is_active: editActive,
                })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || '保存失败');
            showToast("用户资料已更新", "success");
            setSelectedUser(null);
            fetchUsers();
        } catch (e: any) {
            showToast(e.message || "保存失败", "error");
        } finally {
            setSaving(false);
        }
    };

    const filteredUsers = users.filter(u => 
        (u.username && u.username.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (u.nickname && u.nickname.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (u.email && u.email.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (u.organization_name && u.organization_name.toLowerCase().includes(searchQuery.toLowerCase()))
    );

    const getRoleBadge = (role: string) => {
        switch(role) {
            case 'admin':
                return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-danger/10 text-danger border border-danger/20"><ShieldAlert size={12}/> 系统管理员</span>;
            case 'enterprise_admin':
                 return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-accent/10 text-accent border border-accent/20"><Crown size={12}/> 企业管理员</span>;
            default:
                 return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-surface-2 text-text-secondary border border-separator"><UserIcon size={12}/> 普通账号</span>;
        }
    };

    return (
        <div className="h-full flex flex-col bg-bg overflow-hidden">
             {/* Header */}
             <div className="flex-none px-6 pt-6">
                <PageHeader
                    title="用户管理"
                    description="管理系统所有注册用户及其权限"
                    className="mb-0"
                    actions={
                        <>
                            <div className="relative w-64">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-tertiary pointer-events-none" />
                                <Input
                                    placeholder="搜索用户名、邮箱或企业..."
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
                                <RefreshCw size={16} className={isRefreshing ? "animate-spin" : ""} />
                            </Button>
                        </>
                    }
                />
            </div>

            {/* Content */}
            <div className="flex-1 overflow-auto p-6">
                <div className="bg-surface border border-separator rounded-xl overflow-hidden min-h-[500px] flex flex-col">
                    {loading ? (
                         <div className="flex-1 flex flex-col items-center justify-center text-text-secondary gap-3">
                            <Loader2 className="animate-spin text-accent" size={32} />
                            <p className="text-sm">正在加载用户列表...</p>
                        </div>
                    ) : filteredUsers.length === 0 ? (
                        <div className="flex-1 flex flex-col items-center justify-center">
                             <EmptyState
                                icon={Users}
                                title="暂无符合条件的用户"
                                description="尝试调整搜索关键词，或稍后刷新重试"
                                size="sm"
                             />
                        </div>
                    ) : (
                        <Table>
                            <TableHead>
                                <TableRow>
                                    <TableHeaderCell>用户</TableHeaderCell>
                                    <TableHeaderCell>角色</TableHeaderCell>
                                    <TableHeaderCell>所属企业</TableHeaderCell>
                                    <TableHeaderCell>状态</TableHeaderCell>
                                    <TableHeaderCell>注册时间</TableHeaderCell>
                                    <TableHeaderCell className="text-right">操作</TableHeaderCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {filteredUsers.map(user => (
                                    <TableRow key={user.id}>
                                        <TableCell>
                                            <div className="flex items-center gap-3">
                                                <div className="w-8 h-8 rounded-full bg-surface-2 flex items-center justify-center overflow-hidden border border-separator shrink-0">
                                                    {user.avatar ? (
                                                        <img src={user.avatar} alt={user.username || 'User'} className="w-full h-full object-cover" />
                                                    ) : (
                                                        <UserIcon size={14} className="text-text-secondary" />
                                                    )}
                                                </div>
                                                <div className="flex flex-col">
                                                    <span className="text-text font-medium">{user.nickname || user.username || '未命名用户'}</span>
                                                    <span className="text-text-secondary text-xs">{user.email || '无邮箱'}</span>
                                                </div>
                                            </div>
                                        </TableCell>
                                        <TableCell>
                                            {getRoleBadge(user.role)}
                                        </TableCell>
                                        <TableCell>
                                            {user.organization_name ? (
                                                 <div className="flex items-center gap-2 text-text">
                                                     <Building2 size={14} className="text-accent" />
                                                     {user.organization_name}
                                                 </div>
                                            ) : (
                                                <span className="text-text-tertiary italic">未加入组织</span>
                                            )}
                                        </TableCell>
                                        <TableCell>
                                            <div className="flex items-center gap-2">
                                                <span className={`w-2 h-2 rounded-full ${user.is_active ? 'bg-success' : 'bg-danger'} animate-pulse`}></span>
                                                <span className={user.is_active ? 'text-success' : 'text-danger'}>
                                                    {user.is_active ? '正常' : '禁用'}
                                                </span>
                                            </div>
                                        </TableCell>
                                        <TableCell className="text-text-secondary font-mono text-xs tabular-nums">
                                            {new Date(user.created_at).toLocaleString('zh-CN')}
                                        </TableCell>
                                        <TableCell className="text-right">
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                onClick={() => openUserDetail(user)}
                                                className="text-accent hover:text-accent hover:bg-accent/10"
                                            >
                                                详情
                                            </Button>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    )}
                </div>
            </div>

            {/* User Details Modal */}
            {selectedUser && (
                <Modal
                    open
                    onClose={() => setSelectedUser(null)}
                    title="编辑用户"
                    description={`#${selectedUser.id} · ${selectedUser.username}`}
                    footer={
                        <>
                            <Button variant="outline" onClick={() => setSelectedUser(null)}>
                                取消
                            </Button>
                            <Button onClick={handleSave} disabled={saving}>
                                {saving ? <Loader2 size={14} className="animate-spin mr-2" /> : null}
                                {saving ? '保存中...' : '保存修改'}
                            </Button>
                        </>
                    }
                >
                    <div className="space-y-4">
                        <div className="flex items-center gap-4">
                            <div className="w-14 h-14 rounded-full bg-surface-2 flex items-center justify-center overflow-hidden border border-separator shrink-0">
                                {selectedUser.avatar ? (
                                    <img src={selectedUser.avatar} alt={selectedUser.username || ''} className="w-full h-full object-cover" />
                                ) : (
                                    <UserIcon size={28} className="text-text-secondary" />
                                )}
                            </div>
                            <div>
                                <p className="text-sm font-medium text-text">{selectedUser.nickname || selectedUser.username}</p>
                                <p className="text-xs text-text-secondary mt-0.5">{selectedUser.email || '无邮箱'}</p>
                            </div>
                        </div>
                        <div>
                            <label className="apple-section-label block mb-1.5">显示名称</label>
                            <Input
                                value={editNickname}
                                onChange={(e) => setEditNickname(e.target.value)}
                                placeholder="用户显示名称"
                            />
                        </div>
                        <div>
                            <label className="apple-section-label block mb-1.5">电子邮箱</label>
                            <Input
                                value={editEmail}
                                onChange={(e) => setEditEmail(e.target.value)}
                                placeholder="user@example.com"
                            />
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="apple-section-label block mb-1.5">角色</label>
                                <select
                                    value={editRole}
                                    onChange={(e) => setEditRole(e.target.value)}
                                    className="w-full h-10 bg-surface-2 border border-transparent rounded-md px-3.5 text-[15px] text-text focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-accent/30 focus-visible:border-accent/50 transition-all"
                                >
                                    <option value="user">普通账号</option>
                                    <option value="enterprise_admin">企业管理员</option>
                                    <option value="admin">系统管理员</option>
                                </select>
                            </div>
                            <div>
                                <label className="apple-section-label block mb-1.5">账号状态</label>
                                <button
                                    onClick={() => setEditActive(!editActive)}
                                    className={`w-full h-10 rounded-md text-sm font-medium border transition-colors ${
                                        editActive
                                            ? 'bg-success/10 text-success border-success/30'
                                            : 'bg-danger/10 text-danger border-danger/30'
                                    }`}
                                >
                                    {editActive ? '● 正常（点击禁用）' : '● 已禁用（点击启用）'}
                                </button>
                            </div>
                        </div>

                        <div className="bg-surface-2 rounded-lg p-3 text-xs text-text-secondary flex justify-between">
                            <span>所属企业：{selectedUser.organization_name || '未加入'}</span>
                            <span className="tabular-nums">注册于：{new Date(selectedUser.created_at).toLocaleDateString('zh-CN')}</span>
                        </div>
                    </div>
                </Modal>
            )}
        </div>
    );
}
