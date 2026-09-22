# Apple 风格精修完成报告（web-console）

日期：2026-09-22 ｜ 范围：apps/web-console + packages/ui-tokens ｜ 全部改动均为展示层，未触碰业务逻辑、API、状态管理、路由与数据结构。

## 提交记录

| 提交 | 内容 |
|---|---|
| `5ff78ce` | 首页精修（第二部分 1–11） |
| `d82f79c` | 产品矩阵菜单（第三部分 12–18） |
| `74bc2cc` | 跨平台（第五部分 31–33） |
| `1ea8491` | 共享组件 EmptyState/Modal/Table/PageHeader + Input 高度统一 |
| `710c2cb` | 子应用 35 页统一改造（第四部分 19–30） |
| `23d9424` | 首页令牌化收尾 + 375px 响应式修复 |
| `294d589` | 登录页硬编码颜色清理 |

## 二、首页（数字人调度中心）—— 文件：apps/web-console/app/page.tsx、packages/ui-tokens/tokens.css、tailwind.preset.js

| # | 条目 | 修改位置与方式 |
|---|---|---|
| 1 | 分类标签移到标题行右侧胶囊 | `app/page.tsx` DepartmentSection：`ml-auto px-2 py-0.5 rounded-full bg-surface-2 text-[11px] text-text-secondary`，与标题同行垂直居中 |
| 2 | 去掉分区外层大卡片 | DepartmentCard → DepartmentSection：标题直接渲染在页面背景上，无包裹容器；英文副标题缩为 11px + `text-text-tertiary/60` |
| 3 | 通栏 + 响应式网格 | 分区改为整页通栏；模块卡片 `grid-cols-2 lg:grid-cols-3 xl:grid-cols-4` |
| 4 | 卡片去分割线 | 卡片内部改为 `flex-col gap-2.5` 间距分层；员工标签胶囊无边框（bg-surface-2） |
| 5 | macOS 实心彩色图标 | 所有模块/分区图标：`rounded-[22%]` 实心方块 + `text-on-accent` 白色图标；新增令牌 `--ui-tint-growth/revenue/decision/ops`（深色 #FF453A/#0A84FF/#5E5CE6/#FF9F0A，浅色 #FF3B30/#007AFF/#5856D6/#FF9500），`TINT_BG` 静态映射保证 Tailwind JIT 可扫描 |
| 6 | 删除统计卡装饰图标 | HudPanel 移除右上角 48px 半透明装饰图标 |
| 7 | 统计卡高度自适应 | HudPanel 移除 `h-full`，统计区 grid 加 `items-start` |
| 8 | 柱状图 | `bg-success`（深色令牌已更新为 #30D158），最新一根全不透明、其余 `bg-success/50`，新增 X 轴日期标签（`BAR_DATES` 最近 12 天） |
| 9 | 员工状态点 | 工作中 `bg-success`、待机 `bg-text-tertiary`（灰），无橙色 |
| 10 | 任务进度条 | 生成中 `bg-accent`、排队中 `bg-text-tertiary/60`（灰） |
| 11 | 英文状态中文化 | TASKS 数据：Generating→生成中、Queued→排队中；删除未使用的 MARKET_METRICS（含英文 High/Critical） |

## 三、产品矩阵下拉菜单 —— 文件：apps/web-console/app/page.tsx、apps/web-console/app/globals.css

| # | 条目 | 修改位置与方式 |
|---|---|---|
| 12 | 菜单强毛玻璃 | 新增 `globals.css` 工具类 `.menu-glass`：`rgb(var(--ui-surface) / 0.85)` + `backdrop-filter: blur(40px) saturate(180%)`——深色即 rgba(28,28,30,.85)、浅色自动为 rgba(255,255,255,.85) |
| 13 | backdrop-blur 失效排查 | 菜单由 `group-hover` 改为 React state 控制，移除了悬停链路中的 pointer-events/translate 组合；祖先链（header → .relative 容器）无 transform/filter/will-change 覆盖子级毛玻璃，仅 header 自身 backdrop-blur（不破坏子级） |
| 14 | 遮罩 + 关闭交互 | 菜单打开时渲染 `bg-overlay/30` 遮罩（新令牌 `--ui-overlay`，即 rgba(0,0,0,.3)），点击遮罩关闭，`useEffect` 监听 Esc 关闭；点击菜单内链接也关闭 |
| 15 | 副标题颜色 | 各产品 slogan `text-accent` → `text-text-secondary`；蓝色仅保留「查看全景图」链接 |
| 16 | 英文指标中文化 | SYSTEM_PRODUCTS 数据：1.2TB 数据 / 32.4% 份额 / 99% 响应率 / **128 件商品**（替换无语义的 2024 Collection）/ 投产比 +30% / 线索 +45% / 24h 直播 / 14 名在线 / 99.9% 可用 / 模型网关 |
| 17 | 产品图标 | 改为 `w-11 h-11 rounded-[22%]` 实心分区色方块 + 白色图标，与首页一致 |
| 18 | 版权文字 | `text-xs text-text-tertiary`，去掉 uppercase/tracking-widest |

