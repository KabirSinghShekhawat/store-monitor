from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config import settings
from src.store.router import router as store_router
from src.store_status.router import router as store_status_router
from src.timezones.router import router as timezone_router
from src.business_hours.router import router as business_hours_router
from src.report.router import router as report_router
from src.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app: FastAPI = FastAPI(
    title="store monitor",
    version="1.0",
    docs_url="/docs",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def base_route():
    return {"status": "ok"}


app.include_router(report_router, tags=["report"], prefix="/report")
app.include_router(store_router, tags=["store"], prefix="/store")
app.include_router(store_status_router, tags=["store status"], prefix="/store-status")
app.include_router(timezone_router, tags=["timezone"], prefix="/timezone")
app.include_router(business_hours_router, tags=["business hours"], prefix="/business-hours")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        reload=settings.DEBUG_MODE,
        port=settings.PORT,
    )
