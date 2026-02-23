import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    RECAPTCHA_SECRET = os.getenv("RECAPTCHA_SECRET")

    # Parse from Railway MYSQL_URL if available: mysql://user:pass@host:port/db
    _mysql_url = os.getenv("MYSQL_URL") or os.getenv("MYSQL_PRIVATE_URL")
    if _mysql_url:
        import urllib.parse
        _parsed = urllib.parse.urlparse(_mysql_url)
        MYSQL_HOST = _parsed.hostname
        MYSQL_USER = _parsed.username
        MYSQL_PASSWORD = _parsed.password
        MYSQL_DB = _parsed.path.lstrip("/")
        MYSQL_PORT = _parsed.port or 3306
    else:
        MYSQL_HOST = os.getenv("MYSQL_HOST", os.getenv("MYSQLHOST", "localhost"))
        MYSQL_USER = os.getenv("MYSQL_USER", os.getenv("MYSQLUSER", "root"))
        MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", os.getenv("MYSQLPASSWORD", ""))
        MYSQL_DB = os.getenv("MYSQL_DATABASE", os.getenv("MYSQLDATABASE", "fest_management"))
        MYSQL_PORT = int(os.getenv("MYSQL_PORT", os.getenv("MYSQLPORT", 3306)))
