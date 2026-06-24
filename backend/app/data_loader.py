"""
CSV 로딩 및 시간 컬럼 매칭 전처리 모듈.
앱 시작 시 한 번만 데이터를 메모리에 로드하고, 이후 조회는 캐시된 DataFrame을 사용.
"""

from pathlib import Path
from functools import lru_cache

import pandas as pd

# 데이터 파일 경로 (backend/ 기준으로 상위 디렉터리의 CSV)
DATA_PATH = Path(__file__).parent.parent.parent / "processed_subway_congestion.csv"

# 데이터에 존재하는 모든 시간 슬롯 (30분 단위)
TIME_COLUMNS: list[str] = [
    "5시30분", "6시00분", "6시30분", "7시00분", "7시30분",
    "8시00분", "8시30분", "9시00분", "9시30분", "10시00분",
    "10시30분", "11시00분", "11시30분", "12시00분", "12시30분",
    "13시00분", "13시30분", "14시00분", "14시30분", "15시00분",
    "15시30분", "16시00분", "16시30분", "17시00분", "17시30분",
    "18시00분", "18시30분", "19시00분", "19시30분", "20시00분",
    "20시30분", "21시00분", "21시30분", "22시00분", "22시30분",
    "23시00분", "23시30분", "00시00분", "00시30분",
]

TIME_COLUMN_SET = set(TIME_COLUMNS)


def time_input_to_column(time_str: str) -> str:
    """
    사용자 입력 시각(HH:MM)을 데이터 컬럼명으로 변환.

    규칙: 가장 가까운 30분 슬롯으로 반올림
      - 분 < 15  → :00 슬롯
      - 15 ≤ 분 < 45 → :30 슬롯
      - 분 ≥ 45  → 다음 시각의 :00 슬롯

    Examples:
      '08:30' → '8시30분'
      '08:14' → '8시00분'
      '08:45' → '9시00분'
      '18:00' → '18시00분'
    """
    try:
        hour_str, min_str = time_str.strip().split(":")
        h, m = int(hour_str), int(min_str)
    except (ValueError, AttributeError):
        raise ValueError(f"시간 형식이 올바르지 않습니다 (예: '08:30'): {time_str!r}")

    if m < 15:
        slot_h, slot_m = h, 0
    elif m < 45:
        slot_h, slot_m = h, 30
    else:
        slot_h, slot_m = (h + 1) % 24, 0

    col = f"{slot_h}시{slot_m:02d}분"

    if col not in TIME_COLUMN_SET:
        raise ValueError(
            f"운행 시간 범위(05:30 ~ 00:30)를 벗어난 시각입니다: {time_str!r} → {col!r}"
        )
    return col


@lru_cache(maxsize=1)
def load_dataframe() -> pd.DataFrame:
    """CSV를 메모리에 로드 (최초 1회만 실행, 이후 캐시 반환)."""
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"데이터 파일을 찾을 수 없습니다: {DATA_PATH}")

    df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")

    # 시간 컬럼 숫자 변환 (비어 있는 셀은 0으로 처리)
    time_cols_in_df = [c for c in df.columns if c in TIME_COLUMN_SET]
    df[time_cols_in_df] = (
        df[time_cols_in_df].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    )

    return df


def get_available_stations() -> list[str]:
    return sorted(load_dataframe()["출발역"].unique().tolist())


def get_available_lines() -> list[str]:
    return sorted(load_dataframe()["호선"].unique().tolist())
