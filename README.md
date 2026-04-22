# 业绩匹配Agent项目

一个基于AI的业绩匹配系统，用于分析和匹配企业业绩数据。

## 项目结构

```
yejichaxun/
├── frontend/                 # 前端React应用
│   ├── public/
│   ├── src/
│   │   ├── components/       # 可复用组件
│   │   │   ├── FileUpload/    # 文件上传组件
│   │   │   ├── ResultDisplay/ # 结果展示组件
│   │   │   └── Visualization/ # 可视化图表组件
│   │   ├── pages/           # 页面组件
│   │   │   ├── Home/        # 主页面
│   │   │   ├── Analysis/    # 分析结果页面
│   │   │   └── History/     # 历史记录页面
│   │   ├── services/        # API服务
│   │   └── utils/           # 工具函数
│   └── package.json
│
├── backend/                 # 后端FastAPI应用
│   ├── app/
│   │   ├── api/            # API路由
│   │   │   ├── v1/
│   │   │   │   ├── endpoints/
│   │   │   │   │   ├── upload.py    # 文件上传接口
│   │   │   │   │   ├── analyze.py   # 分析接口
│   │   │   │   │   └── report.py    # 报告接口
│   │   │   │   └── dependencies/    # 依赖注入
│   │   │   └── websocket/           # WebSocket接口
│   │   ├── core/           # 核心模块
│   │   │   ├── agent/      # Agent核心逻辑
│   │   │   │   ├── goal_parser.py   # 目标解析器
│   │   │   │   ├── planner.py       # 规划器
│   │   │   │   ├── executor.py      # 执行器
│   │   │   │   └── memory.py        # 记忆模块
│   │   │   ├── tools/      # 工具模块
│   │   │   │   ├── ocr_tool.py      # OCR工具
│   │   │   │   ├── search_tool.py   # 搜索工具
│   │   │   │   ├── calculator.py    # 计算工具
│   │   │   │   └── report_tool.py   # 报告工具
│   │   │   └── models/     # 数据模型
│   │   │       ├── tender.py        # 招标文件模型
│   │   │       ├── project.py       # 项目模型
│   │   │       └── analysis.py      # 分析结果模型
│   │   ├── config/         # 配置文件
│   │   ├── database/       # 数据库相关
│   │   │   ├── connection.py        # 数据库连接
│   │   │   └── repositories/        # 数据访问层
│   │   └── utils/          # 工具函数
│   ├── requirements.txt
│   └── main.py             # 应用入口
│
├── database/               # 数据库相关
│   ├── migrations/         # 数据库迁移
│   ├── scripts/            # 数据导入脚本
│   └── data/               # 示例数据
│
├── docs/                   # 项目文档
│   ├── api/                # API文档
│   ├── design/             # 设计文档
│   └── user_guide/         # 用户指南
│
├── tests/                  # 测试文件
│   ├── unit/               # 单元测试
│   ├── integration/        # 集成测试
│   └── e2e/                # 端到端测试
│
├── docker/                 # Docker配置
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── scripts/                # 脚本文件
│   ├── setup.sh            # 安装脚本
│   └── deploy.sh           # 部署脚本
│
├── .env.example            # 环境变量示例
├── .gitignore
├── README.md
└── pyproject.toml          # Python项目配置
```

## 功能特性

- **智能文件解析**：支持多种格式的文件解析（PDF、Excel、Word等）
- **AI分析引擎**：基于Transformer模型的智能分析
- **实时数据可视化**：动态图表展示分析结果
- **历史记录管理**：保存和查询历史分析记录
- **WebSocket实时通信**：实时更新分析进度
- **多模态数据处理**：文本、图像、表格数据的综合处理

## 技术栈

- **前端**：React 18 + TypeScript + Ant Design
- **后端**：FastAPI + Python 3.9+
- **数据库**：PostgreSQL + Redis
- **AI框架**：Transformers + LangChain + TensorFlow/PyTorch
- **部署**：Docker + Docker Compose

## 快速开始

### 前端开发

```bash
cd frontend
npm install
npm start
```

### 后端开发

