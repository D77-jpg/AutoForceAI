import os
import urllib.parse
from pydantic import BaseModel
from dotenv import load_dotenv
from core.auth import is_production

load_dotenv()

class DatabaseSettings(BaseModel):
    # 优先使用 DATABASE_URL
    # 如果没有，尝试从组件构建 Postgres URL
    # 最后回退到 SQLite
    echo: bool = False
    
    @property
    def url(self) -> str:
        env_url = os.getenv("DATABASE_URL")
        if env_url:
            return env_url
            
        # 尝试构建 Postgres URL
        user = os.getenv("DB_USER")
        if user:
            password = urllib.parse.quote_plus(os.getenv("DB_PASSWORD", ""))
            host = os.getenv("DB_HOST", "localhost")
            port = os.getenv("DB_PORT", "5432")
            db_name = os.getenv("DB_NAME", "geo_mind")
            return f"postgresql://{user}:{password}@{host}:{port}/{db_name}"
            
        return "sqlite:///./geo_mind_v2.db"

class Settings(BaseModel):
    database: DatabaseSettings = DatabaseSettings()
    
    # Global Skill Configurations
    SERP_API_KEY: str = os.getenv("SERP_API_KEY", "")
    RPA_SERVER_URL: str = os.getenv("RPA_SERVER_URL", "http://localhost:8000")
    
settings = Settings()

class AppSettings(BaseModel):
    title: str = "Digital Employee Brain Service"
    version: str = "1.0.0"
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"
    database: DatabaseSettings = DatabaseSettings()
    worker_secret: str = ""

    def model_post_init(self, __context) -> None:
        self.worker_secret = os.getenv("WORKER_SECRET", "")
        if is_production() and len(self.worker_secret.encode("utf-8")) < 32:
            raise RuntimeError("Production requires a strong WORKER_SECRET (at least 32 bytes)")

settings = AppSettings()
