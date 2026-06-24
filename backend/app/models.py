"""Pydantic 요청/응답 모델."""

from typing import Literal, Optional
from pydantic import BaseModel, Field


DayType = Literal["평일", "토요일", "일요일"]
Direction = Literal["상선", "하선", "내선", "외선"]


# ── 혼잡도 조회 ───────────────────────────────────────────────

class CongestionResponse(BaseModel):
    station: str = Field(..., description="역 이름")
    line: str = Field(..., description="호선")
    day_type: DayType
    time_column: str = Field(..., description="매칭된 데이터 컬럼 (예: '8시30분')")
    congestion_by_direction: dict[str, float] = Field(
        ..., description="방향별 혼잡도 (0~150+, 100이 적정 혼잡)"
    )
    average_congestion: float = Field(..., description="전 방향 평균 혼잡도")


# ── 노선 혼잡 순위 ────────────────────────────────────────────

class StationRankEntry(BaseModel):
    rank: int
    station: str
    line: str
    average_congestion: float
    congestion_by_direction: dict[str, float]


class LineRankingResponse(BaseModel):
    line: str
    day_type: DayType
    time_column: str
    stations: list[StationRankEntry]


# ── Dijkstra 경로 탐색 ────────────────────────────────────────

class PathNode(BaseModel):
    station: str
    congestion: float = Field(..., description="해당 역의 혼잡도 (가중치 산정에 사용)")
    cumulative_weight: float = Field(..., description="출발역부터 이 역까지의 누적 가중치")


class RouteResponse(BaseModel):
    start: str
    end: str
    day_type: DayType
    time_column: str
    path: list[PathNode]
    total_weight: float = Field(..., description="경로 전체 혼잡 가중치 합계")
    total_stops: int


# ── 메타 정보 ─────────────────────────────────────────────────

class MetaResponse(BaseModel):
    available_lines: list[str]
    available_day_types: list[str]
    time_range: str
    time_slot_interval_minutes: int