```bash
# 推荐 Python 3.11（避免 pandas 在 Python 3.14 下触发源码编译失败）
cd F:\yejichaxun
python -m venv .venv311  # 或 py -3.11 -m venv .venv311 (Windows)
source .venv311/bin/activate  # Linux/Mac
# 或 .\.venv311\Scripts\activate  # Windows
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload
```

### 数据库设置

```bash
cd database
alembic upgrade head
```

## 部署

```bash
docker-compose up -d
```

## 今日开发总结（2026-04-16）

围绕 M2-M5 连续推进，已完成从“任务可执行”到“任务可观测、可运维、可实时推送”的闭环升级。

- 后端任务能力增强：
  - 新增任务取消接口 `POST /api/v1/tasks/{task_id}/cancel`（仅 `queued/running` 可取消）。
  - `POST /api/v1/analyze/{task_id}` 支持 `cancelled` 任务重置后重跑。
  - 增加任务事件流与详情查询：`GET /api/v1/tasks/{task_id}/events`。
  - 增加任务指标接口：`GET /api/v1/tasks/metrics`（成功率、失败率、失败分布、重试成功率、阶段均耗）。
- 前端交互增强：
  - 历史面板支持状态筛选、失败/取消重试、运行中取消。
  - 增加任务详情抽屉（阶段日志、阶段耗时、总耗时、复制 task_id、错误高亮）。
  - 上传分析链路修复终态收口问题（`cancelled` 不再轮询超时）。
- M5 WebSocket 实时化：
  - 新增 `WS /api/v1/ws/tasks/{task_id}`，连接后先发 `task.snapshot`，状态变化推送 `task.update`。
  - 前端上传流程优先使用 WebSocket 推送，连接异常时自动降级回轮询。
- 状态机规则固化：
  - 后端统一状态常量：`backend/app/core/task_state.py`。
  - 前端统一状态常量：`frontend/src/constants/taskState.js`。
  - 规则文档：`docs/task-state-machine.md`。

## 与总进度对比报告

当前里程碑对比（按既定计划 M1-M5）：

- M1（建表 + 上传建任务 + 任务状态查询）：已完成。
- M2（分析链路接入 OCR/RAG/LLM）：已完成，并补充取消感知与重试。
- M3（报告查询 + 前端轮询串联）：已完成，异常收口已修复。
- M4（历史列表 + 失败重试 + 取消任务）：已完成，并扩展了详情抽屉与运维可观测信息。
- M5（WebSocket 进度推送替换轮询，可选）：核心能力已完成，且已实现“WebSocket 优先 + 轮询降级”。

综合结论：

- 计划完成度：已达到并超过既定范围（含指标与可观测性增强）。
- 与原计划偏差：正向偏差，提前落地了部分运维诊断能力（events + metrics + 详情排障）。
- 当前主要缺口：自动化测试覆盖、生产级 WebSocket 扩展能力、部署文档与监控告警仍需补齐。

## 接下来的开发规划（建议）

建议进入“稳定化与上线准备”阶段，优先级如下：

- P0：质量与回归
  - 增加接口测试：`upload/analyze/tasks/report/cancel/events/metrics/ws`。
  - 增加关键状态机测试：取消、重试、并发请求、终态保护。
  - 增加前端关键流程 E2E：上传->分析->报告、取消->重试、WS 断连降级。
- P1：可运维性
  - 为任务链路补充结构化日志字段（task_id、stage、latency、error_code）。
  - 指标接入监控（失败率、阶段耗时、重试成功率）并配置告警阈值。
  - 评估 WebSocket 多进程/多实例场景下的广播方案（如 Redis Pub/Sub）。
- P1：体验优化
  - 历史列表支持分页、搜索和按时间范围过滤。
  - 详情抽屉补充事件导出/复制诊断信息能力。
  - 任务进行中在历史列表实现更细粒度实时刷新策略。
- P2：交付与文档
  - 更新接口文档（含 WS 消息格式与错误码约定）。
  - 补充部署说明（开发/测试/生产环境差异、环境变量清单）。
  - 输出里程碑验收清单与上线回滚预案。

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 联系方式

- 项目维护者：Fanxu Zeng
- 邮箱：zengfanxu9@gmail.com
- 项目地址：https://github.com/yourusername/yejichaxun
