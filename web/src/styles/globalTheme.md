# Aistory 前端统一设计规范（草案）

> 目标：为现有 Vue + Element Plus 前端提供统一的视觉语言，方便二次封装组件和样式改造。

## 1. 设计 Tokens 概览

所有核心 token 已抽象至 `web/src/styles/designTokens.ts`，主要维度如下：

| 类别         | 说明                                             |
| ------------ | ------------------------------------------------ |
| `colorPalette` | 品牌主色、辅助色、灰阶、背景、边框、遮罩等基础色值 |
| `typography` | 字体族、字号、行高、字重                         |
| `spacing`    | 常用间距刻度（4px 基准）                         |
| `radii`      | 圆角梯度                                         |
| `shadows`    | 阴影层级（弱、卡片、浮层）                         |
| `layout`     | 页面框架尺寸（最大宽度、侧边栏宽度、卡片留白等）   |
| `componentTokens` | 按钮、卡片、表格、对话框、表单、标签等组件粒度样式 |
| `transitions` | 动画时长与缓动函数                               |

所有值均为常量对象，可在组件/样式中直接导入；也便于映射到 CSS 变量或 Tailwind 主题。

## 2. 色彩规范

- **主品牌色**：`#2563eb`（Primary），Hover/Active 分别强化亮度与深度。
- **强调色**：`#f97316`，用于关键按钮、提示。
- **反馈色**：成功 `#16a34a`、警告 `#f59e0b`、危险 `#dc2626`、信息 `#0ea5e9`。
- **灰阶**：`neutral100`~`neutral900` 自浅至深，用于背景、边框、正文、标题。
- **背景色**：页面级 `#f5f7fb`，卡片级 `#ffffff`；叠加遮罩 `rgba(17,24,39,0.55)`。

## 3. 字体与层级

- 默认字体：`Inter / PingFang SC / Microsoft Yahei / system`，保证中英混排清晰。
- 字号分层：12/13/14/16/18/24px，对应说明文、辅助文本、正文、子标题、标题、主标题。
- 默认行高：1.5；紧凑 1.25，多段文本 1.7。
- 字重：Regular 400、Medium 500、Semibold 600、Bold 700。

## 4. 间距与布局

- 基准栅格：4px；常用 8/12/16/20/24/32px。
- 页面主体最大宽度 1280px；侧边栏 260px；顶栏高度 64px；模块之间保留 24px。
- 卡片默认内边距 16px，可根据场景调节。

## 5. 组件样式指引

### 5.1 按钮（Button）
- 高度：28/36/44px（三档）；水平内边距 8/12/16px。
- 圆角：8px；字重 500；Hover 使用 `primaryHover`；Active 使用 `primaryActive`。
- 禁用态：背景取 `neutral200`，文本 `neutral500`。

### 5.2 卡片（Card）
- 背景 `#ffffff`，圆角 12px；投影 `shadows.card`；边框 `borderSubtle`。
- Header 行间距 12px，内容内边距 16px。

### 5.3 表格（Table）
- 表头背景 `neutral100`，字体颜色 `neutral700`；悬停 `#f0f5ff`。
- 斑马纹 `#f8fbff`；行高 ≥ 44px；分隔线 `borderSubtle`。

### 5.4 对话框（Dialog）
- 最大宽度 720px；圆角 12px；内边距 20px；标题字号 18px。
- 遮罩使用 `overlay`；按钮区域与内容间距 16px。

### 5.5 表单（Form）
- 标签颜色 `neutral700`；输入控件圆角 8px。
- 聚焦态边框颜色 `primary`，Hover 态 `primarySoft`。

### 5.6 标签（Tag）
- 圆角 999px；高度 24px；内边距 8px；字号 13px。

## 6. 主题落地建议

1. **CSS 变量**：在根节点引入（例如 `/src/styles/variables.scss`）统一注入：
   ```scss
   :root {
     --color-primary: #2563eb;
     --font-family-base: 'Inter', 'PingFang SC', sans-serif;
     --space-4: 16px;
     // ...
   }
   ```
2. **Element Plus 定制**：
   - 使用 `ElConfigProvider` + `namespace` + `component size` 定制。
   - 可在 `element-plus` 主题变量中引入上述 tokens。
3. **自定义组件库**：
   - 创建 `components/ui/` 下的 `BaseButton`, `BaseCard`, `BaseTable` 等，内部引用 `designTokens`。
   - 每个组件输出 props 以兼容 Element Plus 默认行为。
4. **Tailwind/Windi**（若使用）：
   - 配置 `tailwind.config.js`，将 tokens 注入 `theme.extend.colors`、`spacing` 等。

## 7. 推进步骤

1. **确认设计稿/调性**：评审上述配色、字体、间距是否符合品牌。
2. **实现基础样式层**：创建 `variables.scss` 或 CSS vars，引入 Element 自定义主题。
3. **封装基础组件**：先实现 `BaseButton`, `BaseCard`, `BaseTag`，在关键页面替换。
4. **页面迁移**：从核心页面（任务列表/详情、Gemini Console）开始，逐步替换旧组件；保持响应式。
5. **验证与治理**：加入 Stylelint/Tailwind lint 规则 & Storybook 校验，确保视觉一致性。

---

> 后续可根据正式设计稿继续细化间距、动画、配色梯度（例如灰阶、品牌色的 10% 步长），并在 Storybook 中为每个封装组件提供可视测试用例。