"""말투 샘플 로딩 테스트 (PRD §11.5 · Q7)."""

import pytest

from app import tone_samples
from app.report_service import _user_prompt

SAMPLE_MD = """# 내 말투

## 사례 1
주제: 재회운
문장: 지금 먼저 연락하시는 건 권하지 않습니다.

## 사례 2
주제: 연애
문장: 급하게 정하지 마시고 두세 번은 만나 보시면 좋겠습니다.

## 사례 3
문장: 큰돈이 들어오는 달은 아닙니다.

## 사례 4
주제: 대인관계
문장: 굳이 맞추려 하지 않으셔도 됩니다.

## 사례 5
주제: 재물
문장: 나가는 걸 막으시면 그게 버는 것과 같은 시기입니다.
"""


@pytest.fixture(autouse=True)
def clear_cache():
    tone_samples.load.cache_clear()
    yield
    tone_samples.load.cache_clear()


def test_parses_topic_and_text():
    samples = tone_samples.parse(SAMPLE_MD)
    assert len(samples) == 5
    assert samples[0].topic == "재회운"
    assert samples[2].topic is None  # 주제 생략 허용
    assert "권하지 않습니다" in samples[0].text


def test_missing_file_means_inactive(monkeypatch, tmp_path):
    monkeypatch.setattr(tone_samples, "SAMPLES_PATH", tmp_path / "없는파일.md")
    assert tone_samples.load() == []
    assert tone_samples.is_active() is False


def test_under_five_samples_is_not_applied(monkeypatch, tmp_path):
    """표본이 적으면 문체가 잡히지 않고 문장을 베껴 쓰는 부작용이 생긴다."""
    p = tmp_path / "tone_samples.md"
    p.write_text("## 사례 1\n문장: 한 건뿐입니다.\n", encoding="utf-8")
    monkeypatch.setattr(tone_samples, "SAMPLES_PATH", p)
    assert tone_samples.load() == []
    assert tone_samples.is_active() is False


def test_five_samples_activates(monkeypatch, tmp_path):
    p = tmp_path / "tone_samples.md"
    p.write_text(SAMPLE_MD, encoding="utf-8")
    monkeypatch.setattr(tone_samples, "SAMPLES_PATH", p)
    assert len(tone_samples.load()) == 5
    assert tone_samples.is_active() is True


@pytest.mark.parametrize(
    "bad",
    [
        "손님은 1988-03-05 생이시고 흐름이 좋습니다.",
        "연락처 010-1234-5678 로 안내드렸습니다.",
    ],
)
def test_personal_info_is_dropped(monkeypatch, tmp_path, bad):
    """실수로 개인정보를 넣었어도 프롬프트로 나가지 않는다 (PRD §12.9)."""
    p = tmp_path / "tone_samples.md"
    p.write_text(SAMPLE_MD + f"\n## 사례 6\n문장: {bad}\n", encoding="utf-8")
    monkeypatch.setattr(tone_samples, "SAMPLES_PATH", p)
    texts = [s.text for s in tone_samples.load()]
    assert bad not in texts
    assert len(texts) == 5


def test_prompt_includes_samples_when_active(monkeypatch, tmp_path):
    p = tmp_path / "tone_samples.md"
    p.write_text(SAMPLE_MD, encoding="utf-8")
    monkeypatch.setattr(tone_samples, "SAMPLES_PATH", p)

    prompt = _user_prompt("<계산결과>사실</계산결과>", "홍길동", ["재회운"])
    assert "[내 문체 예시]" in prompt
    assert "권하지 않습니다" in prompt
    # 고른 주제의 샘플이 먼저 나와야 한다
    assert prompt.index("(재회운)") < prompt.index("(연애)")
    # 내용을 베끼지 말라는 지시가 함께 있어야 한다
    assert "내용은 참고하지 말고" in prompt


def test_prompt_omits_section_when_inactive(monkeypatch, tmp_path):
    monkeypatch.setattr(tone_samples, "SAMPLES_PATH", tmp_path / "없음.md")
    prompt = _user_prompt("<계산결과>사실</계산결과>", "홍길동", ["재회운"])
    assert "[내 문체 예시]" not in prompt


def test_example_file_is_committed_and_parseable():
    """작성 안내용 예시 파일은 저장소에 있고, 형식이 실제로 파싱된다."""
    example = tone_samples.SAMPLES_PATH.parent / "tone_samples.example.md"
    assert example.exists()
    samples = tone_samples.parse(example.read_text(encoding="utf-8"))
    assert len(samples) >= tone_samples.MIN_SAMPLES


def test_ansi_encoded_file_does_not_crash(monkeypatch, tmp_path):
    """메모장에서 ANSI 로 저장하면 UTF-8 로 못 읽는다 — 그래도 리포트 생성이 죽으면 안 된다."""
    p = tmp_path / "tone_samples.md"
    p.write_bytes("## 사례 1\n문장: 한글 문장입니다.\n".encode("cp949"))
    monkeypatch.setattr(tone_samples, "SAMPLES_PATH", p)
    assert tone_samples.load() == []       # 예외가 아니라 빈 목록
    assert tone_samples.is_active() is False


def test_bom_is_stripped(monkeypatch, tmp_path):
    """메모장이 붙이는 BOM 때문에 첫 사례가 사라지면 안 된다."""
    p = tmp_path / "tone_samples.md"
    p.write_text(SAMPLE_MD, encoding="utf-8-sig")   # BOM 붙여 저장
    monkeypatch.setattr(tone_samples, "SAMPLES_PATH", p)
    samples = tone_samples.load()
    assert len(samples) == 5
    assert samples[0].topic == "재회운"             # BOM 이 남으면 여기가 None 이 된다
