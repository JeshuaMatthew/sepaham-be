from contextlib import asynccontextmanager
from pathlib import Path
import sys
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from src.app.core.config import settings
from src.app.core.database import AsyncSessionLocal
from src.app.core.logger import app_logger
from src.app.modules.auth.router import router as auth_router
from src.app.modules.profile.router import router as profile_router
from src.app.modules.catalog.router import router as catalog_router
from src.app.modules.roadmap.router import router as roadmap_router
from src.app.modules.collab.router import router as collab_router
from src.app.modules.github.router import router as github_router
from src.app.modules.community.router import (
    community_router,
    chat_router,
)
from src.app.modules.faculty.router import router as faculty_router
from src.app.modules.realtime.router import router as realtime_router
from src.app.modules.onboarding.router import router as onboarding_router
from src.app.modules.ai.router import router as ai_router

# Ensure uploads directory exists
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI): 
    async with AsyncSessionLocal() as session:
        try:
            await session.execute(text("SELECT 1"))
            app_logger.info("DB connection SUCCESS! :)")
        except Exception as e:
            app_logger.error("DB connection FAILED! :(")
            app_logger.error(f"{str(e)}")
            sys.exit(1)
        
    yield  
    app_logger.info("Shutting down server..")

app = FastAPI(title="Sepaham's Rest API Backend", lifespan=lifespan)

# CORS Configuration
origins = [o.strip() for o in settings.CORS_ALLOWED_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Error Handlers to conform to: {"error": "pesan error"}
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Extract first error message
    err_msgs = []
    for err in exc.errors():
        msg = err.get("msg", "Input tidak valid")
        if "Value error, " in msg:
            msg = msg.replace("Value error, ", "")
        err_msgs.append(msg)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": "; ".join(err_msgs)},
    )

# Static files for uploads
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Include Routers
app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(catalog_router)
app.include_router(roadmap_router)
app.include_router(collab_router)
app.include_router(github_router)
app.include_router(community_router)
app.include_router(chat_router)
app.include_router(faculty_router)
app.include_router(realtime_router)
app.include_router(onboarding_router, prefix="/api/onboarding")
app.include_router(onboarding_router, prefix="/api/v1/onboarding")
app.include_router(ai_router)

@app.get("/health", status_code=status.HTTP_200_OK)
@app.get("/api/health", status_code=status.HTTP_200_OK)
async def health_check():
    return {"status": "ok"}

@app.get("/")
async def read_root():
    return {"message": "Sepaham Backend API is running"}


