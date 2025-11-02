from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.mysql import TINYINT
from .base import BaseModel

class Task(BaseModel):
    __tablename__ = "tasks"
    
    user_id = Column(Integer, nullable=True, comment="用户ID")
    workflow_type = Column(String(32), nullable=False, comment="工作流类型")
    # 状态码约定：0待处理,1处理中,2成功,3失败,4跳过,5取消,6部分完成
    # 备注：将使用 6 作为 INTERRUPTED (中断) 状态的约定（用于 TaskStep/Scene 的中断语义）
    status = Column(TINYINT, nullable=False, default=0, comment="状态码：0待处理,1处理中,2成功,3失败,4跳过,5取消,6部分完成")
    params = Column(JSON, nullable=True, comment="任务参数JSON")
    result = Column(JSON, nullable=True, comment="任务结果JSON")
    error_msg = Column(String(255), nullable=True, comment="错误信息")
    is_deleted = Column(Boolean, nullable=False, default=False, comment="是否删除")
    
    # 新增字段
    task_config = Column(JSON, nullable=True, comment="任务完整配置JSON")
    # 自动/手动模式：'auto' | 'manual' （优先从单独列读取，兼容旧的 task_config.mode）
    mode = Column(String(16), nullable=False, default='auto', comment="任务执行模式：auto/manual")
    progress = Column(Integer, nullable=False, default=0, comment="任务进度 0-100")
    total_scenes = Column(Integer, nullable=True, comment="总分镜数")
    completed_scenes = Column(Integer, nullable=False, default=0, comment="已完成分镜数")
    providers = Column(JSON, nullable=True, comment="功能模块选用的服务提供商映射，例如 {'image':'runninghub'}")
    merged_video_url = Column(String(500), nullable=True, comment="分镜拼接后视频URL（未加背景音乐）")
    final_video_url = Column(String(500), nullable=True, comment="最终成片URL（完成配乐/滤镜等处理）")
    selected_voice_id = Column(String(128), nullable=True, comment="Fish Audio voice_id chosen for this task")
    selected_voice_name = Column(String(128), nullable=True, comment="Display name of the selected voice")
    subtitle_style_id = Column(Integer, ForeignKey("subtitle_styles.id", ondelete="SET NULL"), nullable=True, comment="选择的字幕样式 ID")
    subtitle_style_snapshot = Column(JSON, nullable=True, comment="字幕样式快照 JSON")

class TaskStep(BaseModel):
    __tablename__ = "task_steps"
    
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, comment="关联任务ID")
    step_name = Column(String(64), nullable=False, comment="步骤名称")
    seq = Column(Integer, nullable=False, comment="步骤顺序")
    # 状态码约定：0待处理,1处理中,2成功,3失败,4跳过,5取消,6中断
    status = Column(TINYINT, nullable=False, default=0, comment="状态码：0待处理,1处理中,2成功,3失败,4跳过,5取消,6中断")
    params = Column(JSON, nullable=True, comment="步骤参数JSON")
    result = Column(JSON, nullable=True, comment="步骤结果JSON")
    error_msg = Column(String(255), nullable=True, comment="错误信息")
    started_at = Column(DateTime, nullable=True, comment="开始时间")
    finished_at = Column(DateTime, nullable=True, comment="完成时间")
    
    # 新增字段
    retry_count = Column(Integer, nullable=False, default=0, comment="重试次数")
    max_retries = Column(Integer, nullable=False, default=3, comment="最大重试次数")
    progress = Column(Integer, nullable=False, default=0, comment="步骤进度 0-100")
    provider = Column(String(64), nullable=True, comment="本步骤使用的服务提供商")
    external_task_id = Column(String(128), nullable=True, comment="外部服务返回的任务ID或Job ID")
    context = Column(JSON, nullable=True, comment="步骤运行时上下文信息，例如排队状态、回调信息")