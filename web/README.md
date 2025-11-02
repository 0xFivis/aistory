# AI Story Generator Frontend

基于 Vue 3 + TypeScript 的 AI 故事生成器前端应用。

## 项目结构

```
web/
├── src/
│   ├── assets/        # 静态资源
│   ├── components/    # Vue 组件
│   ├── router/        # 路由配置
│   ├── stores/        # Pinia 状态管理
│   └── views/         # 页面视图
├── public/           # 公共文件
└── env.*.local      # 环境变量
```

## 技术栈

- Vue 3 Composition API
- TypeScript
- Element Plus UI
- Pinia 状态管理
- Vue Router
- Vite 构建工具

## 开发环境设置

在运行前端之前，请复制 `.env.example` 为 `.env.development`（或 `.env.local`）并根据实际后端地址调整：

```
cp .env.example .env.development
# 编辑 .env.development 设置 VITE_API_BASE、VITE_API_PROXY_TARGET
```

1. 安装依赖：
```bash
npm install
```

2. 启动开发服务器：
```bash
npm run dev
```

3. 构建生产版本：
```bash
npm run build
```

4. 代码格式化：
```bash
npm run format
```

## 主要功能

- 故事生成工作流管理
- 实时任务状态跟踪
- 媒体文件预览
- AI 生成参数配置
- 文件上传和管理

## 代理配置

开发环境已配置 API 代理，所有 `/api` 请求会被转发到 `VITE_API_PROXY_TARGET` 指定的后端服务。可在 `.env.*` 或 `vite.config.ts` 中调整。