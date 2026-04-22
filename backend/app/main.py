import logging
from dotenv import load_dotenv

load_dotenv()  # 加载.env文件中的环境变量

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 导入路由
from backend.app.api.v1.endpoints.analyze import router as analyze_router
from backend.app.api.v1.endpoints.report import router as report_router
from backend.app.api.v1.endpoints.tasks import router as tasks_router
from backend.app.api.v1.endpoints.upload import router as upload_router
from backend.app.api.v1.endpoints.ocr import router as ocr_router
from backend.app.api.v1.endpoints.rag import router as rag_router
from backend.app.api.v1.endpoints.ws_tasks import router as ws_tasks_router
from backend.app.db.init_db import init_db

# 配置日志
logging.basicConfig(
    level=logging.INFO,  # 设置日志级别为 INFO
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # 输出到控制台
        logging.FileHandler('backend.log')  # 输出到文件
    ]
)

app = FastAPI()


@app.on_event("startup")
def on_startup() -> None:
    init_db()

# 允许前端访问（解决跨域）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600
)

app.include_router(upload_router, prefix="/api/v1")
app.include_router(analyze_router, prefix="/api/v1")
app.include_router(report_router, prefix="/api/v1")
app.include_router(tasks_router, prefix="/api/v1")
app.include_router(ocr_router, prefix="/api/v1")
app.include_router(rag_router, prefix="/api/v1")
app.include_router(ws_tasks_router, prefix="/api/v1")