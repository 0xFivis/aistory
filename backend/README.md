# AI Story Generator Backend

基于 FastAPI 和 MySQL 的 AI 故事生成器后端服务。

## 项目结构（摘要）

```

```
backend/
├── src/
│   └── app/
│       ├── config/         # 配置管理
│       ├── models/         # 数据库模型
│       │   ├── task.py    # 任务相关模型
│       │   ├── media.py   # 媒体文件模型
│       │   └── system.py  # 系统配置模型
│       ├── api/           # API 路由
│       ├── services/      # 业务服务
│       └── dependencies/  # 依赖注入
├── alembic/              # 数据库迁移
│   ├── versions/        # 迁移版本
│   └── env.py          # 迁移环境配置
├── tests/              # 测试文件
└── storage/           # 本地存储
    ├── temp/         # 临时文件
    └── media/        # 媒体文件
```

## 开发环境设置

1. 创建虚拟环境：
```bash
python -m venv .venv
```

2. 激活虚拟环境：
```bash
# Windows
.\.venv\Scripts\Activate.ps1

# Linux/Mac
source .venv/bin/activate
```

3. 安装依赖：
```bash
pip install -r requirements.txt
```

4. 设置环境变量：
```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，设置必要的环境变量
```

5. 创建数据库：
```bash
# Windows
python scripts\init_db.py

# Linux/Mac
python scripts/init_db.py
```

6. 运行数据库迁移：
```bash
alembic upgrade head
```

6. 启动开发服务器：
```bash
uvicorn app.main:app --reload
```

## 主要功能

- 任务管理和状态追踪
- 多步骤工作流编排
- 文件上传和管理
- AI 服务集成
- 媒体文件处理

## API 文档

启动服务后，访问以下地址查看 API 文档：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
```
pip install -r requirements.txt
uvicorn src.app.main:app --reload --port 8000
```

API endpoints:
- GET / -> health check
- POST /stories/ -> create story (payload: { title, content })
- GET /stories/{id} -> get story

Migrations:
- The repo includes `alembic` in requirements; to initialize migrations run `alembic init alembic` and configure `alembic/env.py` to import metadata from `src.app.db.base`.
