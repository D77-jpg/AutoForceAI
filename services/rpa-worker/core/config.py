import os
import sys
import json
from dotenv import load_dotenv

# Try to import baked config (injected during build)
try:
    from .build_config import BAKED_CONFIG
except ImportError:
    BAKED_CONFIG = {}

# 1. 优先加载 .env (开发模式)
load_dotenv()


# 2. 尝试加载本地 config.json (客户端模式)
CONFIG_FILE = "config.json"
local_config = {}

# 如果是打包后的 EXE，路径处理稍微不同
if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
    config_path = os.path.join(application_path, CONFIG_FILE)
else:
    config_path = CONFIG_FILE

# 增加 AppData 配置路径 (用于协议唤起时保存配置)
appdata_path = os.path.join(os.environ.get('APPDATA', 'C:\\'), 'DigitalEmployee', CONFIG_FILE)

# 加载顺序: 本地配置(config.json) > AppData配置 > 环境变量 > 默认值
if os.path.exists(config_path):
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            local_config = json.load(f)
    except Exception as e:
        print(f"Warning: Failed to load local config.json: {e}")
elif os.path.exists(appdata_path):
    try:
        with open(appdata_path, 'r', encoding='utf-8') as f:
            local_config = json.load(f)
    except Exception as e:
        print(f"Warning: Failed to load AppData config.json: {e}")

def get_conf(key, default):
    # 优先级: 
    
    # 1. config.json (Local - Explicit Local Override)
    if local_config.get(key):
        return local_config[key]
        
    # 2. Environment Variables (.env - Dev / Docker Override)
    env_val = os.getenv(key)
    if env_val:
        return env_val

    # 3. Build Parameters (Baked Default for Frozen EXEs)
    if BAKED_CONFIG.get(key):
        return BAKED_CONFIG[key]
        
    # 4. Code Default
    return default

# --- 配置定义 ---
# Default to local dev server
GEO_SERVER_URL = get_conf("GEO_SERVER_URL", "http://localhost:8002/api/v1")
WORKER_ID = get_conf("WORKER_ID", "rpa_worker_default")
WORKER_SECRET = get_conf("WORKER_SECRET", "")

# 客户端模式默认开启 Headless=False (要看到浏览器窗口)
HEADLESS = str(get_conf("RPA_HEADLESS", "false")).lower() == "true"
BROWSER_TYPE = get_conf("RPA_BROWSER", "chromium")
POLL_INTERVAL = int(get_conf("RPA_POLL_INTERVAL", "5"))

# Browser Persistence
# 客户端模式下，数据应当存在用户文档目录下，防止 EXE 目录不可写
if getattr(sys, 'frozen', False):
    # C:\Users\User\AppData\Roaming\DigitalEmployee
    BASE_DIR = os.path.join(os.environ.get('APPDATA', '.'), 'DigitalEmployee')
    if not os.path.exists(BASE_DIR):
        try:
            os.makedirs(BASE_DIR)
        except:
             pass
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

USER_DATA_DIR = os.path.join(BASE_DIR, "browser_data")

# Platform Credentials (Deprecated in Local Mode)
ZHIHU_COOKIE = os.getenv("ZHIHU_COOKIE", "")
WECHAT_COOKIE = os.getenv("WECHAT_COOKIE", "")


