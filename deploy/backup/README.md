# H-12 PostgreSQL 备份与恢复演练

`postgres_backup.py` 是 AutoForceAI 共享 PostgreSQL 数据库的独立运维工具；Genesis MongoDB 的配套实现与文档在 Genesis_CRM 仓库的 H-12 分支。这里不调用现有 `services/digital-brain/scripts/pg_rehearsal.py`，因为后者会执行 downgrade，**严禁用于生产库演练**。

## 依赖和预置

在受信任备份主机安装与数据库兼容的 `pg_dump`、`pg_restore`、`psql`；可选安装 `age` 做公钥加密。用主机环境或权限限制为仅操作者可读的 `PGPASSFILE` 配置 libpq `PGHOST`、`PGPORT`、`PGUSER`、`PGSSLMODE=verify-full`、`PGDATABASE`。不要在命令、仓库、报告或 manifest 中放置口令、数据库 URL 或 age 私钥。请预先创建一个**空的、隔离的**演练数据库，名称必须包含 `rehearsal` 或 `restore_test`；将演练账号权限限制到该库。备份文件夹必须已经存在，不能是根目录，也不能是软链接；设置仅备份操作员可读写的目录权限。

## 操作示例

```sh
python deploy/backup/postgres_backup.py backup --database autoforce --directory /srv/backup/postgres --report /srv/backup/reports/postgres-backup.json
python deploy/backup/postgres_backup.py restore --directory /srv/backup/postgres --manifest postgres_autoforce_YYYYMMDDTHHMMSSffffffZ.manifest.json --target autoforce_rehearsal --report /srv/backup/reports/postgres-rehearsal.json
python deploy/backup/postgres_backup.py prune --directory /srv/backup/postgres --days 30 --max-copies 14
```

如果启用加密，备份额外传 `--recipient age1...`（公钥），恢复传 `--identity /secure/age-identity.txt`（私钥文件路径）；请在机密存储中保管私钥并定期验证可解密。明文临时文件在备份目录同一文件系统的受限 staging 中生成，脚本关闭时删除。数据库备份为 PostgreSQL custom format (`pg_dump --format=custom`)，恢复前会验证 SHA-256 与 `pg_restore --list`；备份归档和 manifest 通过同目录原子更名提交。**文件对并非跨文件事务**，如意外中断出现孤立归档，人工审查后处理；无 manifest 的归档不会被恢复或清理。不要直接对线上库 restore；工具禁止对非演练库名操作、禁止覆盖非空目标、从不使用 `--clean` / `--create`。

恢复后验证关键 CRM 表与行数、`alembic_version`、CRM entity link 项目数，并生成机器可读报告（RTO 实耗秒数、RPO 即备份至演练的年龄秒数及失败类型）。脚本无法自己证明真实生产 RPO 或跨仓数据一致性：生产排期由运维指定并监控，Genesis Mongo 对应快照应在协调停写/一致性窗口内取得；恢复后用冻结 Integration v1 契约对比双方 CRM 映射和 Genesis project 数量。留存清理只针对经过 manifest 和哈希验证的同目录文件对，按 UTC 创建时间与份数执行，没有递归删除。任何演练失败均不得当作生产恢复成功。

快速安全测试：`python -m unittest discover -s deploy/backup -p 'test_*.py' -v`。集成演练需管理员配置隔离 PostgreSQL 实例与空演练库；单元测试仅使用假命令，不连接真实数据库。
