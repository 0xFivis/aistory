import sys
sys.path.insert(0, r'D:\workspace\aistory\backend\src')

from app.database import get_db_session
from app.models.service_config import ServiceCredential, ServiceOption


def mask(s):
    if not s:
        return None
    s = str(s)
    if len(s) <= 6:
        return '***'
    return s[:3] + '...' + s[-3:]


def main():
    try:
        db = get_db_session()
    except Exception as e:
        print('无法建立数据库连接:', e)
        return
    try:
        creds = db.query(ServiceCredential).filter(ServiceCredential.service_name == 'gemini').all()
        if not creds:
            print('数据库中没有找到 service_credentials 中 service_name == "gemini" 的条目')
        else:
            print('找到以下 gemini 凭证（已遮罩 key/secret）：')
            for c in creds:
                print(f"id={c.id}, service_name={c.service_name}, is_active={c.is_active}, api_url={c.api_url}, credential_key(masked)={mask(c.credential_key)}, credential_secret(masked)={mask(c.credential_secret)}, description={c.description}")

        opts = db.query(ServiceOption).filter(ServiceOption.service_name == 'gemini').all()
        if not opts:
            print('数据库中没有找到 service_options 中 service_name == "gemini" 的条目')
        else:
            print('找到以下 gemini 的 service_options：')
            for o in opts:
                print(f"id={o.id}, option_type={o.option_type}, option_key={o.option_key}, option_value={o.option_value}, is_default={o.is_default}")
    except Exception as e:
        print('查询时出错:', e)
    finally:
        try:
            db.close()
        except Exception:
            pass

if __name__ == '__main__':
    main()
