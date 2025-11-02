from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, DateTime

from app.utils.timezone import naive_now

Base = declarative_base()

class BaseModel(Base):
    __abstract__ = True
    
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=naive_now)
    updated_at = Column(DateTime, default=naive_now, onupdate=naive_now)