## 四、子应用通用规则

**共用外壳现状（重要结论）**：全部子应用已经统一使用共享外壳——`components/AuthWrapper.tsx`（页面容器）+ `components/sidebar.tsx`（唯一侧边栏，内部按路由切换各应用的菜单组），**没有任何子应用自建布局，无需迁移**。侧边栏三项规则本就由共享组件保证：

- 19 分组间距统一 `mb-5 last:mb-0`、组标题 `text-[11px] text-text-tertiary`（`components/sidebar.tsx`）
- 20 选中/hover/「开发中」徽章统一（`globals.css` 的 `.nav-item` + sidebar 的 MenuLink badge）
- 21 底部用户信息区头像/名称/设置按钮一致（共享 sidebar 底部区）

**新建共享组件**（`components/PageHeader.tsx`、`components/ui/empty-state.tsx`、`components/ui/modal.tsx`、`components/ui/table.tsx`）并逐页落地：

| # | 条目 | 落地位置 |
|---|---|---|
| 22 | 页面标题去前置图标 | `PageHeader`（apple-title 文字 + apple-subtitle 说明）落地到全部 33 个子应用页面 |
| 23 | 标题区右侧操作按钮 | 统一放入 `PageHeader` 的 `actions`（如 knowledge 新建知识库、workforce 新建数字员工、analytics/ops 刷新按钮） |
| 24 | 统一 EmptyState | `components/ui/empty-state.tsx`：居中大图标 + 标题 + 说明 + 可选蓝色主按钮，`size="lg"/"sm"` |
| 25 | 主数据缺失时只显示大号 EmptyState | `app/knowledge/page.tsx`（无知识库→隐藏文档列表+检索测试台，只显示"新建知识库"EmptyState）；`app/workforce/page.tsx`（无员工→隐藏卡片网格，只显示"新建数字员工"）；`app/ops/enterprises/page.tsx`（空企业列表）；`app/ops/page.tsx`（加载失败） |
| 26 | 下级列表空 → 面板内小 EmptyState | leads、knowledge 文档列表、marketing/rpa、ops/users、workforce/mission、distribution（任务表与日志区）、platform/traffic、platform/skills、platform/models、marketing/analytics（渠道发布/最近询盘）等 |
| 27 | 「输入框+创建按钮」→ 新建按钮 + Modal | `app/knowledge/page.tsx`（新建知识库）、`app/geo/page.tsx`（新建监测任务）、`app/platform/models/page.tsx`、`app/ops/enterprises/page.tsx`（5 个手写弹窗全部迁移共享 Modal）、`app/ops/users/page.tsx`（编辑弹窗）、`app/distribution/page.tsx`（编辑/删除确认弹窗）；均复用原有 state 与提交函数。**注：marketing 系 6 页经逐一确认不存在该写法（创建动作本就在标题按钮或页面主体表单），未强行改动交互结构** |
| 28 | 统一 Table 组件 | `components/ui/table.tsx`（无竖线、细横分割线、表头 12px text-secondary）；替换 knowledge、leads、marketing/rpa、ops/users、platform/models、platform/traffic、distribution 的原生 table |
| 29 | 输入框与按钮等高 | `components/ui/input.tsx` 默认高度 h-11 → **h-10**，与 Button 默认尺寸一致（全局一处修复，所有"输入框+按钮"组合受益）；distribution 编辑弹窗、settings、knowledge/settings 等表单同步 h-10 + gap-2 |
| 30 | 英文状态/指标中文化 | 全部通过展示层映射实现（判断值/API 字段不变）：leads（新线索/已联系/已转化/已放弃）、workforce（在线/工作中/待机、角色徽标）、workforce/mission（进行中/已完成/失败等）、marketing/rpa（排队中/执行中/成功/失败）、monitor（系统监控/成功/失败/延迟等）、knowledge（已索引/处理中/排队中/失败、分块数/相关度）、ops（健康/警告等）、marketing（成功率/提示词/主题等）、distribution（LIVE→实时） |

