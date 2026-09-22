"use client";

import React, { useState, useEffect } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { 
  Search, 
  BarChart3, 
  Activity, 
  Bot, 
  Radar, 
  Compass, 
  Brain, 
  Factory, 
  Share2, 
  Settings, 
  Users,
  Grid,
  ChevronRight,
  Zap,
  Cpu,
  Globe,
  Bell,
  MessageSquare,
  Sparkles,
  Command,
  LayoutGrid,
  Terminal,
  ShieldCheck,
  User as UserIcon,
  Maximize2,
  Briefcase,
  Target,
  PenTool,
  Mic2,
  Database,
  Network,
  Megaphone,
  Coins,
  Crown,
  ArrowUpRight,
  LogOut,
  Library,
  ShoppingBag
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

// --- Types & Data ---

interface UserProfile {
  username: string;
  role: string;
  avatar?: string;
}

const MARKET_METRICS = [
  { label: "品牌心智份额", value: "32.4%", trend: "+2.1%", isPositive: true },
  { label: "竞对活跃指数", value: "High", trend: "Critical", isPositive: false },
];

const TASKS = [
  { id: 1, name: "Q3 行业趋势分析报告", progress: 85, status: "Generating" },
  { id: 2, name: "新品上市社媒文案矩阵", progress: 42, status: "Queued" },
];

const AGENTS = [
  { name: "Alpha (分析师)", task: "Google Search 爬取中...", status: "busy" },
  { name: "Beta (创作者)", task: "撰写小红书文案", status: "busy" },
  { name: "Gamma (守卫者)", task: "待机中", status: "idle" },
];

// Reorganized Data Model: Department -> Digital Employee -> Product
const DEPARTMENTS = [
    {
        title: "增长中心",
        enTitle: "MARKETING & GROWTH",
        colorVar: "pink",
        description: "品牌声量与获客流量引擎",
        icon: Megaphone, // Abstract icon
        apps: [
            { href: "/optimize", label: "内容工场", agent: "Leo (首席内容官)", icon: PenTool, color: "text-danger", desc: "全平台爆款内容批量生产", tag: "AI中台" },
            { href: "/geo", label: "全域洞察", agent: "Sophie (品牌经理)", icon: Radar, color: "text-danger", desc: "品牌舆情与心智份额追踪", tag: "GEO" },
            { href: "/marketing", label: "投放参谋", agent: "Max (投放专员)", icon: Target, color: "text-danger", desc: "广告投放ROI实时优化", tag: "数字员工" },
        ]
    },
    {
        title: "营收中心",
        enTitle: "SALES & REVENUE",
        colorVar: "blue",
        description: "全渠道转化与客户服务中枢",
        icon: Coins,
        apps: [
            { href: "/digital-human", label: "数字人直播", agent: "Emma (金牌主播)", icon: Mic2, color: "text-accent", desc: "7x24小时不间断带货直播", tag: "数字人" },
            { href: "/service/sessions", label: "智能接待", agent: "Ray (销售代表)", icon: MessageSquare, color: "text-accent", desc: "全渠道客户自动接待转化", tag: "AI客服" },
            { href: "/leads", label: "本地线索池", agent: "Outbox", icon: Briefcase, color: "text-accent", desc: "询盘入库、去重、导出，待 CRM 对接", tag: "线索" },
            { href: "/service/stats", label: "服务质检", agent: "AI Judge (裁判)", icon: Activity, color: "text-accent", desc: "AI 自动评分与问题诊断大屏", tag: "质量监控" },
            { href: "/service/rules", label: "质检规则", agent: "SOP Manager", icon: ShieldCheck, color: "text-accent", desc: "配置服务标准与评分SOP", tag: "配置" },
        ]
    },
    {
        title: "决策中心",
        enTitle: "DECISION & INSIGHT",
        colorVar: "blue",
        description: "竞争情报与战略决策大脑",
        icon: Crown,
        apps: [
            { href: "/diagnosis", label: "竞争诊断", agent: "Arthur (行业分析师)", icon: Compass, color: "text-accent", desc: "竞品策略拆解与红黑榜", tag: "GEO" },
            { href: "/diagnosis", label: "市场扫描", agent: "Data Scout (情报员)", icon: Globe, color: "text-accent", desc: "全球前沿市场信号捕捉", tag: "数字员工" },
            { href: "/diagnosis", label: "深度调研", agent: "Insight Bot (研究员)", icon: Activity, color: "text-accent", desc: "定制化行业深度研报生成", tag: "数字员工" },
        ]
    },
    {
        title: "运营中心",
        enTitle: "OPERATIONS & CORE",
        colorVar: "orange",
        description: "组织资产与系统效能保障",
        icon: LayersIcon,
        apps: [
            { href: "/knowledge", label: "企业知识库", agent: "Doc (知识总管)", icon: Brain, color: "text-warning", desc: "核心知识资产沉淀与分发", tag: "AI知识库" },
            { href: "/organization", label: "组织编排", agent: "Monica (HRBP)", icon: Network, color: "text-warning", desc: "数字员工权限与团队管理", tag: "AI中台" },
            { href: "/ops", label: "系统运维", agent: "System (工程师)", icon: Terminal, color: "text-warning", desc: "全平台运行状态监控", tag: "智能运维" },
        ]
    }
];

const SYSTEM_PRODUCTS = [
    {
        id: "knowledge",
        name: "AI知识库",
        slogan: "组织智慧的数字大脑",
        desc: "非结构化数据的清洗、向量化与检索",
        icon: Library,
        keyData: "1.2TB Data",
        href: "/knowledge",
        color: "text-warning"
    },
    {
        id: "geo",
        name: "GEO",
        slogan: "让AI主动推荐你的品牌",
        desc: "基于生成式引擎优化的品牌资产管理系统",
        icon: Radar,
        keyData: "32.4% Share",
        href: "/geo",
        color: "text-accent"
    },
    {
        id: "service",
        name: "AI客服",
        slogan: "全渠道自动接单机器",
        desc: "基于RAG的智能问答与销售线索转化",
        icon: MessageSquare,
        keyData: "99% Resp",
        href: "/service/sessions",
        color: "text-accent"
    },     
    {
        id: "ecommerce",
        name: "AI电商",
        slogan: "高定时尚电商平台",
        desc: "基于大模型的沉浸式购物体验与智能导购",
        icon: ShoppingBag,
        keyData: "2024 Collection",
        href: "/ecommerce", 
        color: "text-warning"
    },
    {
        id: "marketing",
        name: "AI营销",
        slogan: "AIGC 内容生产与投放",
        desc: "文生文、文生图、视频生成与全域自动化投放",
        icon: Megaphone,
        keyData: "ROI +30%",
        href: "/marketing",
        color: "text-danger"
    },
    {
        id: "crm",
        name: "AI CRM",
        slogan: "智能客户关系管理",
        desc: "全渠道数据沉淀与销售线索智能化挖掘",
        icon: Briefcase,
        keyData: "Leads +45%",
        href: "/crm",
        color: "text-danger"
    },
    {
        id: "digital-human",
        name: "数字人",
        slogan: "7x24小时的一线明星",
        desc: "高保真数字人视频生成与直播推流",
        icon: Mic2,
        keyData: "24h Live",
        href: "/digital-human",
        color: "text-danger"
    },
    {
        id: "workforce",
        name: "数字员工",
        slogan: "企业级AI劳动力编排",
        desc: "创建、管理与评估您的数字化员工团队",
        icon: Users,
        keyData: "14 Active",
        href: "/workforce",
        color: "text-accent-hover"
    },
    {
        id: "ops",
        name: "系统运维",
        slogan: "全链路系统健康卫士",
        desc: "基础设施监控与自动化异常熔断",
        icon: Terminal,
        keyData: "99.9% Up",
        href: "/ops",
        color: "text-success"
    },
    {
        id: "mid-platform",
        name: "AI中台",
        slogan: "企业级模型与插件中心",
        desc: "统一的LLM网关与私有插件市场",
        icon: Cpu,
        keyData: "API Gateway",
        href: "/platform",
        color: "text-accent"
    }
];

// Helper Icons (Locally defined if not in lucide imports or distinct usage)
function MegaphoneIcon(props: any) { return <Zap {...props} /> } // Proxy for visual
function CoinsIcon(props: any) { return <Factory {...props} /> }
function ChessIcon(props: any) { return <Brain {...props} /> }
function LayersIcon(props: any) { return <Database {...props} /> }


// --- Sub-Components ---

const HudPanel = ({ title, icon: Icon, color, children, href }: any) => {
    const Content = (
      <div className={`relative h-full group overflow-hidden bg-surface border border-separator rounded-[22px] p-5 hover:bg-surface-2 transition-all duration-300 shadow-card ${href ? 'cursor-pointer' : ''}`}>
          <div className="absolute top-0 right-0 p-4 opacity-[0.08]">
               <Icon size={48} className={color} />
          </div>
          
          <div className="flex items-center gap-2 mb-4 relative z-10">
              <div className={`p-1.5 rounded-xl bg-text/5 ${color}`}>
                  <Icon size={16} />
              </div>
              <h3 className="text-sm font-semibold text-text tracking-tight">{title}</h3>
              {href && <ArrowUpRight size={12} className="text-text-tertiary opacity-0 group-hover:opacity-100 transition-opacity" />}
          </div>
          <div className="relative z-10">
              {children}
          </div>
      </div>
    );

    return href ? <Link href={href} className="block h-full">{Content}</Link> : Content;
};

const IconButton = ({ icon: Icon, onClick, badge }: any) => (
  <button 
    onClick={onClick}
    className="relative w-9 h-9 rounded-full bg-text/5 hover:bg-text/10 flex items-center justify-center text-text-secondary hover:text-white transition-colors"
  >
    <Icon size={16} />
    {badge && <span className="absolute top-0.5 right-0.5 w-2 h-2 bg-danger rounded-full" />}
  </button>
);

const DepartmentCard = ({ dept, className = "" }: { dept: any, className?: string }) => {
    return (
        <div className={`relative overflow-hidden bg-surface border border-separator rounded-2xl p-6 hover:bg-surface-2 transition-all duration-300 group/card ${className}`}>
            
            <div className="relative z-10 flex items-start justify-between mb-6 pb-4 border-b border-separator">
                <div>
                    <div className="flex items-center gap-3 mb-1">
                        <div className={`p-2 rounded-2xl bg-text/5 ${dept.apps[0].color}`}>
                             <dept.icon size={20} />
                        </div>
                        <div>
                            <h3 className="text-lg font-semibold text-white tracking-tight">{dept.title}</h3>
                            <div className="text-[11px] text-text-tertiary tracking-[0.12em] uppercase">
                                {dept.enTitle}
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 relative z-10">
                {dept.apps.map((app:any, idx:number) => (
                    <Link 
                        key={idx} 
                        href={app.href}
                        className="flex flex-col p-3 rounded-[16px] bg-surface-2/70 border border-separator hover:bg-surface-2 transition-all duration-300 group/item relative overflow-hidden"
                    >
                        <div className="flex items-start justify-between mb-2">
                             <div className="flex items-center gap-2">
                                 <div className={`w-8 h-8 rounded-xl flex items-center justify-center bg-bg/40 ${app.color} group-hover/item:scale-105 transition-transform`}>
                                     <app.icon size={16} />
                                 </div>
                                 <div>
                                     <div className="text-sm font-semibold text-text flex items-center gap-1">
                                         {app.label}
                                     </div>
                                 </div>
                             </div>
                             <ChevronRight size={14} className="text-text-tertiary group-hover/item:text-white -translate-x-2 opacity-0 group-hover/item:translate-x-0 group-hover/item:opacity-100 transition-all" />
                        </div>
                        
                        <div className="mt-1 mb-2">
                            <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded-full bg-bg/30 text-[10px] text-text-secondary">
                                <Bot size={10} className={app.color} />
                                <span>{app.agent}</span>
                            </span>
                        </div>

                        <div className="text-[11px] text-text-secondary leading-normal line-clamp-1 border-t border-separator pt-2 mt-auto">
                            {app.desc}
                        </div>
                        
                        {app.tag && (
                             <div className="absolute bottom-0 right-0">
                                 <span className="inline-block px-1.5 py-0.5 bg-text/10 text-text text-[9px] font-medium rounded-tl-xl">
                                     {app.tag}
                                 </span>
                             </div>
                        )}
                    </Link>
                ))}
            </div>
        </div>
    );
};

// --- Main Layout ---

export default function HomePage() {
  const [mounted, setMounted] = useState(false);
  const { user, logout } = useAuth();
  const [showUserMenu, setShowUserMenu] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null;

  return (
    <div className="min-h-screen bg-bg text-text font-sans w-full overflow-x-hidden">
      
      <div className="fixed inset-0 z-0 pointer-events-none">
          <div className="absolute top-[-18%] left-[12%] w-[720px] h-[420px] bg-accent/10 blur-[140px]" />
      </div>

      <header className="fixed top-0 left-0 right-0 z-50 h-16 border-b border-separator bg-bg/70 backdrop-blur-2xl px-6 flex justify-between items-center">
          <div className="flex items-center gap-4">
              <Link href={process.env.NEXT_PUBLIC_OFFICIAL_SITE_URL || "#"} className="w-8 h-8 relative cursor-pointer hover:opacity-80 transition-opacity">
                   <Image src="/logo.png" alt="Logo" fill className="object-contain" />
              </Link>
              <div className="mr-6">
                  <h1 className="text-[17px] font-semibold tracking-tight text-white leading-none mb-0.5">
                      GlobalPilot AI
                  </h1>
                  <p className="text-[11px] text-text-secondary tracking-[0.04em]">
                      全球 B2B 智能增长操作系统
                  </p>
              </div>

              {/* Product Menu */}
              <div className="relative group h-16 flex items-center">
                  <button className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-text-secondary hover:text-white hover:bg-text/5 rounded-full transition-colors">
                      <LayoutGrid size={16} className="text-accent"/>
                      <span>产品矩阵</span>
                      <ChevronRight size={12} className="group-hover:rotate-90 transition-transform duration-300" />
                  </button>
                  
                  {/* Mega Menu Dropdown */}
                  <div className="absolute top-full left-0 w-[800px] bg-surface/95 backdrop-blur-2xl border border-separator rounded-2xl shadow-popover p-6 opacity-0 translate-y-2 pointer-events-none group-hover:opacity-100 group-hover:translate-y-0 group-hover:pointer-events-auto transition-all duration-300 z-50 overflow-hidden">
                        
                        <div className="relative z-10 grid grid-cols-2 gap-4">
                            {SYSTEM_PRODUCTS.map((prod) => (
                                <Link 
                                    key={prod.id} 
                                    href={prod.href} 
                                    target={prod.href.startsWith('http') ? '_blank' : undefined}
                                    className="flex items-start gap-4 p-4 rounded-2xl hover:bg-text/5 border border-transparent transition-all group/card"
                                >
                                    <div className={`p-3 rounded-2xl bg-surface-2 ${prod.color} group-hover/card:scale-105 transition-transform duration-300`}>
                                        <prod.icon size={24} />
                                    </div>
                                    <div className="flex-1">
                                        <div className="flex justify-between items-start mb-1">
                                            <h4 className="font-bold text-text group-hover/card:text-white transition-colors">{prod.name}</h4>
                                            <span className="text-[10px] font-medium bg-text/5 px-1.5 py-0.5 rounded-full text-text-secondary">{prod.keyData}</span>
                                        </div>
                                        <p className="text-[11px] font-medium text-accent mb-1">{prod.slogan}</p>
                                        <p className="text-xs text-text-secondary leading-relaxed line-clamp-2">{prod.desc}</p>
                                    </div>
                                </Link>
                            ))}
                        </div>
                        <div className="mt-4 pt-3 border-t border-separator flex justify-between items-center px-2">
                             <span className="text-[10px] text-text-secondary uppercase tracking-widest">GlobalPilot AI © 2026</span>
                             <Link href="/solution" className="text-xs text-accent hover:text-white flex items-center gap-1 group/link">
                                 查看全景图 <ArrowUpRight size={12} className="group-hover/link:translate-x-0.5 group-hover/link:-translate-y-0.5 transition-transform"/>
                             </Link>
                        </div>
                  </div>
              </div>
          </div>

          <div className="flex items-center gap-5">
               {/* Search Bar */}
               <div className="hidden lg:flex items-center bg-surface border border-separator rounded-full h-9 px-4 w-[320px] mr-2 focus-within:border-accent/40 focus-within:bg-surface-2 transition-all">
                   <Search size={14} className="text-text-secondary mr-2" />
                   <input type="text" placeholder="呼叫数字员工 / 搜索业务数据..." className="bg-transparent border-none outline-none text-xs text-text placeholder:text-text-tertiary flex-1" />
                   <div className="flex items-center gap-1 text-[10px] text-text-tertiary font-mono">
                    <span className="bg-text/10 px-1.5 py-0.5 rounded border border-separator">⌘ K</span>
                   </div>
               </div>

               <div className="h-4 w-px bg-text/10" />
               
               <div className="flex gap-2">
                   <IconButton icon={Bell} badge />
                   <IconButton icon={Settings} />
               </div>
               
               <div 
                  className="flex items-center gap-3 pl-4 border-l border-separator cursor-pointer group relative"
                  onClick={() => setShowUserMenu(!showUserMenu)}
               >
                   <div className="text-right hidden sm:block">
                       <div className="text-xs font-bold text-text group-hover:text-white transition-colors">{user?.nickname || user?.username || 'GUEST'}</div>
                       <div className="text-[10px] text-text-secondary uppercase">
                          {user?.role === 'admin' ? '系统管理员' : (user?.role === 'enterprise_admin' ? '企业管理员' : '普通成员')}
                       </div>
                   </div>
                   <div className="w-9 h-9 rounded-full bg-surface-2 overflow-hidden relative">
                      {(user?.avatar || user?.headimgurl) ? (
                          <img src={user?.headimgurl || user?.avatar} alt="Avatar" className="w-full h-full object-cover" />
                      ) : (
                          <UserIcon className="w-5 h-5 m-2 text-text-secondary" />
                      )}
                   </div>

                   {/* User Dropdown */}
                   {showUserMenu && (
                        <div className="absolute top-full right-0 mt-2 w-56 bg-surface border border-separator rounded-2xl shadow-popover overflow-hidden animate-fade-in-up z-50">
                            <div className="p-3 border-b border-separator">
                                <p className="text-xs text-text-secondary">当前账号</p>
                                <div className="text-sm font-bold text-white truncate flex items-center gap-1">
                                    {user?.nickname || user?.username || 'Guest'}
                                    {user?.org_name && (
                                        <>
                                            <span className="text-text-secondary mx-0.5">|</span>
                                            <span className="text-accent font-normal truncate max-w-[100px]" title={user.org_name}>
                                                {user.org_name}
                                            </span>
                                        </>
                                    )}
                                </div>
                            </div>
                            <div className="p-1">
                                <Link href="/settings/profile" className="flex items-center gap-2 px-3 py-2 text-xs text-text hover:text-white hover:bg-text/5 rounded-lg transition-colors">
                                    <UserIcon size={14} /> 用户中心
                                </Link>
                                <Link href="/ops" className="flex items-center gap-2 px-3 py-2 text-xs text-text hover:text-white hover:bg-text/5 rounded-lg transition-colors">
                                    <Settings size={14} /> 系统配置
                                </Link>
                                <div className="h-px bg-text/5 my-1" />
                                <button 
                                    onClick={logout}
                                    className="w-full flex items-center gap-2 px-3 py-2 text-xs text-danger hover:text-danger hover:bg-danger/10 rounded-lg transition-colors text-left"
                                >
                                    <LogOut size={14} /> 退出登录
                                </button>
                            </div>
                        </div>
                   )}
               </div>
          </div>
      </header>

      {/* --- 2. Main Content (Padded for Fixed Header) --- */}
      <main className="relative z-10 container mx-auto px-4 md:px-8 pt-24 pb-12 max-w-[1600px]">
          
          {/* Dashboard Header - Context */}
          <div className="flex justify-between items-end mb-8">
               <div>
                   <h2 className="text-2xl font-bold text-white mb-2">数字人调度中心</h2>
                   <p className="text-sm text-text-secondary max-w-2xl">
                       全天候运行中。当前系统健康度 <span className="text-success">98.2%</span>，在线数字员工 <span className="text-accent">14</span> 名。
                   </p>
               </div>
               <div className="hidden md:flex gap-3">
                   <Link href="/knowledge/brain" className="px-4 py-2 bg-surface-2 hover:bg-surface-2 text-white text-xs font-medium rounded-full transition-colors flex items-center gap-2">
                       <Brain size={14} />
                       企业知识大脑
                   </Link>
                   <Link href="/workforce/create" className="px-4 py-2.5 bg-accent hover:bg-accent-hover text-white text-xs font-medium rounded-full transition-colors flex items-center gap-2">
                       <Bot size={14} />
                       新建数字员工
                   </Link>
               </div>
          </div>

          {/* HUD Widgets - Strategic Overview */}
          <section className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-10">
              <HudPanel title="市场态势" icon={Radar} color="text-success" href="/diagnosis">
                   <div className="space-y-4">
                       <div className="flex justify-between items-end pb-2 border-b border-separator">
                            <span className="text-xs text-text-secondary">品牌心智份额</span>
                            <div className="text-right">
                                <span className="text-xl font-bold text-white font-mono">32.4%</span>
                                <span className="text-[10px] text-success ml-2">▲ 2.1%</span>
                            </div>
                       </div>
                       <div className="h-10 flex items-end gap-1">
                          {[30, 45, 35, 60, 50, 70, 55, 80, 65, 75, 60, 90].map((h, i) => (
                              <div key={i} className="flex-1 bg-success/30 rounded-[1px] hover:bg-success transition-colors" style={{ height: `${h}%` }} />
                          ))}
                       </div>
                   </div>
              </HudPanel>

              <HudPanel title="任务流水线" icon={Factory} color="text-accent" href="/ops">
                   <div className="space-y-3 pt-1">
                       {TASKS.map(task => (
                           <div key={task.id} className="group/item">
                               <div className="flex justify-between text-xs mb-1">
                                   <span className="text-text font-medium">{task.name}</span>
                                   <span className="text-[10px] text-accent bg-accent/10 px-1.5 rounded">{task.status}</span>
                               </div>
                               <div className="h-1 w-full bg-text/10 rounded-full overflow-hidden">
                                   <div className="h-full bg-accent rounded-full relative" style={{ width: `${task.progress}%` }}>
                                       <div className="absolute right-0 top-0 bottom-0 w-2 bg-text/15 blur-[2px]" />
                                   </div>
                               </div>
                           </div>
                       ))}
                   </div>
              </HudPanel>

              <HudPanel title="员工状态" icon={Users} color="text-accent" href="/workforce">
                   <div className="space-y-3">
                       {AGENTS.map((agent, i) => (
                           <div key={i} className="flex items-center gap-3 p-1.5 rounded-xl hover:bg-text/5 transition-colors cursor-pointer">
                               <div className="w-8 h-8 rounded-xl bg-surface-2 flex items-center justify-center relative">
                                   <Bot size={16} className={agent.status === 'busy' ? "text-accent" : "text-text-tertiary"} />
                                   {agent.status === 'busy' && <span className="absolute -top-0.5 -right-0.5 w-2 h-2 bg-warning rounded-full" />}
                               </div>
                               <div className="min-w-0 flex-1">
                                   <div className="text-xs font-bold text-text">{agent.name}</div>
                                   <div className="text-[10px] text-text-secondary truncate">{agent.task}</div>
                               </div>
                           </div>
                       ))}
                   </div>
              </HudPanel>
          </section>

          {/* --- 3. App Matrix (Departmental Grid) --- */}
          <section className="">
             
             {/* Section Header */}
             <div className="flex items-center gap-4 mb-6">
                 <div className="h-px flex-1 bg-text/10" />
                 <span className="text-[11px] text-text-tertiary uppercase tracking-[0.16em] flex items-center gap-2">
                     <Grid size={12} />
                     产品矩阵
                 </span>
                 <div className="h-px flex-1 bg-text/10" />
             </div>

             <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                 {DEPARTMENTS.map((dept, index) => (
                     <DepartmentCard key={index} dept={dept} />
                 ))}
             </div>
          </section>
      </main>
    </div>
  );
}
