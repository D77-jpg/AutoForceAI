# UI 重设计计划（Apple 设计风格）

> 生成时间：2026-09-22 · 阶段 0 审计报告

## 0. 重要前置发现

| 应用 | 状态 |
| --- | --- |
| `apps/web-console` | ✅ 存在（Next.js 14 + Tailwind 3），本次改造对象 |
| `apps/official-site` | ❌ **仓库中不存在**（`apps/` 下仅有 `browser-extension`、`chat-widget`、`web-console`） |
| `apps/ai-mall` | ❌ **仓库中不存在** |

因此阶段 3（官网）与阶段 4（商城）**无代码可改**，本计划仅覆盖：阶段 0/1/2/5。共享令牌包 `packages/ui-tokens` 会按三应用通用标准建设，未来 official-site / ai-mall 落地时可直接接入。`docs/screenshots` 中的截图已存在（cp/geo/kb/kfzj/qydn/tp.png），可供未来官网使用。

## 1. web-console 现状审计

### 1.1 技术栈与配置
- `apps/web-console/package.json`：Next.js ^14.1、React 18、Tailwind ^3.3、lucide-react ^0.292、radix（tabs/dropdown-menu/slot）、recharts、sonner。**未使用成品组件库**，`components/ui/*` 为自建（shadcn 风格）。
- `apps/web-console/tailwind.config.ts`：已有一组 `apple.*` 深色硬编码色板（#000/#1c1c1e/#0a84ff 等）、自定义圆角 `apple*`、阴影 `shadow-apple*`、`shine` 动画。无 CSS 变量驱动、无浅色模式。
- `apps/web-console/app/globals.css`：定义 `--background` 等变量但**未被 Tailwind 引用**；`color-scheme: dark` 写死；含 `.glass-panel/.glass-card/.nav-item/.apple-page/.apple-title` 等工具类，颜色全部硬编码。
- `apps/web-console/app/layout.tsx`：`<html className="dark">` 写死深色；body 硬编码 `bg-black text-[#f5f5f7]`。
- 根 `package.json`：**未配置 workspaces**（仅有 5 个根依赖，需新增 `workspaces: ["apps/*", "packages/*"]`）。

### 1.2 公共组件清单（`components/ui/`）
`alert / badge / button / card / dropdown-menu / input / label / switch / tabs`（9 个，props 接口保持不变）。

### 1.3 布局与公共组件
- `components/sidebar.tsx`：主侧边栏（按路由前缀切换应用分组），硬编码深色。
- `components/AuthWrapper.tsx`、`components/OrganizationGate.tsx`、`components/ChatSidebar.tsx`、`components/Typewriter.tsx`
- `components/ecommerce/`：`AICreateDialog / CreateProductModal / PublishProductModal`
- `contexts/`：AuthContext、ToastContext 等（仅改展示样式）。

### 1.4 页面路由（38 个 page.tsx）
`/`、`/login`、`/crm`、`/diagnosis`、`/digital-human`、`/distribution`、`/geo`、`/knowledge`(+brain/settings/solution/stats)、`/leads`、`/marketing`(+analytics/distribution/image-gen/rpa/text-gen)、`/monitor`、`/ops`(+enterprises/users)、`/optimize`、`/organization`、`/platform`(+models/monitor/skills/traffic)、`/settings`(+client/profile)、`/workforce`(+create/mission)、`/tools/setup`

### 1.5 硬编码样式规模
- 全应用 `*.tsx` 中十六进制颜色 / Tailwind 默认色（slate、green-500、blue-600 等）匹配 **约 1197 处**，遍布全部 38 个页面与组件。
- 典型问题：`text-slate-*`、`bg-[#1c1c1e]`、`border-white/8`、`bg-blue-600`、`text-green-500` 混用；同一语义（次级文字）有 #86868b / #6e6e73 / slate-400 / slate-500 四种写法。

## 2. 改造计划与预计修改文件

### 阶段 1：共享设计令牌 `packages/ui-tokens`
- 根 `package.json` 增加 workspaces。
- 新建 `packages/ui-tokens/`：
  - `tokens.css`：CSS 变量（浅色 `:root` + `prefers-color-scheme: dark` + `[data-theme="dark"]` 双通道深色），含颜色/圆角/阴影/字体栈/动效/毛玻璃工具类。
  - `tailwind.preset.js`（CJS）：Tailwind preset，颜色经 `rgb(var(--token) / <alpha-value>)` 引用变量以支持透明度修饰；圆角 sm/md/lg/xl/2xl/pill、阴影 card/popover/modal、时长 200/300/600、easing Apple 曲线。
  - `package.json`（`@autoforce/ui-tokens`）。
- `apps/web-console/tailwind.config.ts` 改为 `presets: [preset]`（相对路径引用，避免安装解析问题）；`app/layout.tsx` 引入 tokens.css。
- 验证：web-console lint + build。

### 阶段 2：web-console 改造
顺序：基础组件 → 全局布局 → 逐页替换。
1. 重写 `app/globals.css`（令牌化玻璃拟态、nav-item、滚动条、reduced-motion）。
2. 重写 `components/ui/*`（Button 实心 accent 10px 圆角、Input 浅灰底+聚焦 accent 光晕、iOS Toggle、Segmented Tabs、Card/Modal 圆角阴影、Badge 克制灰底），props 不变。
3. `components/sidebar.tsx`、`app/layout.tsx`、`AuthWrapper/OrganizationGate/ToastContext` 令牌化；侧边栏毛玻璃 + accent 高亮块。
4. 脚本化 codemod（`scripts/ui-codemod.js`）：将 38 个页面中的硬编码颜色映射到令牌（#f5f5f7→text、#86868b→text-tertiary、#1c1c1e→surface、#0a84ff/#0071e3→accent、green→success、slate→text-secondary 等），随后人工复核关键页面（首页 dashboard、knowledge/brain、settings 分组列表）。
5. web-console 保持 `data-theme="dark"` 为默认（与现状一致），令牌同时支持浅色与系统跟随。
- 验证：lint + build。

### 阶段 3/4：official-site / ai-mall
- 代码不存在，跳过；在令牌包中预留三端通用能力。

### 阶段 5：一致性检查
- 全局搜索残留 `#hex`、`rgb()`、Tailwind 默认色并替换为令牌。
- 抽查按钮/输入框/卡片圆角阴影统一性、深色模式、375px 横向溢出（检查固定宽度 `w-[...]`、min-w、grid 溢出）。
- 三应用（实际：web-console）lint + build 通过。