## 五、跨平台

| # | 条目 | 修改位置与方式 |
|---|---|---|
| 31 | 快捷键平台提示 | `app/page.tsx`：`isMac` 在渲染期派生（组件 mounted 前返回 null，无 hydration 风险、无 setState-in-effect），macOS 显示 ⌘K、其他 Ctrl K |
| 32 | Inter 字体 | `app/layout.tsx` 引入 `next/font/google` Inter（`--font-inter` 变量）；`packages/ui-tokens/tokens.css` 字体栈更新为 `-apple-system, BlinkMacSystemFont, var(--font-inter,"Inter"), "SF Pro Text", "PingFang SC", ...`——Inter 正好位于 BlinkMacSystemFont 之后、PingFang SC 之前，macOS 不受影响、Windows 英文/数字使用 Inter |
| 33 | tabular-nums | `globals.css` 新增 `.tabular-nums` 工具类；首页统计/柱状图日期、knowledge 统计、rpa KPI、ops、workforce/mission、distribution 统计卡等全部数字统计已加该类 |

## 六、验收

| # | 条目 | 结果 |
|---|---|---|
| 34 | lint + build | `tsc --noEmit` 0 错误；`npm run lint`（eslint）exit 0，共 11 个 error **与基线提交 65658a3 完全一致（11 个，零新增）**，全部为既有 `react-hooks/set-state-in-effect` 等规则的历史遗留（AuthContext.tsx、ecommerce/PublishProductModal.tsx、Typewriter.tsx 等未改动文件）；`npm run build` ✓ Compiled successfully，39 个静态页全部生成（含 Inter 字体下载） |
| 35 | 深/浅色检查 | 所有改动均走设计令牌（含浅色变体），全局扫描确认改造范围内无残留 text-white/hex/rgb 硬编码（login 页二维码白底改用 `bg-on-accent` 令牌表达）。**限制**：`app/layout.tsx` 当前硬编码 `data-theme="dark"`，应用无浅色切换入口（既有架构决定，未擅自变更）；浅色模式通过令牌静态审计保证可用 |
| 36 | 375px 无横向溢出 | 修复 `app/optimize/page.tsx`（三栏固定宽度 → `flex-col lg:flex-row`，左右栏 w-full lg:w-[400px]/[380px]）、`app/knowledge/stats/page.tsx`（grid-cols-3 → sm:grid-cols-3）、`app/marketing/rpa/page.tsx`（grid-cols-4 → grid-cols-2 lg:grid-cols-4）、首页菜单 `max-w-[calc(100vw-2rem)]`、首页分区网格小屏 2 列；外壳 `flex overflow-hidden` 保证无页面级横滚 |
| 37 | 完成报告 | 本文档；另做运行时冒烟测试：干净构建下 36 条路由全部 200 |

**过程中发现并处理的问题**：验收时发现端口 3050 上的旧生产服务器持有 `.next` 文件锁，导致 `next build` 产物 chunk 缺失、线上 500。已在干净环境重建（39 页全部生成），并用新构建重启 3050 服务，复验全部路由 200。

**未完成/不适用条目**：
- 条目 27 对 marketing 系 6 页不适用（无"输入框+创建按钮并排"写法），未为凑规则改变其交互结构。
- `app/monitor/page.tsx` 大屏页按最小改动原则仅做标题/文案中文化，保留原生 table 与 recharts 图表内部配色（大屏视觉属特殊场景）。
- 375px 下侧边栏仍为固定 248px 常驻（不横滚但内容区较窄）；如需真正的移动端体验（可折叠抽屉式侧边栏）建议另行立项，超出本次展示层范围。

**子应用共用组件迁移情况**：无迁移——10 个子应用（AI知识库/GEO/AI客服/AI电商/AI营销/AI CRM/数字人/数字员工/系统运维/AI中台）及次级页面全部已经使用共享 `AuthWrapper + Sidebar` 外壳，本次仅统一其内部页面的标题/空状态/弹窗/表格组件。
