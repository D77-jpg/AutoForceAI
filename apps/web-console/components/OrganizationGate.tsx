"use client";
import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Building2, UserPlus, ArrowRight, Loader2, Copy, Check, LogOut, Settings, User, Info, HelpCircle, ChevronDown, Users } from 'lucide-react';
import { useToast } from '../contexts/ToastContext';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';

export default function OrganizationGate({ children }: { children: React.ReactNode }) {
    const { user, login, logout } = useAuth();
    const { showToast } = useToast();
    
    // UI State
    const [mode, setMode] = useState<'selection' | 'create' | 'join'>('selection');
    const [showUserMenu, setShowUserMenu] = useState(false);
    const pathname = usePathname();
    const [loading, setLoading] = useState(false);
    
    // Create Form
    const [createName, setCreateName] = useState('');
    const [createDesc, setCreateDesc] = useState('');
    const [createdCode, setCreatedCode] = useState<string | null>(null);
    const [createdUserData, setCreatedUserData] = useState<any>(null); // Store user data for login
    
    // Join Form
    const [joinName, setJoinName] = useState('');
    const [joinCode, setJoinCode] = useState('');
    
    // Check if API_URL is defined, otherwise fallback
    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8010';
    const API_BASE = `${API_URL}/auth/organization`; // Use config if available

    const refreshUser = async () => {
        try {
            const token = localStorage.getItem('token');
            if (token) {
                const res = await fetch(`${API_URL}/auth/me`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                if (res.ok) {
                    const userData = await res.json();
                    
                    // Always update user context with fresh data
                    login(token, {
                        id: userData.user_id,
                        username: userData.username,
                        role: userData.role,
                        org_id: userData.organization_id, // Normalize key
                        org_name: userData.organization_name,
                        avatar: userData.avatar,
                        nickname: userData.nickname,
                        invite_code: userData.invite_code
                    }); 
                    
                    if (userData.organization_id) {
                         showToast("账户数据已同步", "success");
                         return true;
                    }
                }
            }
        } catch (e) {
            console.error("Failed to refresh profile", e);
        }
        return false;
    };

    // Auto-refresh if user has no org_id OR (org_id but no org_name) (Fix for stale localStorage)
    React.useEffect(() => {
        if (user) {
            // If user has no org, OR if user has org but name is missing in local state
            // This ensures we fetch the name for the UI
            if (!user.org_id || (user.org_id && !user.org_name)) {
                refreshUser();
            }
        }
    }, [user?.org_id, user?.org_name]); // Dependency on props allows re-check if they change

    // Always render children, but overlay if needed
    // Exception: Profile settings logic to allow logout, System Admins might not need an org
    // Note: Even if we return children, the useEffect above will run to fetch org_name if missing
    // FIX: Check user.org_id existence correctly.
    // Allow public routes to bypass the organization gate
    const isPublicRoute = pathname === '/login' || pathname === '/landing' || pathname === '/solution';
    
    // Also bypass if user is not logged in (presumably handled by AuthContext redirect, 
    // but ensures we don't show the Org Gate overlay momentarily)
    if (isPublicRoute || !user || (user && user.org_id) || user?.role === 'admin' || pathname?.startsWith('/settings/profile')) {
        return <>{children}</>;
    }

    const handleCreate = async () => {
        if (!createName) return showToast("请输入企业名称", "error");
        
        const token = localStorage.getItem('token');
        if (!token) {
            showToast("未检测到登录凭证，请重新登录", "error");
            window.location.href = '/login';
            return;
        }

        setLoading(true);
        try {
            console.log("Creating org with token:", token.substring(0, 10) + "...");
            const res = await fetch(`${API_BASE}/create`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ name: createName, description: createDesc })
            });
            const data = await res.json();
            
            if (res.ok) {
                showToast("企业创建成功", "success");
                setCreatedCode(data.invite_code);
                setCreatedUserData(data); // Store for finishCreation
            } else {
                if (res.status === 401) {
                    showToast("登录已过期，请刷新页面", "error");
                    // Force logout or refresh
                    setTimeout(() => window.location.reload(), 1500);
                    return;
                }
                if (data.detail === "You are already in an organization") {
                     showToast("检测到您已加入企业，正在同步...", "info");
                     const refreshed = await refreshUser();
                     if (refreshed) {
                        return; // Successfully refreshed, component should update
                     }
                     // Fallback if refresh failed or no org found in profile
                     showToast("同步失败，请刷新页面重试", "error");
                     return;
                }
                showToast(data.detail || "创建失败", "error");
            }
        } catch (e) {
            showToast("网络请求失败", "error");
        } finally {
            setLoading(false);
        }
    };

    const handleJoin = async () => {
        if (!joinName || !joinCode) return showToast("请填写完整信息", "error");
        
        const token = localStorage.getItem('token');
        if (!token) {
             showToast("未登录，请重新登录", "error");
             window.location.href = '/login';
             return;
        }

        setLoading(true);
        try {
            const res = await fetch(`${API_BASE}/join`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ name: joinName, invite_code: joinCode })
            });
            const data = await res.json();
            
            if (res.ok) {
                showToast("加入成功", "success");
                // Update User Context
                login(data.access_token, {
                    id: data.user_id,
                    username: data.username,
                    nickname: data.nickname,
                    role: data.role,
                    org_id: data.organization_id, // Map from response
                    org_name: joinName, // We know the name because we just joined it
                    avatar: data.avatar
                });
                // Overlay will disappear automatically
            } else {
                if (res.status === 401) {
                    showToast("登录已过期，请刷新页面", "error");
                    setTimeout(() => window.location.reload(), 1500);
                    return;
                }
                showToast(data.detail || "加入失败", "error");
            }
        } catch (e) {
            showToast("网络请求失败", "error");
        } finally {
            setLoading(false);
        }
    };

    const finishCreation = async () => {
         if (createdUserData) {
             const token = localStorage.getItem('token');
             if (token) {
                 // Use the data from creation response to update context
                 login(token, {
                     id: createdUserData.user_id,
                     username: createdUserData.username,
                     nickname: createdUserData.nickname,
                     role: createdUserData.role,
                     org_id: createdUserData.organization_id, 
                     org_name: createName, // Use the name we just created
                     avatar: createdUserData.avatar,
                     invite_code: createdUserData.invite_code
                 });
                 // No need to reload, the state update will unmount the overlay
                 // But let's navigate to root just in case we were on weird route
                 // window.history.pushState({}, '', '/'); 
                 return;
             }
         }
         
         // Fallback if data missing
         window.location.href = '/'; 
    };

    return (
        <div className="relative h-full w-full">
            {/* The main content is rendered but blurred/hidden behind overlay */}
            <div className="absolute inset-0 filter blur-sm pointer-events-none user-select-none" aria-hidden="true">
                {children}
            </div>

            {/* Blocking Overlay */}
            <div className="fixed inset-0 z-[100] bg-black/95 backdrop-blur-md flex flex-col items-center justify-center p-4 animate-in fade-in duration-300">
                
                {/* Header for User Profile */}
                <div className="absolute top-4 right-4 sm:top-8 sm:right-8 z-50">
                    <div className="relative">
                        <button 
                            onClick={() => setShowUserMenu(!showUserMenu)}
                            className="flex items-center gap-3 bg-[#1c1c1e] hover:bg-[#2c2c2e] border border-white/5 rounded-full pl-2 pr-4 py-1.5 transition-colors focus:outline-none"
                        >
                            <div className="relative w-8 h-8 rounded-full overflow-hidden border border-white/10 bg-slate-700">
                                {user?.avatar ? (
                                    <img src={user.avatar} alt="Avatar" className="w-full h-full object-cover" />
                                ) : (
                                    <div className="w-full h-full flex items-center justify-center bg-[#0071e3] text-white font-bold text-xs">
                                        {(user?.nickname || user?.username || 'U')[0].toUpperCase()}
                                    </div>
                                )}
                            </div>
                            <span className="text-sm font-medium text-slate-200">{user?.nickname || user?.username}</span>
                            <ChevronDown size={14} className={`text-slate-400 transition-transform ${showUserMenu ? 'rotate-180' : ''}`} />
                        </button>

                        {/* Dropdown Menu */}
                        {showUserMenu && user && (
                            <div className="absolute top-full right-0 mt-2 w-64 bg-[#1c1c1e] border border-white/10 rounded-xl shadow-2xl py-1 overflow-hidden animate-in fade-in zoom-in-95 duration-200 z-[60]">
                                <div className="px-4 py-3 border-b border-white/5 bg-white/5">
                                    <div className="text-sm font-medium text-white truncate">
                                        <span className="font-semibold text-slate-200">{user.nickname || user.username}</span>
                                        <span className="mx-2 text-slate-500">|</span>
                                        <span className="text-slate-400 font-normal">
                                            {user.org_name || '未加入企业'}
                                        </span>
                                    </div>
                                    <div className="text-xs text-slate-500 truncate mt-0.5">
                                        {user.role === 'admin' ? '系统管理员' : '普通用户'}
                                    </div>
                                </div>
                                <Link 
                                    href="/settings/profile" 
                                    className="flex items-center gap-2 px-4 py-2.5 text-sm text-slate-300 hover:bg-white/5 hover:text-white transition-colors"
                                >
                                    <User size={16} />
                                    用户中心
                                </Link>
                                <div className="h-px bg-white/5 my-1" />
                                <button 
                                    onClick={() => logout()}
                                    className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-red-400 hover:bg-white/5 hover:text-red-300 transition-colors text-left"
                                >
                                    <LogOut size={16} />
                                    退出登录
                                </button>
                            </div>
                        )}
                    </div>
                </div>

                <div className="w-full h-full flex items-center justify-center relative">
                    
                    {/* Centered: Creation/Join Form */}
                    <div className="w-full max-w-md shrink-0 z-10 transition-all duration-500">
                        <div className="text-center mb-10">
                            <div className="mx-auto w-16 h-16 bg-[#0a84ff]/10 rounded-2xl flex items-center justify-center mb-4 border border-[#0a84ff]/20">
                                <Building2 size={32} className="text-[#0a84ff]" />
                            </div>
                            <h1 className="text-2xl font-bold text-white mb-2">欢迎加入数字员工平台</h1>
                            <p className="text-slate-400">为了更好地协作，您需要加入一个企业组织</p>
                        </div>

                        {mode === 'selection' && (
                            <div className="grid gap-4">
                                <button 
                                    onClick={() => setMode('create')}
                                    className="group p-6 bg-[#1c1c1e] hover:bg-[#2c2c2e] border border-white/5 hover:border-[#0a84ff]/30 rounded-xl transition-all flex items-center justify-between text-left"
                                >
                                    <div>
                                        <h3 className="text-lg font-bold text-white mb-1 group-hover:text-[#0a84ff] transition-colors">我是团队负责人</h3>
                                        <p className="text-sm text-slate-400">创建新企业，邀请成员加入</p>
                                    </div>
                                    <ArrowRight size={20} className="text-slate-500 group-hover:text-[#0a84ff] transform group-hover:translate-x-1 transition-all" />
                                </button>

                                <button 
                                    onClick={() => setMode('join')}
                                    className="group p-6 bg-[#1c1c1e] hover:bg-[#2c2c2e] border border-white/5 hover:border-[#0a84ff]/30 rounded-xl transition-all flex items-center justify-between text-left"
                                >
                                    <div>
                                        <h3 className="text-lg font-bold text-white mb-1 group-hover:text-[#0a84ff] transition-colors">我是团队成员</h3>
                                        <p className="text-sm text-slate-400">使用邀请码加入现有团队</p>
                                    </div>
                                    <UserPlus size={20} className="text-slate-500 group-hover:text-[#0a84ff] transform group-hover:translate-x-1 transition-all" />
                                </button>
                            </div>
                        )}

                        {mode === 'create' && !createdCode && (
                            <div className="bg-[#1c1c1e] border border-white/5 rounded-xl p-6 animate-in slide-in-from-bottom-4 duration-300">
                                <div className="flex items-center justify-between mb-6">
                                    <h3 className="text-xl font-bold text-white">创建新企业</h3>
                                    <div className="px-2 py-1 rounded bg-[#0a84ff]/16 text-[#64d2ff] text-xs font-bold border border-[#0a84ff]/25">
                                        负责人模式
                                    </div>
                                </div>
                                <div className="space-y-4">
                                    <div>
                                        <label className="block text-xs font-bold text-slate-500 uppercase mb-2">企业名称</label>
                                        <input 
                                            className="w-full bg-black border border-white/10 rounded-lg p-3 text-slate-200 text-sm focus:outline-none focus:border-[#0a84ff] transition-colors"
                                            placeholder="例如：星之光年"
                                            value={createName}
                                            onChange={e => setCreateName(e.target.value)}
                                            autoFocus
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-xs font-bold text-slate-500 uppercase mb-2">企业描述</label>
                                        <textarea 
                                            className="w-full h-24 bg-black border border-white/10 rounded-lg p-3 text-slate-200 text-sm focus:outline-none focus:border-[#0a84ff] transition-colors resize-none"
                                            placeholder="简单的介绍..."
                                            value={createDesc}
                                            onChange={e => setCreateDesc(e.target.value)}
                                        />
                                    </div>
                                    <div className="flex gap-3 pt-4">
                                        <button 
                                            onClick={() => setMode('selection')}
                                            className="flex-1 py-3 text-slate-400 hover:text-white transition-colors"
                                        >
                                            返回
                                        </button>
                                        <button 
                                            onClick={handleCreate}
                                            disabled={loading}
                                            className="flex-[2] py-3 bg-[#0071e3] hover:bg-[#0077ed] text-white rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
                                        >
                                            {loading ? <Loader2 className="animate-spin" size={18}/> : '立即创建'}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        )}

                        {mode === 'create' && createdCode && (
                            <div className="bg-[#1c1c1e] border border-white/5 rounded-xl p-6 animate-in zoom-in-95 duration-300 text-center">
                                <div className="w-16 h-16 bg-green-500/10 rounded-full flex items-center justify-center mx-auto mb-4 border border-green-500/20">
                                    <Check size={32} className="text-green-500" />
                                </div>
                                <h3 className="text-xl font-bold text-white mb-2">创建成功！</h3>
                                <p className="text-slate-400 text-sm mb-6">
                                    您的企业已创建，您是超级管理员。<br/>
                                    请将下方的邀请码发送给团队成员。
                                </p>
                                
                                <div className="bg-black border border-white/10 rounded-lg p-4 mb-6 flex items-center justify-between group cursor-pointer" onClick={() => {
                                    navigator.clipboard.writeText(createdCode);
                                    showToast("已复制到剪贴板", "success");
                                }}>
                                    <span className="text-2xl font-mono text-[#0a84ff] font-bold tracking-widest">{createdCode}</span>
                                    <Copy size={18} className="text-slate-500 group-hover:text-white transition-colors" />
                                </div>

                                <button 
                                    onClick={finishCreation}
                                    className="w-full py-3 bg-[#0071e3] hover:bg-[#0077ed] text-white rounded-lg font-medium transition-colors"
                                >
                                    进入工作台
                                </button>
                            </div>
                        )}

                        {mode === 'join' && (
                            <div className="bg-[#1c1c1e] border border-white/5 rounded-xl p-6 animate-in slide-in-from-bottom-4 duration-300">
                                <div className="flex items-center justify-between mb-6">
                                    <h3 className="text-xl font-bold text-white">加入企业</h3>
                                    <div className="px-2 py-1 rounded bg-teal-500/20 text-teal-300 text-xs font-bold border border-teal-500/30">
                                        成员模式
                                    </div>
                                </div>
                                <div className="space-y-4">
                                    <div>
                                        <label className="block text-xs font-bold text-slate-500 uppercase mb-2">企业名称</label>
                                        <input 
                                            className="w-full bg-black border border-white/10 rounded-lg p-3 text-slate-200 text-sm focus:outline-none focus:border-[#0a84ff] transition-colors"
                                            placeholder="请输入需加入的企业全称"
                                            value={joinName}
                                            onChange={e => setJoinName(e.target.value)}
                                            autoFocus
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-xs font-bold text-slate-500 uppercase mb-2">邀请码</label>
                                        <input 
                                            className="w-full bg-black border border-white/10 rounded-lg p-3 text-slate-200 text-sm focus:outline-none focus:border-[#0a84ff] transition-colors font-mono tracking-widest"
                                            placeholder="6位邀请码"
                                            value={joinCode}
                                            onChange={e => setJoinCode(e.target.value)}
                                            maxLength={6}
                                        />
                                    </div>
                                    <div className="bg-[#2c2c2e]/60 rounded-lg p-3 flex gap-3 items-start border border-white/5">
                                        <Info size={16} className="text-slate-400 mt-0.5 shrink-0" />
                                        <p className="text-xs text-slate-400 leading-relaxed">
                                            请联系您的企业管理员获取邀请码。只有输入正确的企业名称和对应的邀请码才能成功加入。
                                        </p>
                                    </div>
                                    <div className="flex gap-3 pt-2">
                                        <button 
                                            onClick={() => setMode('selection')}
                                            className="flex-1 py-3 text-slate-400 hover:text-white transition-colors"
                                        >
                                            返回
                                        </button>
                                        <button 
                                            onClick={handleJoin}
                                            disabled={loading}
                                            className="flex-[2] py-3 bg-[#0071e3] hover:bg-[#0077ed] text-white rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
                                        >
                                            {loading ? <Loader2 className="animate-spin" size={18}/> : '验证并加入'}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>

                     {/* Right Side: Guide / Instructions - Absolute Positioned */}
                     <div className="hidden lg:block absolute right-0 top-1/2 -translate-y-1/2 w-full max-w-sm text-left animate-in slide-in-from-right-8 duration-500 delay-100 pr-8">
                        <div className="bg-[#1c1c1e]/50 border border-white/5 rounded-2xl p-6 backdrop-blur-sm">
                            <h3 className="text-white font-bold flex items-center gap-2 mb-4">
                                <HelpCircle size={18} className="text-[#0a84ff]" />
                                操作指引
                            </h3>
                            
                            <div className="space-y-6 relative">
                                {/* Vertical line connecting steps */}
                                <div className="absolute left-3 top-2 bottom-2 w-0.5 bg-[#0a84ff]/16" />

                                <div className="relative pl-10">
                                    <div className="absolute left-0 top-0 w-6 h-6 rounded-full bg-black border-2 border-[#0a84ff] flex items-center justify-center z-10">
                                        <span className="text-[10px] font-bold text-white">1</span>
                                    </div>
                                    <h4 className="text-sm font-bold text-slate-200 mb-1">何时“创建企业”？</h4>
                                    <p className="text-xs text-slate-400 leading-relaxed">
                                        如果您是团队的负责人或管理员，且您的组织尚未在平台上注册，请选择此选项。您将成为该组织的“超级管理员”，拥有最高权限。
                                    </p>
                                </div>

                                <div className="relative pl-10">
                                    <div className="absolute left-0 top-0 w-6 h-6 rounded-full bg-black border-2 border-teal-500 flex items-center justify-center z-10">
                                        <span className="text-[10px] font-bold text-white">2</span>
                                    </div>
                                    <h4 className="text-sm font-bold text-slate-200 mb-1">何时“加入企业”？</h4>
                                    <p className="text-xs text-slate-400 leading-relaxed">
                                        如果您是团队成员，且您的组织已经由管理员创建。请先向管理员索要“邀请码”，然后选择此选项加入。
                                    </p>
                                </div>

                                <div className="relative pl-10">
                                    <div className="absolute left-0 top-0 w-6 h-6 rounded-full bg-black border-2 border-yellow-500 flex items-center justify-center z-10">
                                        <span className="text-[10px] font-bold text-white">3</span>
                                    </div>
                                    <h4 className="text-sm font-bold text-slate-200 mb-1">关于“企业邀请码”</h4>
                                    <p className="text-xs text-slate-400 leading-relaxed">
                                        每个企业有一个唯一的6位邀请码。它就像进门的钥匙。管理员可以在“系统设置”或创建成功页面找到它。
                                    </p>
                                </div>
                            </div>
                        </div> 
                    </div>
                </div>
            </div>
        </div>
    );
}