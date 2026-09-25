"use client";
import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { 
  LayoutDashboard, 
  BrainCircuit, 
  FlaskConical, 
  RadioTower, 
  PlayCircle, 
  Settings, 
  ShieldCheck, 
  Database, 
  BarChart4, 
  User as UserIcon, 
  LogOut, 
  FileText, 
  Book,
  LayoutGrid,
  Bot,
  Brain,
  Network,
  Users,
  Terminal,
  Activity,
  Video,
  Plus,
  Sparkles,
  Presentation,
  SlidersHorizontal,
  Building2
} from 'lucide-react';
import Image from 'next/image';
import { useAuth } from '@/contexts/AuthContext';
import ThemeToggle from './ThemeToggle';

const MenuLink = ({ href, icon: Icon, label, exact, badge }: any) => {
  const pathname = usePathname();
  // Precise match for root or exact path match or sub-path match with separator
  // This prevents /knowledge matching /knowledge/brain active state incorrectly
  const isActive = exact 
    ? pathname === href 
    : (pathname === href || pathname?.startsWith(`${href}/`));
  
  return (
    <Link href={href} className={`nav-item ${isActive ? 'active' : ''}`}>
        <Icon size={18} strokeWidth={1.75} />
        <span className="font-medium text-sm">{label}</span>
        {badge && (
          <span className="ml-auto text-[9px] px-1.5 py-0.5 rounded-full bg-warning/15 text-warning font-medium shrink-0">
            {badge}
          </span>
        )}
    </Link>
  );
}

