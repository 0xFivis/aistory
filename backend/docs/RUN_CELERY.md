# 运行 Celery Worker

此项目使用 Celery + Redis 作为异步任务队列。下面是常见的运行步骤（Windows PowerShell）：

1. 启动 Redis（请确保 Redis 已安装并运行）

2. 启动 Celery worker：

```powershell
cd D:\workspace\aistory\backend
.\.venv\Scripts\python.exe -m celery -A app.celery_app.celery_app worker --loglevel=info --concurrency=2
```

3. 启动 FastAPI 应用（如果还未启动）：

```powershell
cd D:\workspace\aistory\backend\src
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

4. 创建任务后，`create_task` 会把 `generate_storyboard_task` 发送到 Celery，worker 会处理后续步骤。

调试提示：
- Celery worker 日志会显示任务执行详情。
- 如果使用代理或网络访问外部服务，确保 worker 进程可以读取 `.env` 的代理配置（与主进程相同环境）。

