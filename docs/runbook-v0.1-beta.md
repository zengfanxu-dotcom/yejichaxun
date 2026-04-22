# 可复制执行版上线 Runbook（v0.1-beta）

以下按“单机/云主机 + Docker Compose”给你一版最快可落地流程。你可以今天就执行。

---

## 0. 上线目标与范围

- 目标：上线 `v0.1-beta`，支持真实用户小流量使用
- 范围：前端 + FastAPI 后端 + SQLite（当前架构）
- 灰度策略：仅内部白名单账号或固定入口访问

---

## 1. 发布前冻结（T-2h）

### 1.1 代码冻结

```bash
git checkout main
git pull
# 确认没有未提交改动
git status
```

### 1.2 本地验收

```bash
# 后端测试
python -m pytest backend/tests -q -o addopts=

# 前端测试
cd frontend
npm test -- --watchAll=false --runInBand
cd ..
```

### 1.3 版本标记

```bash
git tag v0.1.0-beta
git tag
```

---

## 2. 生产环境准备（服务器）

### 2.1 目录结构

```bash
/opt/yejichaxun/
  ├─ app/            # 代码
  ├─ data/           # SQLite/持久化数据
  ├─ uploads/        # 上传文件
  ├─ logs/           # 日志
  └─ .env            # 生产配置
```

### 2.2 生产 `.env`（模板）

```env
APP_ENV=production
LOG_LEVEL=INFO

# API
HOST=0.0.0.0
PORT=8000

# DB
DATABASE_URL=sqlite:////opt/yejichaxun/data/app.db

# 上传与模型
UPLOAD_DIR=/opt/yejichaxun/uploads
HF_ENDPOINT=https://hf-mirror.com
RAG_EMBEDDINGS_ALLOW_ONLINE_FALLBACK=1

# CORS（替换成你的真实域名）
CORS_ALLOW_ORIGINS=https://your-domain.com
```

---

## 3. 构建与启动（Docker Compose）

### 3.1 首次部署

```bash
cd /opt/yejichaxun/app
docker compose pull
docker compose build --no-cache
docker compose up -d
```

### 3.2 查看状态

```bash
docker compose ps
docker compose logs -f backend
docker compose logs -f frontend
```

---

## 4. 上线后验收（必须全部通过）

### 4.1 健康检查

```bash
curl -I http://127.0.0.1:8000/docs
curl -I http://127.0.0.1:3000
```

### 4.2 核心链路手测

- 上传文件 -> 分析成功 -> 报告可查看
- 运行中任务可取消
- 失败/取消任务可重试
- 历史列表可查看事件、指标
- WS 断开后能自动降级轮询

### 4.3 关键口径核对

- 当总分为 0 时，`有效业绩总数` 必须为 0（你刚修复的点）

---

## 5. 灰度发布策略（首周）

- D1：仅内部账号，限制上传文件大小（如 10MB）
- D2-D3：放开到 10%-20% 用户
- D4-D7：观察指标再扩容

### 监控阈值（建议）

- API 5xx > 2%（5分钟）报警
- 任务失败率 > 10%（15分钟）报警
- P95 分析时长 > 120s 报警
- WS 连接失败率 > 15% 报警

---

## 6. 回滚 SOP（5分钟内）

### 6.1 触发条件（任一）

- 大面积 5xx
- 核心链路不可用（上传/分析/报告）
- 关键业务口径错误（如有效业绩统计异常）

### 6.2 回滚步骤

```bash
# 切回上一稳定版本tag
git checkout v0.0.x-stable

# 重启服务
docker compose down
docker compose up -d --build
```

### 6.3 回滚后验证

- 重跑健康检查
- 重跑一条上传->分析->报告链路

---

## 7. 运营值班手册（简版）

### 常用命令

```bash
docker compose ps
docker compose logs --tail=200 backend
docker compose restart backend
```

### 常见故障快修

- 模型拉取慢/失败：确认 `HF_ENDPOINT` 可达
- SQLite 锁冲突：降低并发、排查长事务
- 前端白屏：看浏览器控制台 + `frontend` 容器日志

---

## 8. 上线完成标准（Go/No-Go）

满足以下全部才算 Go：

- 健康检查通过
- 核心链路全通过
- 指标稳定 30 分钟
- 回滚演练至少一次成功

---

## 9. RAG 周更与回退（执行版）

### 9.1 小样本先在测试环境重建

1. 将新 Excel 放到测试环境，先不覆盖生产文件。
2. 调用 `POST /api/v1/rag/rebuild` 完成测试重建。
3. 用 2~3 个小样本 query（覆盖“应命中/不应命中/边界金额”）抽检：
   - 候选召回是否合理；
   - 总分为 0 时，`有效业绩总数` 是否为 0；
   - 封顶场景下，`有效业绩总数` 是否等于实际计分条数。
4. 测试通过后再进入生产重建。

### 9.2 生产重建前必须保留回退点

- 备份当前生产 Excel（时间戳命名）。
- 记录当前重建信息（时间、文件名、文档数、操作者）。

### 9.3 一键执行脚本（Windows PowerShell）

项目已提供：`scripts/rag_rebuild_weekly.ps1`

```powershell
# 在仓库根目录执行：
# 方式1：仅重建（不替换Excel）
powershell -ExecutionPolicy Bypass -File .\scripts\rag_rebuild_weekly.ps1

# 方式2：替换为新Excel后重建
powershell -ExecutionPolicy Bypass -File .\scripts\rag_rebuild_weekly.ps1 `
  -NewExcelPath "F:\new-data\业绩JL.xlsx" `
  -ApiBase "http://127.0.0.1:8000"
```

脚本会自动完成：

- 备份旧 Excel 到 `database/data/backups/`
- （可选）替换主文件 `database/data/业绩JL.xlsx`
- 调用 `/api/v1/rag/rebuild`
- 写入重建记录到 `docs/rag-rebuild-history.md`

### 9.4 快速回退/切换槽位（A/B）

项目已提供：`scripts/rag_switch_slot.ps1`

```powershell
# 自动切换（A->B 或 B->A）
powershell -ExecutionPolicy Bypass -File .\scripts\rag_switch_slot.ps1

# 指定切到 A
powershell -ExecutionPolicy Bypass -File .\scripts\rag_switch_slot.ps1 -TargetSlot A

# 指定切到 B
powershell -ExecutionPolicy Bypass -File .\scripts\rag_switch_slot.ps1 -TargetSlot B
```

说明：

- 该脚本只改 `chroma_db/active_slot.txt` 指针，不会删除任何向量数据。
- 执行后建议重启后端进程，使运行时立即读取新槽位。
