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

---

# 第二轮精修报告（2026-09-22）

提交：主题切换 `（前一轮收尾）` + 本轮 `88ff98a`（33 文件，+489/-429）。全程仅展示层，未动业务逻辑/API/状态/路由/数据结构/判空条件。

## 一、产品矩阵菜单（1–3）

| # | 条目 | 修改文件与方式 |
|---|---|---|
| 1 | 毛玻璃失效根因排查 | **检查结果**：菜单祖先链 `header(fixed, backdrop-blur-2xl) → div(flex) → div.relative.h-16`——无 overflow:hidden/transform/filter/will-change/opacity<1 的祖先。真正的原因有两个且都在菜单自身与父级 header：① 菜单自身常驻 `translate-y-0` transform 类 + `transition-all`（opacity/transform 动画使元素被提升为独立合成层）；② 父级 header 自带 `backdrop-blur-2xl`，**嵌套 backdrop-filter 时子级无法建立自己的 backdrop root**。两者叠加，Chromium 会静默丢弃子级的 backdrop-filter，只剩 85% 半透明底色，故下层文字清晰可见 |
| 2 | 近不透明背景 | `app/globals.css` 的 `.menu-glass`：浅色 `rgba(255,255,255,0.97)`、深色 `rgba(28,28,30,0.95)`（双通道：media query + `[data-theme="dark"]`），保留 `blur(40px) saturate(180%)` 作为增强；`app/page.tsx` 菜单改为条件渲染，移除自身 transform/opacity 动画类（消除合成层问题，让 blur 有机会生效） |
| 3 | 浅色边框与阴影 | `.menu-glass` 浅色态自带 `1px solid rgba(0,0,0,0.08)` 边框 + `var(--ui-shadow-popover)`；深色态用 separator 令牌边框 |

## 二、首页（4–6）—— 文件：apps/web-console/app/page.tsx

| # | 条目 | 方式 |
|---|---|---|
| 4 | 员工信息去胶囊 | 模块卡片的员工标签由胶囊背景改为「Bot 小图标 + 名字」纯文字行（text-[11px] text-text-secondary），与右上角分类标签胶囊拉开层级 |
| 5 | 分区标题去前置图标 | DepartmentSection 标题行移除 tint 色图标方块，只保留文字标题 + 淡色英文副标题；标题与副标题改为 items-baseline 对齐 |
| 6 | 网格最多 3 列 | `grid-cols-2 lg:grid-cols-3 xl:grid-cols-4` → `grid-cols-2 lg:grid-cols-3` |

## 三、子应用通用规则（7–17）

