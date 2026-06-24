"""FastAPI 앱 진입점."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.data_loader import load_dataframe
from app.routers import congestion


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 앱 시작 시 CSV를 메모리에 사전 로드 (첫 요청 지연 방지)
    load_dataframe()
    print("✓ 혼잡도 데이터 로드 완료")
    yield


app = FastAPI(
    title="서울 지하철 혼잡 회피 경로 추천 API",
    description=(
        "서울교통공사 혼잡도 데이터 기반으로 특정 역·시각의 혼잡도를 조회하고, "
        "Dijkstra 알고리즘으로 혼잡도 최소 경로를 탐색합니다."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(congestion.router)

# 프론트엔드 정적 파일 서빙 (http://localhost:8000/app/)
app.mount("/app", StaticFiles(directory="frontend", html=True), name="frontend")


@app.get("/", tags=["root"])
def root() -> dict:
    return {
        "message": "서울 지하철 혼잡 회피 경로 추천 API",
        "frontend": "/app",
        "docs": "/docs",
    }
