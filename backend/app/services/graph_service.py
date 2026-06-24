"""
지하철 네트워크 그래프 + Dijkstra 최소 혼잡 경로 탐색.

설계 원칙:
  - 노드 = 역 이름 (str)
  - 엣지 = 인접 역 연결 (양방향)
  - 엣지 가중치 = BASE_TIME + CONGESTION_PENALTY × avg_endpoint_congestion
      → 혼잡도가 높을수록 해당 구간의 가중치(비용)가 커짐
      → Dijkstra 알고리즘은 총 가중치 최소 경로를 탐색
  - Dijkstra 향후 확장 시 이 클래스만 교체/확장하면 됨
"""

import heapq
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from app.data_loader import time_input_to_column
from app.models import PathNode, RouteResponse
from app.services.congestion_service import get_station_avg_congestion_value

# ── 튜닝 파라미터 ──────────────────────────────────────────────────────────────
BASE_TIME_MINUTES: float = 2.0   # 역간 기본 이동 시간(분)
CONGESTION_ALPHA: float = 0.03   # 혼잡도 1 단위당 추가 패널티(분)
# 최종 엣지 가중치 = BASE_TIME + CONGESTION_ALPHA × avg_congestion
# 혼잡도 100 → +3.0분, 혼잡도 150 → +4.5분 패널티


# ── 서울 지하철 노선도 위상 (인접 역 목록) ─────────────────────────────────────
# 실제 서비스에서는 외부 DB/JSON 파일로 분리 권장.
# 현재 데이터에 포함된 1~8호선 순서 기준으로 정의.

LINE_TOPOLOGY: dict[str, list[str]] = {
    # 1호선 (데이터 포함 구간만)
    "1호선": [
        "서울역", "시청", "종각", "종로3가", "종로5가",
        "동대문", "신설동", "동묘앞",
    ],
    # 2호선 순환선 (내선 순서)
    "2호선": [
        "시청", "을지로입구", "을지로3가", "을지로4가",
        "동대문역사문화공원", "신당", "상왕십리", "왕십리",
        "한양대", "뚝섬", "성수", "건대입구", "구의", "강변",
        "잠실나루", "잠실", "잠실새내", "종합운동장", "삼성",
        "선릉", "역삼", "강남", "교대", "서초", "방배",
        "사당", "낙성대", "서울대입구", "봉천", "신림",
        "신대방", "구로디지털단지", "대림", "신도림", "문래",
        "영등포구청", "당산", "합정", "홍대입구", "신촌(지하)",
        "이대", "아현", "충정로",
    ],
    # 3호선
    "3호선": [
        "대화", "주엽", "정발산", "마두", "백석", "대곡", "화정",
        "원당", "원흥", "삼송", "지축", "구파발", "연신내", "불광",
        "녹번", "홍제", "무악재", "독립문", "경복궁", "안국",
        "종로3가", "을지로3가", "충무로", "동대입구", "약수",
        "금호", "옥수", "압구정", "신사", "잠원", "고속터미널",
        "교대", "남부터미널", "양재", "매봉", "도곡",
        "대치", "학여울", "대청", "일원", "수서", "가락시장",
        "경찰병원", "오금",
    ],
    # 4호선
    "4호선": [
        "당고개", "상계", "노원", "창동", "쌍문", "수유",
        "미아", "미아사거리", "길음", "성신여대입구", "한성대입구",
        "혜화", "동대문", "동대문역사문화공원", "충무로",
        "명동", "회현", "서울역", "숙대입구", "삼각지",
        "신용산", "이촌", "동작", "총신대입구(이수)",
        "사당", "남태령",
    ],
    # 5호선 (방화↔마천/하남검단산 분기)
    "5호선": [
        "방화", "개화산", "김포공항", "송정", "마곡",
        "발산", "우장산", "화곡", "까치산", "신정",
        "목동", "오목교", "양평", "영등포구청",
        "영등포시장", "신길", "여의도", "여의나루",
        "마포", "공덕", "애오개", "충정로", "서대문",
        "광화문", "종로3가", "을지로4가", "동대문역사문화공원",
        "청구", "신금호", "행당", "왕십리", "마장",
        "답십리", "장한평", "군자", "아차산", "광나루",
        "천호", "강동",
    ],
    # 6호선
    "6호선": [
        "응암", "역촌", "불광", "독바위", "연신내", "구산",
        "새절", "증산", "디지털미디어시티", "월드컵경기장",
        "마포구청", "망원", "합정", "상수", "광흥창",
        "대흥", "공덕", "효창공원앞", "삼각지", "녹사평",
        "이태원", "한강진", "버티고개", "약수", "청구",
        "신당", "동묘앞", "창신", "보문", "안암",
        "고려대", "월곡", "상월곡", "돌곶이", "석계",
        "태릉입구", "화랑대", "봉화산", "신내",
    ],
    # 7호선
    "7호선": [
        "장암", "도봉산", "수락산", "마들", "노원",
        "중계", "하계", "공릉", "태릉입구", "먹골",
        "중화", "상봉", "면목", "사가정", "용마산",
        "중곡", "군자", "어린이대공원", "건대입구",
        "뚝섬유원지", "청담", "강남구청", "학동",
        "논현", "반포", "고속터미널", "내방", "총신대입구(이수)",
        "남성", "숭실대입구", "상도", "장승배기",
        "신대방삼거리", "보라매", "신풍", "대림",
        "남구로", "가산디지털단지", "철산", "광명사거리",
        "천왕", "온수",
    ],
    # 8호선
    "8호선": [
        "암사", "천호", "강동구청", "몽촌토성", "잠실",
        "석촌", "송파", "가락시장", "문정", "장지",
        "복정", "산성", "남위례", "단대오거리",
        "신흥", "수진", "모란",
    ],
}