| # | 条目 | 修改文件（仅列有改动的） |
|---|---|---|
| 7 | 选中态统一 accent 蓝 | optimize（平台/语气选择、focus 环、主按钮、进度点、编辑/发布按钮、selection 色，原 danger 红全改 accent）；distribution（平台筛选标签）；marketing/distribution（渠道卡）；image-gen（预设卡 + 生成按钮去 destructive）；text-gen（模板/类型选择，原 warning 橙改 accent）；workforce/create（技能卡 border-accent/40）；platform/models（筛选按钮、启用勾选 text-success→text-accent）；platform/skills（TabsTrigger 补 text-on-accent）；ops（服务状态卡去装饰色，仅超阈值才 warning）；ops/users（管理员徽标 danger→accent、禁用状态改中性灰、状态开关 accent/中性）；ops/enterprises（成员选择器 bg-accent/10+border-accent/40、待保存标记 text-success→text-accent）；monitor（RPA 队列装饰橙→中性）；login（Tab 选中不可见修复 bg-surface+shadow-card）；crm（占位图标误用 danger→accent）；marketing/page（KPI 下行徽标 danger→中性）。**红色现仅存于错误/删除语义** |
| 8 | emoji → lucide 细线图标 | diagnosis（insights 文案 ✅⚠️❌💡 前缀删除、⚡自动选择→自动选择（推荐））；optimize（平台/语气 emoji 与符号图标全删、❤→lucide Heart）；ops/users（「●」字符→真实圆点 span）；全部改动文件的 lucide 图标统一补 strokeWidth={1.75}（knowledge、workforce 3 页、ops 3 页、monitor、marketing 等） |
| 9 | 第三方平台图标 | distribution（表格平台列 9 个彩色圆点全删，只留平台名文字）；marketing/distribution（LinkedIn/WordPress/X 统一 lucide 细线单色 text-text-secondary 同尺寸）；optimize（平台图标随 R8 移除，只显示文字）；login/settings 已是单色细线 |
| 10 | 双语标题/大字距清理 | optimize（「Leo 神经网络处理进程 (Neural Process)」→「生成进度」、「实机预览 (Live Preview)」→「实时预览」）；marketing 4 页标题去英文括注（文生文/文生图/海外投放/获客漏斗）+ marketing 看板 6 处双语后缀 +「内容产出 (30d)」→「内容产出/近 30 天」；geo（「GEO 健康度评分」大字距、Modal「品牌名称 (Brand)」）；diagnosis（10 处中文标签去 uppercase tracking）；distribution（8 处）；ops（统计卡大字距）；settings/profile（4 个表单标签）；platform/page（KPI tracking-wider）；workforce/create（3 个区块标题）；monitor（再扫）；**侧边栏**：`总览 Dashboard`→`总览`、`概览 Dashboard`→`概览`、`内容创作 (AIGC)`→`内容创作`、`文生文 (Copy)`→`文生文`、`文生图 (Image)`→`文生图`、组标题去 uppercase tracking-[0.12em]；**首页**：产品矩阵分隔标签去大字距。技术缩写 API/RPA/GEO/Token/CSV/QPS 保留 |
| 11 | 手机预览 | optimize 设备标签「iPhone 15 Pro Max • 5G」→「手机预览」 |
| 12 | 装饰背景 | optimize（中栏 radial-gradient 点阵删除）；monitor（StatCard 大图标水印删除）；全量扫描确认其余页面无点阵/网格背景 |
| 13 | 多栏布局统一 | optimize（三栏底色与 backdrop-blur 全删，统一透明+hairline 分割线）；knowledge（左栏列表包进与右栏一致的 bg-surface 卡片容器）；workforce/mission（右栏 bg-surface/70 混用底色删除，两栏统一卡片）；workforce/create（模板侧栏补 shadow 对齐卡片语言）；marketing/image-gen（右栏改 glass-panel 卡片与左栏一致）；distribution（展开详情左右栏统一 bg-bg）；monitor/ops/ops/users/ops/enterprises（全部面板统一 bg-surface rounded-lg shadow-card） |
| 14 | 标题区遮挡/裁切 | marketing 5 页 PageHeader 补 shrink-0 防 flex 压缩；workforce/mission、knowledge/brain、knowledge/solution、monitor、ops 逐一检查无遮挡（报告见各子代理明细） |
| 15 | 空/等待态统一 EmptyState | diagnosis（「等待分析数据」双空态合并、「AI 深度思考」spinner→EmptyState）；optimize（「等待任务指令」→EmptyState sm）；distribution（表格加载态）；workforce（加载态、mission「等待任务指令」+planning 骨架屏→EmptyState）；platform/models/monitor/skills/traffic（加载态→EmptyState sm + Loader2）；settings/profile（加载态）；marketing/analytics（漏斗加载）、rpa（同步 Worker 状态）；monitor（「暂无用量数据」） |
| 16 | 侧边栏顶部命名 | components/sidebar.tsx：`/workforce`「GlobalPilot AI」→「数字员工」+「企业级 AI 劳动力编排」；GEO 默认「GlobalPilot AI \| GEO」+ 英文说明→「GEO 全域洞察」+「品牌舆情与心智份额追踪」；应用名与说明由 truncate 改为完整换行（break-words + leading-snug） |
| 17 | 名称统一（首页卡片 ↔ 侧边栏菜单 ↔ 页面标题） | **统一清单**（→ 后为统一名）：①「内容工场」：侧边栏 内容构建→内容工场、页面标题 内容工厂→内容工场（app/optimize/page.tsx）；②「全域洞察」：侧边栏 品牌资产→全域洞察、页面标题 GEO 优化引擎→全域洞察（app/geo/page.tsx）；③「竞争诊断」：侧边栏 品牌洞察→竞争诊断（页面标题本已一致）；④「投放参谋」：侧边栏 营销看板→投放参谋、页面标题 AI 营销云看板→投放参谋（app/marketing/page.tsx）；⑤「数字人直播」：侧边栏 视频生成→数字人直播、应用名 数字人梦工厂→数字人、页面标题→数字人直播（app/digital-human/page.tsx）；⑥「系统运维」：侧边栏 控制台→系统运维、应用名 智能运维→系统运维、页面标题 运维控制台→系统运维（app/ops/page.tsx）；⑦「智能接待」：侧边栏 实时会话监控→智能接待；⑧「服务质检」：侧边栏 服务质量报表→服务质检；⑨「质检规则」：侧边栏 质检规则配置→质检规则；⑩「组织编排」：应用名 虚拟组织→组织编排、菜单项 团队概览→组织编排；⑪ AI CRM 页标题「AI 客户关系管理 CRM」→「AI CRM」（app/crm/page.tsx）；⑫ AI 营销应用名「AI 营销云」→「AI 营销」。已一致的（企业知识库/本地线索池/营销矩阵/AI 中台等）未动 |

## 四、验收（18–20）

- **18 lint + build**：`tsc --noEmit` 0 错误；eslint **11 errors = 基线 11 errors（零新增）**（均为未改动文件的历史遗留 react-hooks 规则）；`npm run build` ✓ Compiled successfully，39 静态页全部生成；全局扫描 mojibake=0（无编码损坏）。
- **19 深浅色检查**：构建产物 CSS 确认 `.menu-glass` 浅（rgba(255,255,255,.97)+1px 边框）与深（rgba(28,28,30,.95)）双变体均编译在内，且受 `[data-theme]`/prefers-color-scheme 双通道控制；全部子应用页面已令牌化（本轮再次扫描无 hex/调色板色/硬编码黑白残留），切换按钮在侧边栏底部与首页头部。运行时冒烟：6 条代表路由（含 optimize、marketing/text-gen、ops、monitor）全部 200。
- **20 本报告**：条目-文件对照如上；毛玻璃根因见条目 1；名称统一清单见条目 17。

**附带说明**：optimize 页中图片遮罩 `from-black/60`→`from-overlay`、ops/monitor 的 `rounded-full`→`rounded-pill`、recharts 图表 `#666/#fff`→令牌色等硬编码顺手清理；未触碰 toast 文案、console.error、POST 数据体等数据层字符串。
