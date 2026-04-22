from fastapi import APIRouter
from .endpoints.analyze import router as analyze_router
from .endpoints.report import router as report_router
from .endpoints.tasks import router as tasks_router
from .endpoints.upload import router as upload_router
from .endpoints.ocr import router as ocr_router

api_router = APIRouter()
api_router.include_router(upload_router, tags=["upload"])
api_router.include_router(analyze_router, tags=["analyze"])
api_router.include_router(report_router, tags=["report"])
api_router.include_router(tasks_router, tags=["tasks"])
api_router.include_router(ocr_router, tags=["ocr"])