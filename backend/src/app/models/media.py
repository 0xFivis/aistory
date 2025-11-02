from datetime import datetime
from typing import Optional
from sqlalchemy import Column, BigInteger, String, Text, JSON, DateTime, ForeignKey, Integer, TIMESTAMP, Float
from sqlalchemy.dialects.mysql import TINYINT
from .base import BaseModel

class Scene(BaseModel):
    __tablename__ = "scenes"
    
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, comment="关联任务ID")
    seq = Column(Integer, nullable=False, comment="分镜序号")
    status = Column(TINYINT, nullable=False, default=0, comment="状态码：0待处理,1处理中,2成功,3失败,4跳过,5取消")
    params = Column(JSON, nullable=True, comment="分镜参数JSON")
    result = Column(JSON, nullable=True, comment="分镜结果JSON")
    error_msg = Column(Text, nullable=True, comment="错误信息")
    started_at = Column(DateTime, nullable=True, comment="开始时间")
    finished_at = Column(DateTime, nullable=True, comment="完成时间")
    
    # 新增字段 - 内容
    narration_text = Column(Text, nullable=True, comment="旁白文本")
    narration_word_count = Column(Integer, nullable=True, comment="旁白字数")
    image_prompt = Column(Text, nullable=True, comment="图片提示词")
    video_prompt = Column(Text, nullable=True, comment="图生视频提示词")
    
    # 新增字段 - 子状态
    image_status = Column(TINYINT, nullable=False, default=0, comment="图片状态：0待处理,1处理中,2成功,3失败")
    # 本地 Celery task id，用于在中断时调用 revoke/terminate
    image_celery_id = Column(String(128), nullable=True, comment="本地 Celery task id (用于 revoke/terminate)")
    # 本地 Celery task id for video generation (用于 revoke/terminate)
    video_celery_id = Column(String(128), nullable=True, comment="本地 Celery task id for video generation (用于 revoke/terminate)")
    audio_status = Column(TINYINT, nullable=False, default=0, comment="音频状态：0待处理,1处理中,2成功,3失败")
    audio_duration = Column(Float, nullable=True, comment="音频时长（秒）")
    video_status = Column(TINYINT, nullable=False, default=0, comment="视频状态：0待处理,1处理中,2成功,3失败")
    
    # 新增字段 - 重试计数
    image_retry_count = Column(Integer, nullable=False, default=0, comment="图片重试次数")
    audio_retry_count = Column(Integer, nullable=False, default=0, comment="音频重试次数")
    video_retry_count = Column(Integer, nullable=False, default=0, comment="视频重试次数")
    
    # 新增字段 - URL
    image_url = Column(String(500), nullable=True, comment="图片URL")
    audio_url = Column(String(500), nullable=True, comment="音频URL")
    merge_video_url = Column(String(500), nullable=True, comment="音视频合成后视频URL")
    raw_video_url = Column(String(500), nullable=True, comment="原始视频URL（未合成音频）")
    image_provider = Column(String(64), nullable=True, comment="图片生成服务提供商")
    audio_provider = Column(String(64), nullable=True, comment="音频生成服务提供商")
    video_provider = Column(String(64), nullable=True, comment="视频生成服务提供商")
    image_job_id = Column(String(128), nullable=True, comment="图片生成外部任务ID")
    audio_job_id = Column(String(128), nullable=True, comment="音频生成外部任务ID")
    video_job_id = Column(String(128), nullable=True, comment="视频生成外部任务ID")
    image_meta = Column(JSON, nullable=True, comment="图片生成的额外元数据，例如提示词、耗时")
    audio_meta = Column(JSON, nullable=True, comment="音频生成的额外元数据，例如音色、采样率")
    video_meta = Column(JSON, nullable=True, comment="视频生成的额外元数据，例如分辨率、帧率")
    merge_status = Column(TINYINT, nullable=False, default=0, comment="音视频合成状态：0待处理,1处理中,2成功,3失败")
    merge_retry_count = Column(Integer, nullable=False, default=0, comment="音视频合成重试次数")
    merge_video_provider = Column(String(64), nullable=True, comment="音视频合成服务提供商")
    merge_job_id = Column(String(128), nullable=True, comment="音视频合成外部任务ID")
    merge_meta = Column(JSON, nullable=True, comment="音视频合成的额外元数据")

class File(BaseModel):
    __tablename__ = "files"
    
    task_id = Column(BigInteger, ForeignKey("tasks.id"), nullable=False, comment="关联任务ID")
    scene_id = Column(Integer, ForeignKey("scenes.id"), nullable=True, comment="关联分镜ID")
    file_type = Column(String(16), nullable=False, comment="文件类型：image,audio,video")
    file_path = Column(String(255), nullable=True, comment="本地文件路径")
    file_url = Column(String(255), nullable=True, comment="远程文件URL")
    file_size = Column(BigInteger, nullable=True, comment="文件大小(字节)")
    mime_type = Column(String(64), nullable=True, comment="MIME类型")
    meta_data = Column(JSON, nullable=True, comment="元数据JSON")
    
    # 新增字段
    duration = Column(Float, nullable=True, comment="媒体时长（秒）")
    width = Column(Integer, nullable=True, comment="宽度（像素）")
    height = Column(Integer, nullable=True, comment="高度（像素）")
    storage_type = Column(String(20), nullable=False, default='local', comment="存储类型: local, cloudinary, s3")
    provider = Column(String(64), nullable=True, comment="生成该文件的服务提供商")
    origin_step = Column(String(64), nullable=True, comment="生成该文件的流程步骤标识")