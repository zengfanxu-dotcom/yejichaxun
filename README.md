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

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 联系方式

- 项目维护者：Your Name
- 邮箱：your.email@example.com
- 项目地址：https://github.com/yourusername/yejichaxun