# 2호선 성수지선 (성수 ↔ 신설동)
LINE2_SEONGSU_BRANCH = ["성수", "용답", "신답", "신설동"]
# 2호선 신정지선 (신도림 ↔ 까치산)
LINE2_SINDORIM_BRANCH = ["신도림", "도림천", "양천구청", "신정네거리", "까치산"]


def _build_adjacency(topology: dict) -> dict:
    """
    노선별 순서 리스트를 양방향 인접 그래프로 변환.
    반환: { station: [(neighbor, line), ...] }
    2호선은 순환 처리(첫 역과 마지막 역도 연결).
    """
    adj: dict = {}

    def add_edge(a: str, b: str, line: str) -> None:
        adj.setdefault(a, []).append((b, line))
        adj.setdefault(b, []).append((a, line))

    for line, stations in topology.items():
        for i in range(len(stations) - 1):
            add_edge(stations[i], stations[i + 1], line)
        # 2호선 순환
        if line == "2호선":
            add_edge(stations[-1], stations[0], line)

    # 2호선 지선 별도 추가
    for branch in [LINE2_SEONGSU_BRANCH, LINE2_SINDORIM_BRANCH]:
        for i in range(len(branch) - 1):
            add_edge(branch[i], branch[i + 1], "2호선")

    return adj


# 앱 시작 시 1회 빌드
_ADJACENCY: dict = _build_adjacency(LINE_TOPOLOGY)


@dataclass(order=True)
class _HeapEntry:
    """Dijkstra 우선순위 큐 엔트리."""
    weight: float
    station: str = field(compare=False)
    path: List[Tuple[str, float]] = field(compare=False)  # [(역명, 혼잡도), ...]


def find_least_congested_path(
    start: str,
    end: str,
    time_str: str,
    day_type: str = "평일",
) -> RouteResponse:
    """
    Dijkstra 알고리즘으로 혼잡도 최소 경로를 탐색.

    가중치 공식:
      edge_weight = BASE_TIME + CONGESTION_ALPHA × avg(from_congestion, to_congestion)

    이 구조에서 혼잡도는 Dijkstra의 엣지 가중치에 직접 통합되어,
    혼잡한 구간을 우회하는 경로를 자동으로 선택.
    """
    if start not in _ADJACENCY:
        raise ValueError(f"출발역을 그래프에서 찾을 수 없습니다: {start!r}")
    if end not in _ADJACENCY:
        raise ValueError(f"도착역을 그래프에서 찾을 수 없습니다: {end!r}")

    time_col = time_input_to_column(time_str)

    def congestion(station: str) -> float:
        return get_station_avg_congestion_value(station, time_col, day_type)

    def edge_weight(from_s: str, to_s: str) -> float:
        avg_cong = (congestion(from_s) + congestion(to_s)) / 2
        return BASE_TIME_MINUTES + CONGESTION_ALPHA * avg_cong

    dist: dict[str, float] = {start: 0.0}
    heap: list[_HeapEntry] = [
        _HeapEntry(0.0, start, [(start, congestion(start))])
    ]
    visited: set[str] = set()

    while heap:
        entry = heapq.heappop(heap)
        current = entry.station

        if current in visited:
            continue
        visited.add(current)

        if current == end:
            path_nodes: list[PathNode] = []
            cumulative = 0.0
            for i, (stn, cong) in enumerate(entry.path):
                if i > 0:
                    prev_stn = entry.path[i - 1][0]
                    cumulative += edge_weight(prev_stn, stn)
                path_nodes.append(
                    PathNode(
                        station=stn,
                        congestion=round(cong, 1),
                        cumulative_weight=round(cumulative, 2),
                    )
                )
            return RouteResponse(
                start=start,
                end=end,
                day_type=day_type,  # type: ignore[arg-type]
                time_column=time_col,
                path=path_nodes,
                total_weight=round(entry.weight, 2),
                total_stops=len(path_nodes) - 1,
            )

        for neighbor, _ in _ADJACENCY.get(current, []):
            if neighbor in visited:
                continue
            new_weight = entry.weight + edge_weight(current, neighbor)
            if new_weight < dist.get(neighbor, float("inf")):
                dist[neighbor] = new_weight
                heapq.heappush(
                    heap,
                    _HeapEntry(
                        new_weight,
                        neighbor,
                        entry.path + [(neighbor, congestion(neighbor))],
                    ),
                )

    raise ValueError(f"경로를 찾을 수 없습니다: {start!r} → {end!r}")


def get_graph_stats() -> dict:
    """그래프 현황 반환 (디버깅/메타 API용)."""
    return {
        "total_nodes": len(_ADJACENCY),
        "total_edges": sum(len(v) for v in _ADJACENCY.values()) // 2,
        "lines_included": list(LINE_TOPOLOGY.keys()),
    }
