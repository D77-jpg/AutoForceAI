/**
 * 产品矩阵下拉数据（从原首页迁移，保持不变）
 */
import {
  Briefcase,
  Cpu,
  Library,
  Megaphone,
  MessageSquare,
  Mic2,
  Radar,
  ShoppingBag,
  Terminal,
  Users,
  type LucideIcon,
} from 'lucide-react';
import type { DepartmentKey } from '@/lib/dashboard-types';

export interface SystemProduct {
  id: string;
  name: string;
  slogan: string;
  desc: string;
  icon: LucideIcon;
  keyData: string;
  href: string;
  tint: DepartmentKey;
}

export const SYSTEM_PRODUCTS: SystemProduct[] = [
  {
    id: 'knowledge',
    name: 'AI知识库',
    slogan: '组织智慧的数字大脑',
    desc: '非结构化数据的清洗、向量化与检索',
    icon: Library,
    keyData: '1.2TB 数据',
    href: '/knowledge',
    tint: 'ops',
  },
  {
    id: 'geo',
    name: 'GEO',
    slogan: '让AI主动推荐你的品牌',
    desc: '基于生成式引擎优化的品牌资产管理系统',
    icon: Radar,
    keyData: '32.4% 份额',
    href: '/geo',
    tint: 'growth',
  },
  {
    id: 'service',
    name: 'AI客服',
    slogan: '全渠道自动接单机器',
    desc: '基于RAG的智能问答与销售线索转化',
    icon: MessageSquare,
    keyData: '99% 响应率',
    href: '/service/sessions',
    tint: 'revenue',
  },
  {
    id: 'ecommerce',
    name: 'AI电商',
    slogan: '高定时尚电商平台',
    desc: '基于大模型的沉浸式购物体验与智能导购',
    icon: ShoppingBag,
    keyData: '128 件商品',
    href: '/ecommerce',
    tint: 'ops',
  },
  {
    id: 'marketing',
    name: 'AI营销',
    slogan: 'AIGC 内容生产与投放',
    desc: '文生文、文生图、视频生成与全域自动化投放',
    icon: Megaphone,
    keyData: '投产比 +30%',
    href: '/marketing',
    tint: 'growth',
  },
  {
    id: 'crm',
    name: 'AI CRM',
    slogan: '智能客户关系管理',
    desc: '全渠道数据沉淀与销售线索智能化挖掘',
    icon: Briefcase,
    keyData: '线索 +45%',
    href: '/crm',
    tint: 'revenue',
  },
  {
    id: 'digital-human',
    name: '数字人',
    slogan: '7x24小时的一线明星',
    desc: '高保真数字人视频生成与直播推流',
    icon: Mic2,
    keyData: '24h 直播',
    href: '/digital-human',
    tint: 'growth',
  },
  {
    id: 'workforce',
    name: '数字员工',
    slogan: '企业级AI劳动力编排',
    desc: '创建、管理与评估您的数字化员工团队',
    icon: Users,
    keyData: '14 名在线',
    href: '/workforce',
    tint: 'decision',
  },
  {
    id: 'ops',
    name: '系统运维',
    slogan: '全链路系统健康卫士',
    desc: '基础设施监控与自动化异常熔断',
    icon: Terminal,
    keyData: '99.9% 可用',
    href: '/ops',
    tint: 'ops',
  },
  {
    id: 'mid-platform',
    name: 'AI中台',
    slogan: '企业级模型与插件中心',
    desc: '统一的LLM网关与私有插件市场',
    icon: Cpu,
    keyData: '模型网关',
    href: '/platform',
    tint: 'decision',
  },
];
