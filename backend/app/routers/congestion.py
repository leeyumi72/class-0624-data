"""혼잡도 관련 API 엔드포인트."""

from typing import Annotated, Optional

from fastapi import APIRouter, HTTPException, Query

from app.data_loader import get_available_lines, get_available_stations, TIME_COLUMNS
from app.models import (
    CongestionResponse,
    LineRankingResponse,
    MetaResponse,
    RouteResponse,
)
from app.services.congestion_service import get_line_ranking, get_station_congestion
from app.services.graph_service import find_least_congested_path, get_graph_stats

router = APIRouter(prefix="/api/congestion", tags=["혼잡도"])


# ── 메타 정보 ─────────────────────────────────────────────────────────────────

@router.get("/meta", response_model=MetaResponse, summary="API 메타 정보")
def meta() -> MetaResponse:
    """사용 가능한 노선, 요일 구분, 시간 범위 등 기본 정보를 반환합니다."""
    return MetaResponse(
        available_lines=get_available_lines(),
        available_day_types=["평일", "토요일", "일요일"],
        time_range="05:30 ~ 00:30",
        time_slot_interval_minutes=30,
    )


@router.get("/stations", summary="전체 역 목록")
def stations() -> dict:
    return {"stations": get_available_stations()}


@router.get("/graph/stats", summary="그래프 노드/엣지 현황")
def graph_stats() -> dict:
    return get_graph_stats()


# ── 단일 역 혼잡도 ────────────────────────────────────────────────────────────

@router.get(
    "/station",
    response_model=CongestionResponse,
    summary="특정 역·시각의 혼잡도 조회",
)
def station_congestion(
    station: Annotated[str, Query(description="역 이름 (예: 강남)")],
    time: Annotated[str, Query(description="시각 HH:MM (예: 08:30)")],
    day_type: Annotated[str, Query(description="평일 | 토요일 | 일요일")] = "평일",
    line: Annotated[Optional[str], Query(description="호선 (환승역 구분 시 입력)")] = None,
) -> CongestionResponse:
    """
    **요청 예시**: `/api/congestion/station?station=강남&time=08:30&day_type=평일`

    반환값에는 방향별(상선/하선 또는 내선/외선) 혼잡도와 평균 혼잡도가 포함됩니다.
    혼잡도 기준: 0~100 여유, 100~130 혼잡, 130+ 매우 혼잡
    """
    try:
        return get_station_congestion(station, time, day_type, line)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── 노선 혼잡 순위 ────────────────────────────────────────────────────────────

@router.get(
    "/line/{line}/ranking",
    response_model=LineRankingResponse,
    summary="특정 노선 전체 역 혼잡 순위",
)
def line_congestion_ranking(
    line: str,
    time: Annotated[str, Query(description="시각 HH:MM (예: 08:30)")],
    day_type: Annotated[str, Query(description="평일 | 토요일 | 일요일")] = "평일",
    top_n: Annotated[Optional[int], Query(description="상위 N개만 반환 (기본: 전체)")] = None,
) -> LineRankingResponse:
    """
    **요청 예시**: `/api/congestion/line/2호선/ranking?time=08:30&top_n=10`

    해당 노선의 전 역을 혼잡도 내림차순으로 정렬해 반환합니다.
    `top_n` 파라미터로 상위 N개만 받을 수 있습니다.
    """
    try:
        result = get_line_ranking(line, time, day_type)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if top_n is not None and top_n > 0:
        result.stations = result.stations[:top_n]

    return result


# ── Dijkstra 최소 혼잡 경로 ───────────────────────────────────────────────────

@router.get(
    "/route",
    response_model=RouteResponse,
    summary="혼잡도 최소 경로 탐색 (Dijkstra)",
)
def least_congested_route(
    start: Annotated[str, Query(description="출발역 (예: 강남)")],
    end: Annotated[str, Query(description="도착역 (예: 홍대입구)")],
    time: Annotated[str, Query(description="시각 HH:MM (예: 08:30)")],
    day_type: Annotated[str, Query(description="평일 | 토요일 | 일요일")] = "평일",
) -> RouteResponse:
    """
    **요청 예시**: `/api/congestion/route?start=강남&end=홍대입구&time=08:30`

    혼잡도를 가중치로 반영한 Dijkstra 알고리즘으로 최적 경로를 탐색합니다.
    단순 최단 경로가 아니라 **가장 덜 혼잡한 경로**를 반환합니다.

    가중치 공식: `edge_weight = 2분 + 0.03 × 평균혼잡도`
    """
    try:
        return find_least_congested_path(start, end, time, day_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
