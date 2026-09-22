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

---

# 完成报告（2026-09-22）

## 各阶段文件与 commit

| 阶段 | Commit | 主要文件 |
| --- | --- | --- |
| 0 审计 | `51a12c5` | `UI_REDESIGN_PLAN.md` |
| 1 共享令牌 | `0166b98` | 新增 `packages/ui-tokens/{package.json,tokens.css,tailwind.preset.js}`；根 `package.json` 增加 workspaces；`apps/web-console/{tailwind.config.ts,eslint.config.mjs,package.json}`；`app/layout.tsx` |
| 2 web-console | `9983391` | `app/globals.css` 全量重写；`components/ui/*` 9 个组件重写（props 不变）；`components/sidebar.tsx`、`AuthWrapper.tsx`、`OrganizationGate.tsx`、`contexts/ToastContext.tsx` 令牌化；codemod 覆盖全部 38 个页面（约 2100 处替换）；新增 `scripts/ui-codemod*.js` |
| 5 一致性 | `3ca8571` | 图表（recharts/SVG）颜色、装饰性 glow 阴影、无效透明度档位（`/8`、`separator/60` 等）、`text-white-700` 无效类修复；`AuthWrapper` 主区 `min-w-0` 防 375px 横向溢出 |

## 关键实现说明
- **令牌体系**：`tokens.css` 用 RGB 通道 CSS 变量，支持 `bg-accent/10` 透明度修饰；深色双通道（`prefers-color-scheme` + `[data-theme="dark"]`）。Tailwind preset 提供 `bg/surface/surface-2/text(-secondary/-tertiary)/accent(-hover)/separator/success/warning/danger`、圆角 `sm/md/lg/xl/2xl/pill`、阴影 `card/popover/modal`、时长 `fast/base/slow` 与 `ease-apple`、毛玻璃 `.ui-glass`。
- **包链接**：web-console 通过 `file:../../packages/ui-tokens` 依赖 + node_modules junction 引入 `tokens.css`；`npm install` 时会自动重建链接。
- **弹窗规范**：所有模态统一 `rounded-xl`（20px）+ `shadow-modal` + `animate-modal-in`（0.96→1 淡入 300ms）。
- **reduced-motion**：tokens.css 全局兜底关闭动效。
- **lint**：修复了原本就无法运行的 lint（`next lint` 与 ESLint 9 不兼容），迁移到 flat config（`eslint.config.mjs`）。

## 无法按规范实现 / 有意保留
1. **`apps/official-site` 与 `apps/ai-mall` 不存在于仓库**——阶段 3、4 无代码可改。`packages/ui-tokens` 已按三端通用设计，新应用落地后接入 preset 即可。
2. **web-console 默认仍为深色**（`data-theme="dark"`，与原产品一致）；令牌已支持浅色，切换属性即可启用。
3. **lint 11 个存量 error**（`react-hooks/set-state-in-effect`、`no-img-element` 等逻辑/规范类问题，改造前即存在）：按要求"不改业务逻辑"未修复；`npm run lint` 会输出报告但不阻断。
4. 图表多系列颜色映射到 `accent/success/warning/danger/accent-hover` 语义色（替代原彩虹色），若产品希望图表保留更多区分色，可在令牌中扩展 chart 系列。
5. 部分装饰性文案保留 `text-white`（彩色按钮/图片遮罩上的白字，符合设计意图）。

## 需人工检查的页面
- 所有 38 个页面建议在浏览器过一遍深色模式，重点：
  - `/knowledge/brain`、`/diagnosis`、`/optimize`（沉浸式深色画布页）
  - `/settings/profile`、`/knowledge/settings`（表单/分组列表观感）
  - `/`（应用启动台）、`/login`（毛玻璃卡片）
  - 电商弹窗（CreateProductModal / PublishProductModal / AICreateDialog）
- 375px 移动端抽查 `/`、`/workforce`、`/distribution` 表格页。
- 若需启用浅色模式，逐页检查浅色对比度（深色优先的透明度叠加在浅色下可能偏淡）。