export default function Sidebar() {
  const { user, logout } = useAuth();
  const [showMenu, setShowMenu] = useState(false);
  const pathname = usePathname();
  const router = useRouter();

  // useEffect(() => {
  //   // Load user from LocalStorage
  //   const storedUser = localStorage.getItem('user');
  //   if (storedUser) {
  //       try {
  //           setUser(JSON.parse(storedUser));
  //       } catch (e) {
  //           console.error("Failed to parse user data", e);
  //       }
  //   }
  // }, []);

  const handleLogout = () => {
      logout();
  };

  const getAppConfig = () => {
    if (pathname?.startsWith('/service')) {
        return {
            appName: 'AI 客服',
            appEnName: '全渠道智能接待与服务中心',
            homeLink: '/service',
            groups: [
                {
                    title: '会话管理',
                    items: [
                        { href: '/service/sessions', icon: Activity, label: '智能接待' },
                        { href: '/service/history', icon: Book, label: '历史会话查询' },
                        { href: '/leads', icon: Users, label: '本地线索池' }
                    ]
                },
                {
                    title: '机器人配置',
                    items: [
                        { href: '/service/config', icon: Bot, label: '接待机器人' }
                    ]
                },
                {
                    title: '客服流程质检',
                    items: [
                        { href: '/service/rules', icon: ShieldCheck, label: '质检规则' },
                        { href: '/service/stats', icon: BarChart4, label: '服务质检' }
                    ]
                }
            ]
        };
    } else if (pathname?.startsWith('/knowledge')) {
      return {
        appName: '企业知识库',
        appEnName: '企业级知识资产管理中枢',
        homeLink: '/knowledge',
        groups: [
          {
            title: '智能中枢',
            items: [
               { href: '/knowledge/brain', icon: Sparkles, label: '企业知识大脑' }
            ]
          },
          {
            title: '知识管理',
            items: [
              { href: '/knowledge', icon: Database, label: '知识文档', exact: true },
              { href: '/knowledge/stats', icon: BarChart4, label: '数据统计' },
            ]
          },
          {
            title: '系统设置',
            items: [
               { href: '/knowledge/settings', icon: Settings, label: '参数配置' }
            ]
          },
          {
            title: '知识库应用',
            items: [
               { href: '/knowledge/solution', icon: Presentation, label: '方案生成' },
            ]
          }
        ]
      };
    } else if (pathname?.startsWith('/workforce')) {
      return {
        appName: '数字员工',
        appEnName: '企业级 AI 劳动力编排',
        homeLink: '/workforce',
        groups: [
          {
            title: '员工管理',
            items: [
              { href: '/workforce', icon: Users, label: '员工大厅' },
              { href: '/workforce/create', icon: Plus, label: '创建员工' },
            ]
          },
          {
            title: '任务中心',
            items: [
              { href: '/workforce/mission', icon: FlaskConical, label: '任务看板' }, 
              // { href: '/workforce/performance', icon: Activity, label: '绩效分析' },
            ]
          }
        ]
      };
    } else if (pathname?.startsWith('/monitor')) {
        return {
          appName: '全链路监控',
          appEnName: '业务与系统实时监控中心',
          homeLink: '/monitor',
          groups: [
            {
              title: '监控中心',
              items: [
                { href: '/monitor', icon: ShieldCheck, label: '实时大屏' }
              ]
            }
          ]
        };
    } else if (pathname?.startsWith('/organization')) {
        return {
          appName: '组织编排',
          appEnName: '数字员工权限与团队管理',
          homeLink: '/organization',
          groups: [
            {
              title: '组织架构',
              items: [
                { href: '/organization', icon: Network, label: '组织编排' }
              ]
            }
          ]
        };
    } else if (pathname?.startsWith('/ops')) {
        return {
          appName: '系统运维',
          appEnName: '系统运维与健康度监测',
          homeLink: '/ops',
          groups: [
            {
              title: '基础设施',
              items: [
                { href: '/ops', icon: Terminal, label: '系统运维', exact: true }
              ]            },
            {
                title: '系统管理',
                items: [
                    { href: '/ops/users', icon: Users, label: '用户管理' },
                    { href: '/ops/enterprises', icon: Building2, label: '企业管理' }
                ]            }
          ]
        };
    } else if (pathname?.startsWith('/digital-human')) {
        return {
          appName: '数字人',
          appEnName: '高保真数字人视频生成与直播推流',
          homeLink: '/digital-human',
          groups: [
            {
              title: '内容制作',
              items: [
                { href: '/digital-human', icon: Video, label: '数字人规划' }
              ]
            }
          ]
        };
    } else if (pathname?.startsWith('/platform')) {
         return {
           appName: 'AI 中台',
           appEnName: '企业级大模型服务设施',
           homeLink: '/platform',
           groups: [
             {
               title: '模型服务',
               items: [
                 { href: '/platform', icon: LayoutDashboard, label: '总览' },
                 { href: '/platform/models', icon: BrainCircuit, label: '模型纳管' },
               ]
             },
             {
               title: '能力中心',
               items: [
                  { href: '/platform/skills', icon: Sparkles, label: '技能工具箱' }
               ]
             },
             {
               title: '监控运维',
               items: [
                  { href: '/platform/monitor', icon: Activity, label: '系统监控' },
                  { href: '/platform/traffic', icon: BarChart4, label: '流量统计' }
               ]
             }
           ]
         };    } else if (pathname?.startsWith('/marketing')) {
        return {
          appName: 'AI 营销',
          appEnName: 'AIGC 内容生产与全域投放',
          homeLink: '/marketing',
          groups: [
            {
              title: '内容创作',
              items: [
                { href: '/marketing', icon: LayoutDashboard, label: '投放参谋' },
                { href: '/marketing/text-gen', icon: FileText, label: '文生文' },
                { href: '/marketing/image-gen', icon: BrainCircuit, label: '文生图' },
              ]
            },
            {
              title: '推广分发',
              items: [
                { href: '/marketing/distribution', icon: RadioTower, label: '全域投放' },
                { href: '/marketing/rpa', icon: Bot, label: 'RPA 执行' }
              ]
            },
            {
              title: '数据洞察',
              items: [
                { href: '/marketing/analytics', icon: BarChart4, label: '营销分析' }
              ]
            }
          ]
        };
    } else if (pathname?.startsWith('/crm') || pathname?.startsWith('/leads')) {
      // /crm 是「集成门户与摘要」：客户/商机/报价明细在 Genesis_CRM 操作，此处不重复建设
      return {
        appName: 'AI CRM',
        appEnName: 'Genesis 集成门户',
        homeLink: '/crm',
        groups: [
            {
              title: '集成门户',
              items: [
                { href: '/crm', icon: LayoutDashboard, label: '概览', exact: true },
                { href: '/leads', icon: Users, label: '本地线索池' },
                { href: '/crm/quotations/new', icon: Sparkles, label: 'AI 报价' },
                { href: '/crm/settings', icon: SlidersHorizontal, label: '集成设置' }
              ]
            }
        ]
      };
    } else {
      // Default: GEO workspace
      return {
        appName: 'GEO 全域洞察',
        appEnName: '品牌舆情与心智份额追踪',
        homeLink: '/geo',
        groups: [
          {
            title: '核心平台',
            items: [
              { href: '/geo', icon: LayoutDashboard, label: '全域洞察' },
              { href: '/diagnosis', icon: BrainCircuit, label: '竞争诊断' },
            ]
          },
          {
            title: '执行中心',
            items: [
              { href: '/optimize', icon: FlaskConical, label: '内容工场' },
              { href: '/distribution', icon: RadioTower, label: '营销矩阵' },
            ]
          }
        ]
      };
    }
  };

  const appConfig = getAppConfig();

  return (
    <aside className="w-[248px] m-3 mr-0 flex flex-col shrink-0 rounded-2xl bg-surface/80 backdrop-blur-2xl border border-separator shadow-card">
         <div className="p-5 pb-4 border-b border-separator">
            <div className="flex items-center gap-3 mb-4">
              <div className="relative w-8 h-8 rounded-xl overflow-hidden bg-surface-2">
                 <Image 
                    src="/logo.png" 
                    alt="Logo" 
                    fill
                    className="object-contain"
                 />
              </div>
              <div className="min-w-0">
                <h1 className="font-semibold text-[15px] tracking-tight leading-snug break-words">{appConfig.appName}</h1>
                <p className="text-[11px] text-text-secondary mt-0.5 leading-snug break-words">
                    {appConfig.appEnName}
                </p>
              </div>
            </div>

            <Link 
                href="/" 
                className="flex items-center gap-2 w-full p-2 rounded-full bg-text/5 hover:bg-text/10 transition-colors text-[12px] text-text font-medium group"
            >
                <LayoutGrid size={14} className="text-text-secondary group-hover:text-accent transition-colors" />
                <span>切换应用</span>
            </Link>
         </div>

         <div className="flex-1 overflow-y-auto py-5 px-2.5 space-y-1">
            {appConfig.groups.map((group, idx) => (
                <div key={idx} className="mb-5 last:mb-0">
                    <div className="text-[11px] font-semibold text-text-tertiary px-3 mb-1.5">
                        {group.title}
                    </div>
                    {group.items.map((item, itemIdx) => (
                        <MenuLink 
                            key={itemIdx} 
                            href={item.href} 
                            icon={item.icon} 
                            label={item.label} 
                            exact={item.exact}
                            badge={(item as any).badge}
                        />
                    ))}
                </div>
            ))}
         </div>

         <div className="p-3 border-t border-separator relative">
            <div 
                className="flex items-center gap-3 p-2 rounded-2xl hover:bg-text/5 transition-colors cursor-pointer group"
                onClick={() => setShowMenu(!showMenu)}
            >
               <div className="w-8 h-8 rounded-full bg-surface-2 flex items-center justify-center overflow-hidden relative">
                  {user?.avatar || user?.headimgurl ? (
                      <img src={user?.headimgurl || user?.avatar} alt="Avatar" className="w-full h-full object-cover" />
                  ) : (
                      <span className="text-xs font-semibold text-text">
                          {(user?.nickname || user?.username || 'U')?.[0]?.toUpperCase()}
                      </span>
                  )}
               </div>
               <div className="flex-1 overflow-hidden min-w-0">
                  <p className="text-sm font-medium text-text truncate" title={user?.nickname || user?.username}>
                      {user?.nickname || user?.username || '未登录用户'}
                  </p>
                  <p className="text-[10px] text-text-secondary truncate flex items-center gap-1">
                      {user?.org_name && (
                          <span className="text-accent font-medium truncate max-w-[80px]" title={user.org_name}>
                              {user.org_name}
                          </span>
                      )}
                      {user?.org_name && <span className="text-surface-2">|</span>}
                      <span className="shrink-0">
                        {user?.role === 'admin' ? '系统管理员' : (user?.role === 'enterprise_admin' ? '管理员' : '成员')}
                      </span>
                  </p>
               </div>
               <ThemeToggle className="w-7 h-7" />
               <Settings size={16} className={`text-text-tertiary group-hover:text-text transition-transform ${showMenu ? 'rotate-90' : ''}`}/>
            </div>

            {showMenu && (
                <div className="absolute bottom-full left-3 right-3 mb-2 bg-surface border border-separator rounded-2xl shadow-popover p-1.5 z-50 animate-fade-in-up">
                    {user?.role === 'enterprise_admin' && user?.invite_code && (
                        <div className="px-3 py-3 border-b border-separator mb-1 bg-surface-2 rounded-xl">
                            <div className="flex justify-between items-center mb-1">
                                <span className="text-xs text-text-secondary">企业邀请码</span>
                                <span className="text-[10px] text-text-tertiary">点击复制</span>
                            </div>
                            <div 
                                className="text-accent font-semibold font-mono text-lg text-center tracking-widest cursor-pointer select-all" 
                                title="点击复制" 
                                onClick={(e) => {
                                    e.stopPropagation();
                                    navigator.clipboard.writeText(user.invite_code || '');
                                }}
                            >
                                {user.invite_code}
                            </div>
                            <p className="text-[10px] text-text-tertiary text-center mt-1">
                                发送给同事以加入企业
                            </p>
                        </div>
                    )}
                    <Link href="/settings/profile" className="flex items-center gap-2 px-3 py-2 text-sm text-text hover:bg-text/5 rounded-xl transition-colors" onClick={() => setShowMenu(false)}>
                        <UserIcon size={14} /> 用户中心
                    </Link>
                    <Link href="/ops" className="flex items-center gap-2 px-3 py-2 text-sm text-text hover:bg-text/5 rounded-xl transition-colors" onClick={() => setShowMenu(false)}>
                        <Settings size={14} /> 系统设置
                    </Link>
                    <div className="h-px bg-text/10 my-1"></div>
                    <button 
                        onClick={handleLogout}
                        className="w-full flex items-center gap-2 px-3 py-2 text-sm text-danger hover:bg-text/5 rounded-xl transition-colors text-left"
                    >
                        <LogOut size={14} /> 退出登录
                    </button>
                </div>
            )}
         </div>
      </aside>
  );
}
