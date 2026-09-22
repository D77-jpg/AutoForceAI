"use client";
import React, { useEffect, useState, useRef } from 'react';
import { User, Phone, Mail, FileText, CheckCircle, XCircle, Save, Loader2, PenLine, Camera } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useToast } from "@/contexts/ToastContext";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/ui/empty-state";

export default function UserProfilePage() {
    const router = useRouter();
    const { showToast } = useToast();
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [uploadingAvatar, setUploadingAvatar] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);
    
    // Signature Editing State
    const [isEditingSignature, setIsEditingSignature] = useState(false);
    const [tempSignature, setTempSignature] = useState('');

    const [profile, setProfile] = useState<any>({
        username: '',
        nickname: '',
        email: '',
        phone: '',
        bio: '', // Used as Signature
        is_wechat_bound: false,
        role: '',
        avatar: '',
        organization_id: ''
    });

    useEffect(() => {
        fetchProfile();
    }, []);

    const fetchProfile = async () => {
        try {
            const token = localStorage.getItem('token');
            if (!token) {
                router.push('/login');
                return;
            }

            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8010'}/auth/me`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (res.ok) {
                const data = await res.json();
                setProfile(data);
                if (data.bio) setTempSignature(data.bio);
                
                // Update local storage user just in case basic info changed
                const localUser = JSON.parse(localStorage.getItem('user') || '{}');
                localStorage.setItem('user', JSON.stringify({ ...localUser, ...data }));
            } else {
                if (res.status === 401) {
                    router.push('/login');
                } else {
                    console.error("Failed to fetch profile");
                }
            }
        } catch (error) {
            console.error("Error fetching profile", error);
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        // Validation
        if (profile.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(profile.email)) {
            showToast('请输入有效的邮箱地址', 'error');
            return;
        }
        if (profile.phone && !/^1[3-9]\d{9}$/.test(profile.phone)) {
             showToast('请输入有效的手机号码', 'error');
             return;
        }

        setSaving(true);
        try {
            const token = localStorage.getItem('token');
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8010'}/auth/profile`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    nickname: profile.nickname, // Now editable
                    email: profile.email,       // Now editable
                    phone: profile.phone,
                    bio: profile.bio
                })
            });

            if (res.ok) {
                showToast('个人资料已更新', 'success');
                fetchProfile();
            } else {
                showToast('更新失败，请重试', 'error');
            }
        } catch (error) {
            showToast('网络错误', 'error');
        } finally {
            setSaving(false);
        }
    };
    
    // Avatar Upload Logic
    const handleAvatarClick = () => {
        fileInputRef.current?.click();
    };
    
    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;
        
        // Basic validation
        if (file.size > 5 * 1024 * 1024) {
            showToast('图片大小不能超过 5MB', 'error');
            return;
        }
        
        setUploadingAvatar(true);
        const formData = new FormData();
        formData.append('file', file);
        
        try {
             const token = localStorage.getItem('token');
             const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8010'}/api/v1/storage/upload/avatar`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                },
                body: formData
            });
            
            if (res.ok) {
                const data = await res.json();
                const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8010';
                
                const fullUrl = data.url.startsWith('http') ? data.url : `${apiUrl}${data.url}`;
                
                setProfile((prev: any) => ({...prev, avatar: fullUrl}));
                showToast('头像上传成功', 'success');
                
                // Immediately update user profile with new avatar URL
                await updateProfileAvatar(fullUrl);
                
            } else {
                showToast('头像上传失败', 'error');
            }
        } catch(err) {
             console.error(err);
             showToast('上传出错', 'error');
        } finally {
            setUploadingAvatar(false);
            if (fileInputRef.current) fileInputRef.current.value = '';
        }
    };
    
    const updateProfileAvatar = async (avatarUrl: string) => {
        const token = localStorage.getItem('token');
        await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8010'}/auth/profile`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ avatar: avatarUrl })
        });
        // Refresh full profile
        fetchProfile();
    };
    
    // Signature Logic
    const openSignatureEdit = () => {
        setTempSignature(profile.bio || '');
        setIsEditingSignature(true);
    };
    
    const saveSignature = async () => {
        setIsEditingSignature(false);
        // Optimistic update
        setProfile((prev: any) => ({...prev, bio: tempSignature }));
        
        try {
             const token = localStorage.getItem('token');
             await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8010'}/auth/profile`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ bio: tempSignature })
            });
            showToast('个性签名已更新', 'success');
        } catch(e) {
            showToast('签名保存失败', 'error');
        }
    };

    if (loading) {
        return (
            <EmptyState
                icon={Loader2}
                size="sm"
                title="正在加载个人资料…"
                className="p-12"
            />
        );
    }

    return (
        <div className="p-8 max-w-4xl mx-auto animate-fade-in">
            <PageHeader
                title="用户中心"
                description="管理您的个人资料、联系方式与账户绑定。"
            />

            <div className="grid grid-cols-1 md:grid-cols-12 gap-8">
                {/* Left Column: Avatar & Signature Area (4 cols) */}
                <div className="md:col-span-4">
                    <div className="glass-card p-6 rounded-xl flex flex-col items-center text-center relative group">
                        <div 
                            className="w-32 h-32 rounded-full bg-surface-2 flex items-center justify-center border-4 border-separator shadow-xl mb-4 overflow-hidden relative cursor-pointer group-hover:border-accent/40 transition-all duration-300"
                            onClick={!uploadingAvatar ? handleAvatarClick : undefined}
                        >
                             {profile.avatar ? (
                                <img src={profile.avatar} alt="Avatar" className="w-full h-full object-cover" />
                             ) : (
                                <span className="text-4xl font-bold text-text-secondary">
                                    {(profile.nickname || profile.username || 'U')?.[0]?.toUpperCase()}
                                </span>
                             )}
                             
                             {/* Overlay for upload hint */}
                             <div className="absolute inset-0 bg-bg/60 flex flex-col items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity backdrop-blur-sm">
                                 {uploadingAvatar ? (
                                     <Loader2 className="animate-spin text-text mb-1" size={24} /> 
                                 ) : (
                                     <>
                                        <Camera className="text-text mb-1" size={24} />
                                        <span className="text-[10px] text-text/80">更换头像</span>
                                     </>
                                 )}
                             </div>
                        </div>
                        <input 
                            type="file" 
                            ref={fileInputRef} 
                            className="hidden" 
                            accept="image/*"
                            onChange={handleFileChange}
                        />

                        <h2 className="text-xl font-bold text-text mb-2 tracking-tight">
                            {profile.nickname || profile.username}
                        </h2>
                        {/* ID and Role tags removed as requested */}
                        
                        {/* Signature Area */}
                        
                        {!isEditingSignature ? (
                             <div 
                                className="w-full text-center p-2 rounded-lg hover:bg-text/5 transition-colors cursor-pointer group/sig relative border border-transparent hover:border-separator"
                                onClick={openSignatureEdit}
                             >
                                 <p className={`text-sm leading-relaxed ${profile.bio ? 'text-text' : 'text-text-tertiary italic'}`}>
                                     {profile.bio || "点击此处添加个性签名..."}
                                 </p>
                                <div className="absolute top-2 right-2 opacity-0 group-hover/sig:opacity-100 transition-opacity">
                                     <PenLine size={12} className="text-accent" />
                                </div>
                             </div>
                        ) : (
                            <div className="w-full space-y-2 animate-in fade-in zoom-in-95 duration-200">
                                <textarea
                                    value={tempSignature}
                                    onChange={(e) => setTempSignature(e.target.value)}
                                    className="w-full bg-bg border border-accent/40 rounded-lg p-3 text-sm text-text focus:outline-none resize-none placeholder:text-text-tertiary"
                                    rows={3}
                                    placeholder="输入个性签名..."
                                    autoFocus
                                    onBlur={(e) => {
                                        // Optional: save on blur or specific logic
                                    }}
                                />
                                <div className="flex gap-2 justify-end">
                                    <button 
                                        onClick={() => setIsEditingSignature(false)}
                                        className="text-xs text-text-secondary hover:text-text px-2 py-1 transition-colors"
                                    >取消</button>
                                    <button 
                                        onClick={saveSignature}
                                        className="text-xs bg-accent hover:bg-accent-hover text-on-accent px-3 py-1 rounded transition-colors"
                                    >保存</button>
                                </div>
                            </div>
                        )}
                        
                        
                        <div className="mt-8 w-full pt-6 border-t border-separator">
                            <div className="flex items-center justify-between text-sm mb-3">
                                <span className="text-text-secondary">微信绑定</span>
                                {profile.is_wechat_bound ? (
                                    <span className="flex items-center text-success text-xs font-medium">
                                        <CheckCircle size={14} className="mr-1.5" /> 已绑定
                                    </span>
                                ) : (
                                    <span className="flex items-center text-text-secondary text-xs">
                                        <XCircle size={14} className="mr-1.5" /> 未绑定
                                    </span>
                                )}
                            </div>
                            <div className="flex items-center justify-between text-sm">
                                <span className="text-text-secondary">组织 ID</span>
                                <span className="text-text font-mono text-xs bg-surface-2 px-1.5 py-0.5 rounded">
                                    {profile.organization_id || '未分配'}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Right Column: Edit Form (8 cols) */}
                <div className="md:col-span-8 space-y-6">
                    <div className="glass-card p-8 rounded-xl space-y-6">
                        <div className="flex items-center justify-between border-b border-separator pb-4 mb-2">
                            <h3 className="text-lg font-semibold text-text">账户资料</h3>
                            <span className="text-xs text-text-secondary">如果不保存，更改将丢失</span>
                        </div>
                        
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div className="md:col-span-2">
                                <label className="block text-xs font-medium text-text-secondary mb-2">显示昵称</label>
                                <div className="relative group">
                                    <User className="absolute left-3 top-3 text-text-secondary group-focus-within:text-accent transition-colors" size={18} />
                                    <input 
                                        type="text" 
                                        value={profile.nickname || ''} 
                                        onChange={(e) => setProfile({...profile, nickname: e.target.value})}
                                        className="w-full bg-surface/70 border border-separator rounded-xl py-2.5 pl-10 pr-3 text-text text-sm focus:border-accent focus:ring-1 focus:ring-accent outline-none transition-all placeholder:text-text-tertiary"
                                        placeholder="设置您的显示名称"
                                    />
                                </div>
                            </div>
                            
                            <div>
                                <label className="block text-xs font-medium text-text-secondary mb-2">系统用户 ID (不可修改)</label>
                                <div className="relative">
                                    <span className="absolute left-3 top-3 text-text-tertiary font-mono text-xs">#</span>
                                    <input 
                                        type="text" 
                                        value={profile.username || ''} 
                                        disabled
                                        className="w-full bg-surface/50 border border-separator rounded-xl py-2.5 pl-8 pr-3 text-text-secondary text-sm cursor-not-allowed font-mono"
                                    />
                                </div>
                            </div>

                            <div>
                                <label className="block text-xs font-medium text-text-secondary mb-2">手机号码</label>
                                <div className="relative group">
                                    <Phone className="absolute left-3 top-3 text-text-secondary group-focus-within:text-accent transition-colors" size={18} />
                                    <input 
                                        type="text" 
                                        value={profile.phone || ''}
                                        onChange={(e) => setProfile({...profile, phone: e.target.value})}
                                        placeholder="输入手机号码"
                                        className="w-full bg-surface/70 border border-separator rounded-xl py-2.5 pl-10 pr-3 text-text text-sm focus:border-accent focus:ring-1 focus:ring-accent outline-none transition-all placeholder:text-text-tertiary"
                                    />
                                </div>
                            </div>
                            
                            <div className="md:col-span-2">
                                <label className="block text-xs font-medium text-text-secondary mb-2">联系邮箱</label>
                                <div className="relative group">
                                    <Mail className="absolute left-3 top-3 text-text-secondary group-focus-within:text-accent transition-colors" size={18} />
                                    <input 
                                        type="email" 
                                        value={profile.email || ''} 
                                        onChange={(e) => setProfile({...profile, email: e.target.value})}
                                        placeholder="name@company.com"
                                        className="w-full bg-surface/70 border border-separator rounded-xl py-2.5 pl-10 pr-3 text-text text-sm focus:border-accent focus:ring-1 focus:ring-accent outline-none transition-all placeholder:text-text-tertiary"
                                    />
                                </div>
                            </div>
                        </div>

                        <div className="pt-8 flex justify-end">
                            <button 
                                onClick={handleSave}
                                disabled={saving}
                                className="flex items-center gap-2 bg-accent hover:bg-accent-hover text-on-accent px-6 py-2.5 rounded-xl text-sm font-medium transition-all shadow-card hover:shadow-card disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none"
                            >
                                {saving ? <Loader2 className="animate-spin" size={18} /> : <Save size={18} />}
                                保存修改
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
