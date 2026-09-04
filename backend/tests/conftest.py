"""테스트 공통 설정.

**테스트는 절대 실제 LLM API 를 호출하지 않는다.** 느려지고 비용이 들고,
외부 서비스 상태에 따라 결과가 흔들린다. 문장 생성기를 가짜로 갈아끼운다.

실제 호출까지 확인하려면 live 마커를 붙인 테스트를 명시적으로 실행한다:
  ./.venv/Scripts/python.exe -m pytest -m live
"""

import pytest

from app.main import app
from app.report_service import Report
from app.routers.readings import get_generator


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
