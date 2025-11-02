import os
import sys
from urllib.parse import urlparse

import pymysql

BACKEND_ROOT = os.path.dirname(os.path.dirname(__file__))
SRC_DIR = os.path.join(BACKEND_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from app.core.env import load_env  # type: ignore[import-not-found]

load_env()


def init_database():
    """初始化数据库"""
    
    # 解析数据库URL
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL not found in environment variables")
        
    parsed = urlparse(db_url.replace("mysql+pymysql://", "mysql://"))
    
    # 解析连接参数
    db_config = {
        "host": parsed.hostname,
        "port": parsed.port or 3306,
        "user": parsed.username,
        "password": parsed.password,
    }
    
    # 连接MySQL（不指定数据库）
    conn = pymysql.connect(**db_config)
    try:
        with conn.cursor() as cursor:
            # 创建数据库
            database = parsed.path.lstrip('/')
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{database}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            print(f"Database '{database}' created successfully")
            
    finally:
        conn.close()

if __name__ == "__main__":
    init_database()