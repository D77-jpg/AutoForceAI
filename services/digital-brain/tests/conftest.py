"""pytest 共享前置：隔离的 SQLite 测试库（必须在任何 database 导入之前设置）。"""
import os
import tempfile

_db_dir = tempfile.mkdtemp(prefix="autoforce-test-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_db_dir, "test.db").replace("\\", "/")
