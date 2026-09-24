"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import Link from 'next/link';
import { useToast } from "../../contexts/ToastContext"; 
import { useAuth } from "../../contexts/AuthContext"; 
import { BrainCircuit, Sparkles, Zap, BarChart3, ScanLine, ShieldCheck, ArrowLeft, Mail, Lock, User as UserIcon } from 'lucide-react';

function getApiBase(): string {
    const envApiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (envApiUrl) return envApiUrl;
    const protocol = window.location.protocol;
    const hostname = window.location.hostname;
    return `${protocol}//${hostname}:8010`;
}

export default function LoginPage() {
  const [loading, setLoading] = useState(false);
  const [wechatUrl, setWechatUrl] = useState<string | null>(null);
  const [isMockMode, setIsMockMode] = useState(true);
  const [authTab, setAuthTab] = useState<'email' | 'wechat'>('email');
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [nickname, setNickname] = useState('');
  const router = useRouter();
  const { showToast } = useToast();
  const { login } = useAuth();

  useEffect(() => {
    // 获取微信登录链接
    const fetchWeChatUrl = async () => {
        try {
            const apiBase = getApiBase();
            const res = await fetch(`${apiBase}/auth/wechat/url`);
            const data = await res.json();
            if (data.url && !data.mock_mode) {
                setWechatUrl(data.url);
                setIsMockMode(false);
            } else {
                setIsMockMode(true);
            }
        } catch (e) {
            console.error("Failed to fetch WeChat URL", e);
            setIsMockMode(true);
        }
    };
    fetchWeChatUrl();
  }, []);

  // 处理微信回调 Login
  useEffect(() => {
    // 仅在客户端执行
    if (typeof window !== 'undefined') {
        const params = new URLSearchParams(window.location.search);
        const code = params.get('code');
        if (code) {
             // 避免重复请求 (React StrictMode 可能导致两次)
             const hasProcessed =  window.sessionStorage.getItem('wx_code_processed');
             if (hasProcessed !== code) {
                 window.sessionStorage.setItem('wx_code_processed', code);
                 // 清除 URL 上的 code 参数，防止刷新重复提交
                 window.history.replaceState({}, document.title, "/login");
                 performLogin(code);
             }
        }
    }
  }, []);

  const performLogin = async (code: string) => {
      setLoading(true);
      try {
        const apiBase = getApiBase();

        const response = await fetch(`${apiBase}/auth/wechat/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code }),
        });

        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || 'Login failed');
        }

        const data = await response.json();
        
        console.log("Login Response Data:", data); // Debug log

        // Ensure we prioritize displaying the nickname, and fallback to username only if absolutely necessary
        const displayName = data.nickname && data.nickname.trim() !== "" ? data.nickname : data.username;
        const displayAvatar = data.avatar || data.headimgurl;

        login(data.access_token, {
            id: data.user_id,
            username: data.username,
            role: data.role,
            org_id: data.organization_id,
            avatar: displayAvatar,
            nickname: displayName,
            invite_code: data.invite_code // Add invite code
        });

        showToast("登录成功！欢迎登录 GlobalPilot AI", "success");
        // Login function handles redirection
        
      } catch (error: any) {
        showToast(error.message || "登录失败，请重试", "error");
        console.error(error);
        // 如果失败，清除处理标记以便重试
        window.sessionStorage.removeItem('wx_code_processed');
      } finally {
        setLoading(false);
      }
  };

  // 邮箱密码 登录/注册
  const handleEmailAuth = async (e: React.FormEvent) => {
      e.preventDefault();
      if (!email || !password) {
          showToast("请输入邮箱和密码", "warning");
          return;
      }
      if (password.length < 6) {
          showToast("密码长度至少 6 位", "warning");
          return;
      }
      setLoading(true);
      try {
          const apiBase = getApiBase();
          const endpoint = isRegister ? '/auth/register' : '/auth/login';
          const body: any = { email: email.trim(), password };
          if (isRegister && nickname.trim()) body.nickname = nickname.trim();

          const response = await fetch(`${apiBase}${endpoint}`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(body),
          });

          if (!response.ok) {
              const errData = await response.json();
              throw new Error(errData.detail || (isRegister ? '注册失败' : '登录失败'));
          }

          const data = await response.json();
          login(data.access_token, {
              id: data.user_id,
              username: data.username,
              role: data.role,
              org_id: data.organization_id,
              avatar: data.avatar,
              nickname: data.nickname || data.username,
              invite_code: data.invite_code
          });
          showToast(isRegister ? "注册成功，欢迎加入！" : "登录成功！", "success");
      } catch (error: any) {
          showToast(error.message || "操作失败，请重试", "error");
      } finally {
          setLoading(false);
      }
  };

  const handleMockLogin = async () => {
    // 模拟一个随机的微信 Code
    const mockCode = "mock_wx_code_" + Math.random().toString(36).substring(7);
    await performLogin(mockCode);
  };

  return (
    <div className="min-h-screen flex w-full bg-bg text-text overflow-hidden font-sans">
      
      <div className="hidden lg:flex flex-col justify-center w-[58%] relative px-20 overflow-hidden">
        
        <div className="absolute top-0 left-0 w-full h-full overflow-hidden z-0 pointer-events-none">
             <div className="absolute top-[-10%] left-[8%] w-[520px] h-[520px] bg-accent/10 rounded-full blur-[140px]"></div>
             <div className="absolute bottom-[0%] right-[8%] w-[420px] h-[420px] bg-text/[0.04] rounded-full blur-[100px]"></div>
        </div>

        <div className="relative z-10 max-w-2xl pl-4">
            <Link href={process.env.NEXT_PUBLIC_OFFICIAL_SITE_URL || "http://localhost:3000"} className="flex items-center gap-3 mb-10 cursor-pointer hover:opacity-80 transition-opacity">
                <div className="relative w-10 h-10 rounded-2xl overflow-hidden bg-surface">
                    <Image 
                        src="/logo.png" 
                        alt="GlobalPilot AI" 
                        fill
                        className="object-contain"
                    />
                </div>
                <span className="text-[17px] font-semibold tracking-tight text-text">
                    GlobalPilot AI
                </span>
            </Link>

            <div className="mb-10">
                <h1 className="text-[52px] font-semibold leading-[1.08] mb-5 tracking-tight">
                    全球 B2B<br/>
                    <span className="text-text-secondary">
                         智能增长操作系统
                    </span>
                </h1>
                <p className="text-[17px] text-text-secondary leading-relaxed max-w-lg">
                    <span className="text-text">AI Operating System for Global B2B Growth</span>
                    <br/>
                    统一编排获客、内容、知识与成交，让全球增长成为可操作系统。
                </p>
            </div>

            {/* 核心功能点 - 横向并排 */}
            <div className="grid grid-cols-3 gap-4 mt-8 w-full">
                <FeatureCard 
                    icon={BrainCircuit} 
                    title="智能体Agent" 
                    desc="零代码编排业务智能体与工作流。"
                />
                <FeatureCard 
                    icon={ShieldCheck} 
                    title="知识库中台" 
                    desc="基于 RAG 的企业级知识检索增强。"
                />
                <FeatureCard 
                    icon={BarChart3} 
                    title="GEO 品牌增长" 
                    desc="优化 AI 搜索引擎品牌排名与内容营销。"
                />
            </div>
            
            <div className="mt-14 text-[12px] text-text-tertiary border-t border-separator pt-5 w-full">
                © 2026 GlobalPilot AI  ·  AI Operating System for Global B2B Growth
            </div>
        </div>
      </div>

      <div className="w-full lg:w-[42%] flex flex-col items-center justify-center p-8 relative">
         
         <div className="w-full max-w-[400px]">
            <div className="bg-surface/90 backdrop-blur-2xl rounded-2xl p-9 shadow-popover border border-separator relative overflow-hidden">

                <h2 className="text-[22px] font-semibold text-text mb-1.5 text-center tracking-tight">欢迎回来</h2>
                <p className="text-text-secondary text-[13px] mb-7 text-center">全球 B2B 智能增长操作系统</p>

                <div className="flex rounded-full bg-surface-2 p-1 mb-7">
                    <button
                        onClick={() => setAuthTab('email')}
                        className={`flex-1 py-2 text-[13px] font-medium rounded-full transition-colors ${authTab === 'email' ? 'bg-surface text-text shadow-card' : 'text-text-secondary hover:text-text'}`}
                    >
                        账号登录
                    </button>
                    <button
                        onClick={() => setAuthTab('wechat')}
                        className={`flex-1 py-2 text-[13px] font-medium rounded-full transition-colors ${authTab === 'wechat' ? 'bg-surface text-text shadow-card' : 'text-text-secondary hover:text-text'}`}
                    >
                        微信扫码
                    </button>
                </div>

                {authTab === 'email' ? (
                    /* ========== 邮箱密码登录/注册 ========== */
                    <form onSubmit={handleEmailAuth} className="space-y-4">
                        <div className="relative">
                            <Mail size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary" />
                            <input
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="邮箱地址"
                                className="w-full bg-surface-2 border border-separator rounded-lg py-3 pl-10 pr-3 text-text text-sm focus:border-accent/50 focus:ring-1 focus:ring-accent/30 outline-none transition-all placeholder:text-text-tertiary"
                            />
                        </div>
                        {isRegister && (
                            <div className="relative">
                                <UserIcon size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary" />
                                <input
                                    type="text"
                                    value={nickname}
                                    onChange={(e) => setNickname(e.target.value)}
                                    placeholder="显示名称（选填）"
                                    className="w-full bg-surface-2 border border-separator rounded-lg py-3 pl-10 pr-3 text-text text-sm focus:border-accent/50 focus:ring-1 focus:ring-accent/30 outline-none transition-all placeholder:text-text-tertiary"
                                />
                            </div>
                        )}
                        <div className="relative">
                            <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary" />
                            <input
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder={isRegister ? "设置密码（至少 6 位）" : "密码"}
                                className="w-full bg-surface-2 border border-separator rounded-lg py-3 pl-10 pr-3 text-text text-sm focus:border-accent/50 focus:ring-1 focus:ring-accent/30 outline-none transition-all placeholder:text-text-tertiary"
                            />
                        </div>

                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full py-3 bg-accent hover:bg-accent-hover disabled:opacity-40 disabled:cursor-not-allowed text-on-accent rounded-full text-sm font-medium transition-colors flex items-center justify-center gap-2"
                        >
                            {loading && <div className="w-4 h-4 border-2 border-separator border-t-transparent rounded-full animate-spin"></div>}
                            {isRegister ? '注册并登录' : '登 录'}
                        </button>

                        <p className="text-center text-xs text-text-secondary">
                            {isRegister ? (
                                <>已有账号？<span onClick={() => setIsRegister(false)} className="text-accent hover:text-accent-hover cursor-pointer">直接登录</span></>
                            ) : (
                                <>还没有账号？<span onClick={() => setIsRegister(true)} className="text-accent hover:text-accent-hover cursor-pointer">立即注册</span>（首个注册用户将成为系统管理员）</>
                            )}
                        </p>
                    </form>
                ) : (
                    /* ========== 微信扫码登录 ========== */
                    <div className="text-center">
                        <div className="flex flex-col items-center justify-center mb-6 min-h-[200px]">
                            {!isMockMode && wechatUrl ? (
                                 <div className="w-[300px] h-[350px] overflow-hidden rounded-lg bg-on-accent shadow-lg">
                                    <iframe
                                        src={wechatUrl}
                                        frameBorder="0"
                                        scrolling="no"
                                        width="300px"
                                        height="400px"
                                        className="-mt-[50px]"
                                    ></iframe>
                                 </div>
                            ) : (
                            <div className="relative group/qr cursor-pointer transition-transform duration-300 hover:scale-[1.02]" onClick={handleMockLogin}>
                                {/* 模拟二维码样式 */}
                                <div className="w-48 h-48 bg-on-accent rounded-lg flex items-center justify-center shadow-lg border-4 border-separator">
                                    <div className="w-full h-full border-2 border-dashed border-separator p-2 flex flex-col items-center justify-center">
                                         <ScanLine size={40} className="text-text-tertiary opacity-80 mb-2" />
                                         <div className="grid grid-cols-5 gap-1 w-24 h-24 opacity-80">
                                             {[...Array(25)].map((_, i) => (
                                                 <div key={i} className={`bg-bg rounded-sm ${Math.random() > 0.5 ? 'opacity-100' : 'opacity-0'}`}></div>
                                             ))}
                                         </div>
                                    </div>
                                </div>

                                {/* 悬停遮罩 */}
                                <div className="absolute inset-0 bg-bg/80 opacity-0 group-hover/qr:opacity-100 transition-opacity duration-300 flex items-center justify-center rounded-lg backdrop-blur-[2px]">
                                    <div className="text-center">
                                         <ScanLine className="w-10 h-10 text-text mx-auto mb-2 animate-pulse" />
                                         <p className="text-text font-medium text-sm">点击模拟扫码成功</p>
                                    </div>
                                </div>

                                {/* Loading 状态 */}
                                {loading && (
                                    <div className="absolute inset-0 bg-surface/95 z-30 flex items-center justify-center rounded-lg">
                                        <div className="flex flex-col items-center">
                                            <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin mb-3"></div>
                                            <span className="text-accent text-xs font-medium">安全验证中...</span>
                                        </div>
                                    </div>
                                )}
                            </div>
                            )}
                        </div>

                        <div className="flex items-center justify-center gap-2 text-xs text-text-secondary">
                            <span className="w-2 h-2 rounded-full bg-success animate-pulse"></span>
                            <span>{isMockMode ? "微信未配置，点击二维码模拟登录（开发模式）" : "请使用微信扫码登录"}</span>
                        </div>
                    </div>
                )}

            </div>

            {/* 底部帮助 */}
            <div className="mt-8 text-center">
                <p className="text-xs text-text-tertiary hover:text-text-secondary cursor-pointer transition">
                    遇到问题？联系管理员获取帮助
                </p>
            </div>
         </div>
      </div>
    </div>
  );
}

// 辅助组件：功能卡片 (竖向布局)
function FeatureCard({icon: Icon, title, desc}: any) {
    return (
        <div className="flex flex-col items-start p-5 rounded-xl bg-surface/70 border border-separator hover:bg-surface-2 transition-all duration-300">
            <div className="mb-3 p-2 bg-text/5 rounded-xl text-accent">
                <Icon size={20} />
            </div>
            <h3 className="font-semibold text-sm text-text mb-2 tracking-tight">{title}</h3>
            <p className="text-[12px] text-text-secondary leading-relaxed">{desc}</p>
        </div>
    )
}
