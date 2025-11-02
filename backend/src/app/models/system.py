from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, ForeignKey
from .base import BaseModel

class Config(BaseModel):
    __tablename__ = "config"
    
    key = Column(String(64), nullable=False, comment="配置键")
    value = Column(Text, nullable=True, comment="配置值")
    type = Column(String(16), nullable=False, default="global", comment="配置类型：global全局,template模板")
    description = Column(String(255), nullable=True, comment="配置描述")

class TaskLog(BaseModel):
    __tablename__ = "task_logs"
    
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, comment="关联任务ID")
    step_id = Column(Integer, ForeignKey("task_steps.id"), nullable=True, comment="关联步骤ID")
    scene_id = Column(Integer, ForeignKey("scenes.id"), nullable=True, comment="关联分镜ID")
    log_type = Column(String(16), nullable=False, comment="日志类型：info,warning,error")
    message = Column(Text, nullable=False, comment="日志信息")
    stack_trace = Column(Text, nullable=True, comment="错误堆栈")