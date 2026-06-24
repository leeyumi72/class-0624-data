"""
혼잡도 조회 비즈니스 로직.
단일 역 혼잡도 반환 및 노선 전체 혼잡 순위 계산을 담당.
"""

from typing import Optional

from app.data_loader import load_dataframe, time_input_to_column
from app.models import (
    CongestionResponse,
    LineRankingResponse,
    StationRankEntry,
)


def get_station_congestion(
    station: str,
    time_str: str,
    day_type: str = "평일",
    line: Optional[str] = None,
) -> CongestionResponse:
    """
    특정 역·시각의 방향별 혼잡도를 반환.

    Args:
        station:  역 이름 (예: '강남')
        time_str: 'HH:MM' 형식 (예: '08:30')
        day_type: '평일' | '토요일' | '일요일'
        line:     호선 지정 시 해당 호선만 조회 (환승역 구분용)
    """
    df = load_dataframe()
    time_col = time_input_to_column(time_str)

    mask = (df["출발역"] == station) & (df["요일구분"] == day_type)
    if line:
        mask &= df["호선"] == line

    rows = df[mask]
    if rows.empty:
        raise ValueError(
            f"데이터를 찾을 수 없습니다: 역={station!r}, 요일={day_type!r}"
            + (f", 호선={line!r}" if line else "")
        )

    congestion_by_dir: dict[str, float] = {}
    for _, row in rows.iterrows():
        direction = row["상하구분"]
        congestion_by_dir[direction] = round(float(row[time_col]), 1)

    avg = round(sum(congestion_by_dir.values()) / len(congestion_by_dir), 1)
    # 대표 호선 (line 인자가 없을 때 첫 번째 행 기준)
    representative_line = line or rows.iloc[0]["호선"]

    return CongestionResponse(
        station=station,
        line=representative_line,
        day_type=day_type,  # type: ignore[arg-type]
        time_column=time_col,
        congestion_by_direction=congestion_by_dir,
        average_congestion=avg,
    )


def get_line_ranking(
    line: str,
    time_str: str,
    day_type: str = "평일",
) -> LineRankingResponse:
    """
    특정 노선의 모든 역을 혼잡도 내림차순으로 정렬해 반환.

    혼잡도는 해당 역의 전 방향(상선+하선 또는 내선+외선) 평균값 기준.
    """
    df = load_dataframe()
    time_col = time_input_to_column(time_str)

    mask = (df["호선"] == line) & (df["요일구분"] == day_type)
    rows = df[mask]
    if rows.empty:
        raise ValueError(f"데이터를 찾을 수 없습니다: 호선={line!r}, 요일={day_type!r}")

    # 역별 방향 평균 집계
    grouped = rows.groupby("출발역")[time_col].mean().reset_index()
    grouped.columns = ["출발역", "평균혼잡도"]
    grouped = grouped.sort_values("평균혼잡도", ascending=False).reset_index(drop=True)

    # 방향별 상세 정보를 함께 제공
    dir_detail: dict[str, dict[str, float]] = {}
    for _, row in rows.iterrows():
        s = row["출발역"]
        if s not in dir_detail:
            dir_detail[s] = {}
        dir_detail[s][row["상하구분"]] = round(float(row[time_col]), 1)

    entries: list[StationRankEntry] = []
    for rank_idx, g_row in grouped.iterrows():
        station_name = g_row["출발역"]
        entries.append(
            StationRankEntry(
                rank=int(rank_idx) + 1,
                station=station_name,
                line=line,
                average_congestion=round(float(g_row["평균혼잡도"]), 1),
                congestion_by_direction=dir_detail.get(station_name, {}),
            )
        )

    return LineRankingResponse(
        line=line,
        day_type=day_type,  # type: ignore[arg-type]
        time_column=time_col,
        stations=entries,
    )


def get_station_avg_congestion_value(
    station: str,
    time_col: str,
    day_type: str,
    line: Optional[str] = None,
) -> float:
    """
    그래프 가중치 계산 내부 헬퍼.
    역의 전 방향 평균 혼잡도를 float으로 반환.
    데이터가 없으면 기본값 50.0 반환 (중간 혼잡도 가정).
    """
    df = load_dataframe()
    mask = (df["출발역"] == station) & (df["요일구분"] == day_type)
    if line:
        mask &= df["호선"] == line

    rows = df[mask]
    if rows.empty or time_col not in df.columns:
        return 50.0

    return float(rows[time_col].mean())
