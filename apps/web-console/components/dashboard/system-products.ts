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
    slogan: '线索与客户服务入口',
    desc: '查看本地线索；智能接待页面尚未开放',
    icon: MessageSquare,
    keyData: '服务入口待开放',
    href: '/leads',
    tint: 'revenue',
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
    slogan: '远期规划',
    desc: '数字人视频与直播模块暂缓，当前页面仅说明规划，不提供直播能力',
    icon: Mic2,
    keyData: '暂缓',
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
