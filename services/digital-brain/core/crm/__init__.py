"""CRM 集成模块（阶段 2）：Genesis Integration API 客户端、契约、Outbox 与回流。"""

# 配置处于这些健康状态时暂停投递与回流（等管理员处理）
PAUSED_HEALTH_STATUSES = ("auth_invalid", "credential_error")
