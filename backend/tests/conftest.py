"""테스트 공통 설정.

**테스트는 절대 실제 LLM API 를 호출하지 않는다.** 느려지고 비용이 들고,
외부 서비스 상태에 따라 결과가 흔들린다. 문장 생성기를 가짜로 갈아끼운다.

실제 호출까지 확인하려면 live 마커를 붙인 테스트를 명시적으로 실행한다:
  ./.venv/Scripts/python.exe -m pytest -m live
"""

import pytest

from app import rate_limit, storage as storage_module
from app.main import app
from app.report_service import Report
from app.routers.readings import get_generator


@pytest.fixture(autouse=True, scope="session")
def isolated_db(tmp_path_factory):
    """테스트는 **임시 DB** 를 쓴다.

    이 장치가 없으면 테스트가 실제 data/readings.db 에 행을 쌓는다
    (실제로 433행이 쌓여 있었다). 손님 데이터와 섞이는 것도 문제지만,
    v3.2 의 "같은 사주·같은 이름이면 풀이를 재사용한다" 규칙 때문에
    **지난 실행분이 이번 실행에 되살아나** 테스트가 엉뚱하게 통과·실패한다.
    실제로 그 일이 일어나서 이 격리를 넣었다.
    """
    storage_module._storage = None
    storage_module.DB_PATH = tmp_path_factory.mktemp("db") / "test.db"
    yield
    storage_module._storage = None


class FakeReportGenerator:
    """호출 인자를 기록하고 고정 문장을 돌려준다."""

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[tuple[str, str, list[str]]] = []

    def generate(self, facts: str, name: str, topics: list[str]) -> Report | None:
        self.calls.append((facts, name, topics))
        if self.fail:
            return None
        return Report(
            saju_reading=["타고난 결 첫 줄.", "둘째 줄.", "셋째 줄."],
            monthly_flow=["첫째 줄입니다.", "둘째 줄입니다.", "셋째 줄입니다."],
            advice={t: f"{t} 조언입니다." for t in topics},
            keywords=["정리", "기다림"],
            model="fake-model",
        )


@pytest.fixture
def fake_generator():
    return FakeReportGenerator()


@pytest.fixture(autouse=True)
def no_network_generator(request):
    """모든 테스트에서 문장 생성기를 가짜로 바꾼다 (live 마커는 예외)."""
    if request.node.get_closest_marker("live"):
        yield None
        return
    fake = FakeReportGenerator()
    app.dependency_overrides[get_generator] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_generator, None)


@pytest.fixture(autouse=True)
def fresh_rate_limit():
    """테스트끼리 한도를 물려주지 않는다.

    이 장치가 없으면 11번째 테스트부터 429 로 무더기 실패한다
    (레이트리밋이 실제로 동작한다는 증거이기도 하다).
    """
    rate_limit.reset()
    yield
    rate_limit.reset()
