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

const MenuLink = ({ href, icon: Icon, label, exact, badge }: any) => {
  const pathname = usePathname();
  // Precise match for root or exact path match or sub-path match with separator
  // This prevents /knowledge matching /knowledge/brain active state incorrectly
  const isActive = exact 
    ? pathname === href 
    : (pathname === href || pathname?.startsWith(`${href}/`));
  
  return (
    <Link href={href} className={`nav-item ${isActive ? 'active' : ''}`}>
        <Icon size={18} />
        <span className="font-medium text-sm">{label}</span>
        {badge && (
          <span className="ml-auto text-[9px] px-1.5 py-0.5 rounded-full bg-[#ff9f0a]/15 text-[#ffd60a] font-medium shrink-0">
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
                        { href: '/service/sessions', icon: Activity, label: '实时会话监控' },
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
                        { href: '/service/rules', icon: ShieldCheck, label: '质检规则配置' },
                        { href: '/service/stats', icon: BarChart4, label: '服务质量报表' }
                    ]
                }
            ]
        };
    } else if (pathname?.startsWith('/ecommerce')) {
        return {
          appName: 'AI 电商',
          appEnName: '高定时尚品牌智能经营系统',
          homeLink: '/ecommerce',
          groups: [
            {
              title: '店铺运营',
              items: [
                { href: '/ecommerce', icon: LayoutDashboard, label: '运营数据', exact: true, badge: '开发中' },
                { href: '/ecommerce/products', icon: Sparkles, label: '商品管理', exact: true, badge: '开发中' },
                { href: '/ecommerce/products/create', icon: Plus, label: '发布商品', badge: '开发中' },
                { href: '/ecommerce/categories', icon: LayoutGrid, label: '商品分类', badge: '开发中' },
                { href: '/ecommerce/attributes', icon:  SlidersHorizontal, label: '商品属性', badge: '开发中' },
                { href: '/ecommerce/orders', icon: FileText, label: '订单管理', badge: '开发中' },
              ]
            },
            {
              title: '客户',
              items: [
                 { href: '/ecommerce/customers', icon: Users, label: '客户与会员', badge: '开发中' }
              ]
            },
            {
              title: '营销',
              items: [
                 { href: '/ecommerce/marketing', icon: RadioTower, label: 'AI 营销', badge: '开发中' }
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
               { href: '/knowledge/solution', icon: Presentation, label: '方案生成', badge: '开发中' },
            ]
          }
        ]
      };
    } else if (pathname?.startsWith('/workforce')) {
      return {
        appName: '思渡数字员工',
        appEnName: '企业级数字劳动力管理平台',
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
                { href: '/monitor', icon: ShieldCheck, label: '实时大屏' },
                { href: '/monitor/alerts', icon: RadioTower, label: '告警记录', badge: '开发中' }
              ]
            }
          ]
        };
    } else if (pathname?.startsWith('/organization')) {
        return {
          appName: '虚拟组织',
          appEnName: 'AI 团队与组织架构管理',
          homeLink: '/organization',
          groups: [
            {
              title: '组织架构',
              items: [
                { href: '/organization', icon: Network, label: '团队概览' },
                { href: '/organization/agents', icon: Users, label: '员工管理', badge: '开发中' }
              ]
            }
          ]
        };
    } else if (pathname?.startsWith('/ops')) {
        return {
          appName: '智能运维',
          appEnName: '系统运维与健康度监测',
          homeLink: '/ops',
          groups: [
            {
              title: '基础设施',
              items: [
                { href: '/ops', icon: Terminal, label: '控制台', exact: true }
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
          appName: '数字人梦工厂',
          appEnName: '超写实数字人视频生成',
          homeLink: '/digital-human',
          groups: [
            {
              title: '内容制作',
              items: [
                { href: '/digital-human', icon: Video, label: '视频生成' },
                { href: '/digital-human/assets', icon: Users, label: '形象资产', badge: '开发中' }
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
                 { href: '/platform', icon: LayoutDashboard, label: '总览 Dashboard' },
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
          appName: 'AI 营销云',
          appEnName: 'AIGC 内容生产与全域投放',
          homeLink: '/marketing',
          groups: [
            {
              title: '内容创作 (AIGC)',
              items: [
                { href: '/marketing', icon: LayoutDashboard, label: '营销看板' },
                { href: '/marketing/text-gen', icon: FileText, label: '文生文 (Copy)' },
                { href: '/marketing/image-gen', icon: BrainCircuit, label: '文生图 (Image)' },
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
      return {
        appName: 'AI CRM',
        appEnName: '智能客户关系管理',
        homeLink: '/leads',
        groups: [
            {
              title: '客户管理',
              items: [
                { href: '/crm', icon: LayoutDashboard, label: '概览 Dashboard' },
                { href: '/leads', icon: Users, label: '本地线索池' },
                { href: '/crm/customers', icon: Building2, label: '客户列表', badge: '开发中' }
              ]            
            },
            {
                title: '销售漏斗',
                items: [
                    { href: '/crm/opportunities', icon: BarChart4, label: '商机管理', badge: '开发中' },
                    { href: '/crm/contracts', icon: FileText, label: '合同归档', badge: '开发中' }
                ]            
            }
        ]
      };
    } else {
      // Default: ThinkGo GEO (formerly Digital Employee)
      return {
        appName: '思渡AI | GEO',
        appEnName: 'AI 驱动的品牌搜索增长引擎',
        homeLink: '/geo',
        groups: [
          {
            title: '核心平台',
            items: [
              { href: '/geo', icon: LayoutDashboard, label: '品牌资产' },
              { href: '/diagnosis', icon: BrainCircuit, label: '品牌洞察' },
            ]
          },
          {
            title: '执行中心',
            items: [
              { href: '/optimize', icon: FlaskConical, label: '内容构建' },
              { href: '/distribution', icon: RadioTower, label: '营销矩阵' },
            ]
          }
        ]
      };
    }
  };

  const appConfig = getAppConfig();

  return (
    <aside className="w-[248px] m-3 mr-0 flex flex-col shrink-0 rounded-[24px] bg-[#1c1c1e]/80 backdrop-blur-2xl border border-white/8 shadow-apple">
         <div className="p-5 pb-4 border-b border-white/6">
            <div className="flex items-center gap-3 mb-4">
              <div className="relative w-8 h-8 rounded-xl overflow-hidden bg-[#2c2c2e]">
                 <Image 
                    src="/logo.png" 
                    alt="Logo" 
                    fill
                    className="object-contain"
                 />
              </div>
              <div className="min-w-0">
                <h1 className="font-semibold text-[15px] tracking-tight truncate">{appConfig.appName}</h1>
                <p className="text-[11px] text-[#86868b] mt-0.5 truncate">
                    {appConfig.appEnName}
                </p>
              </div>
            </div>

            <Link 
                href="/" 
                className="flex items-center gap-2 w-full p-2 rounded-full bg-white/6 hover:bg-white/10 transition-colors text-[12px] text-[#f5f5f7] font-medium group"
            >
                <LayoutGrid size={14} className="text-[#86868b] group-hover:text-[#0a84ff] transition-colors" />
                <span>切换应用</span>
            </Link>
         </div>

         <div className="flex-1 overflow-y-auto py-5 px-2.5 space-y-1">
            {appConfig.groups.map((group, idx) => (
                <div key={idx} className="mb-5 last:mb-0">
                    <div className="text-[11px] font-semibold text-[#6e6e73] px-3 mb-1.5 uppercase tracking-[0.12em]">
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

         <div className="p-3 border-t border-white/6 relative">
            <div 
                className="flex items-center gap-3 p-2 rounded-2xl hover:bg-white/6 transition-colors cursor-pointer group"
                onClick={() => setShowMenu(!showMenu)}
            >
               <div className="w-8 h-8 rounded-full bg-[#3a3a3c] flex items-center justify-center overflow-hidden relative">
                  {user?.avatar || user?.headimgurl ? (
                      <img src={user?.headimgurl || user?.avatar} alt="Avatar" className="w-full h-full object-cover" />
                  ) : (
                      <span className="text-xs font-semibold text-[#f5f5f7]">
                          {(user?.nickname || user?.username || 'U')?.[0]?.toUpperCase()}
                      </span>
                  )}
               </div>
               <div className="flex-1 overflow-hidden min-w-0">
                  <p className="text-sm font-medium text-[#f5f5f7] truncate" title={user?.nickname || user?.username}>
                      {user?.nickname || user?.username || '未登录用户'}
                  </p>
                  <p className="text-[10px] text-[#86868b] truncate flex items-center gap-1">
                      {user?.org_name && (
                          <span className="text-[#0a84ff] font-medium truncate max-w-[80px]" title={user.org_name}>
                              {user.org_name}
                          </span>
                      )}
                      {user?.org_name && <span className="text-[#3a3a3c]">|</span>}
                      <span className="shrink-0">
                        {user?.role === 'admin' ? '系统管理员' : (user?.role === 'enterprise_admin' ? '管理员' : '成员')}
                      </span>
                  </p>
               </div>
               <Settings size={16} className={`text-[#6e6e73] group-hover:text-white transition-transform ${showMenu ? 'rotate-90' : ''}`}/>
            </div>

            {showMenu && (
                <div className="absolute bottom-full left-3 right-3 mb-2 bg-[#1c1c1e] border border-white/10 rounded-2xl shadow-apple-lg p-1.5 z-50 animate-fade-in-up">
                    {user?.role === 'enterprise_admin' && user?.invite_code && (
                        <div className="px-3 py-3 border-b border-white/6 mb-1 bg-[#2c2c2e] rounded-xl">
                            <div className="flex justify-between items-center mb-1">
                                <span className="text-xs text-[#86868b]">企业邀请码</span>
                                <span className="text-[10px] text-[#6e6e73]">点击复制</span>
                            </div>
                            <div 
                                className="text-[#0a84ff] font-semibold font-mono text-lg text-center tracking-widest cursor-pointer select-all" 
                                title="点击复制" 
                                onClick={(e) => {
                                    e.stopPropagation();
                                    navigator.clipboard.writeText(user.invite_code || '');
                                }}
                            >
                                {user.invite_code}
                            </div>
                            <p className="text-[10px] text-[#6e6e73] text-center mt-1">
                                发送给同事以加入企业
                            </p>
                        </div>
                    )}
                    <Link href="/settings/profile" className="flex items-center gap-2 px-3 py-2 text-sm text-[#f5f5f7] hover:bg-white/6 rounded-xl transition-colors" onClick={() => setShowMenu(false)}>
                        <UserIcon size={14} /> 用户中心
                    </Link>
                    <Link href="/ops" className="flex items-center gap-2 px-3 py-2 text-sm text-[#f5f5f7] hover:bg-white/6 rounded-xl transition-colors" onClick={() => setShowMenu(false)}>
                        <Settings size={14} /> 系统设置
                    </Link>
                    <div className="h-px bg-white/8 my-1"></div>
                    <button 
                        onClick={handleLogout}
                        className="w-full flex items-center gap-2 px-3 py-2 text-sm text-[#ff453a] hover:bg-white/6 rounded-xl transition-colors text-left"
                    >
                        <LogOut size={14} /> 退出登录
                    </button>
                </div>
            )}
         </div>
      </aside>
  );
}