from fastapi import APIRouter
from .endpoints.upload import router as upload_router
from .endpoints.ocr import router as ocr_router

api_router = APIRouter()
api_router.include_router(upload_router, prefix="/upload", tags=["upload"])
api_router.include_router(ocr_router, prefix="/ocr", tags=["ocr"])