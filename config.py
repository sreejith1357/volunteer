import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    RECAPTCHA_SECRET = os.getenv("RECAPTCHA_SECRET")

    MYSQL_HOST = os.getenv("MYSQL_HOST", os.getenv("MYSQLHOST", "localhost"))
    MYSQL_USER = os.getenv("MYSQL_USER", os.getenv("MYSQLUSER", "root"))
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", os.getenv("MYSQLPASSWORD", ""))
    MYSQL_DB = os.getenv("MYSQL_DATABASE", os.getenv("MYSQLDATABASE", "fest_management"))
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", os.getenv("MYSQLPORT", 3306)))