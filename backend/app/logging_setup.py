"""로그 마스킹 (PRD §12.15).

로그에 이름·생년월일·토큰·키가 남지 않게 한다.
남기는 것은 method / path / status / latency / trace_id 뿐이다.
"""

import logging
import re

# 값이 노출되면 안 되는 키 이름들
SENSITIVE_KEYS = (
    "name",
    "birth_date",
    "birth_time",
    "birth_date_input",
    "solar_datetime",
    "authorization",
    "token",
    "api_key",
    "apikey",
    "password",
    "secret",
)

# key=value / "key": "value" 양쪽 형태를 잡는다.
# key= 형태는 값에 공백이 들어갈 수 있으므로(예: authorization=Bearer xxx)
# 줄 끝까지 가린다. 덜 가리는 것보다 더 가리는 쪽이 안전하다.
_PATTERNS = [
    re.compile(rf'(?i)("{k}"\s*:\s*")([^"]*)(")') for k in SENSITIVE_KEYS
] + [
    re.compile(rf"(?im)\b({k}\s*=\s*)(.+)$") for k in SENSITIVE_KEYS
] + [
    # 값 자체가 비밀로 보이는 경우 (키 이름이 달라도)
    re.compile(r"(sk-ant-)[A-Za-z0-9_-]+"),
    re.compile(r"(eyJ[A-Za-z0-9_-]{10,}\.)[A-Za-z0-9_.-]+"),
]


# 주소에 담긴 비밀 — 공유 토큰과 리포트 id 는 그 자체가 접근 권한이다.
# 로그(터미널 캡처 포함)에 남으면 남의 리포트에 그대로 들어갈 수 있다.
_PATH_SECRETS = [
    re.compile(r"(/share/)[A-Za-z0-9_-]{8,}"),
    re.compile(r"(/readings/)r-[0-9a-f]{8,}"),
]


def mask_path(path: str) -> str:
    for p in _PATH_SECRETS:
        path = p.sub(r"\1***", path)
    return path


def mask(text: str) -> str:
    # 경로에 담긴 비밀은 uvicorn 접근 로그에도 찍힌다 — 모든 로거에 적용해야 한다
    text = mask_path(text)
    for p in _PATTERNS:
        if p.groups >= 3:
            text = p.sub(r"\1***\3", text)
        else:
            text = p.sub(r"\1***", text)
    return text


class MaskingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = mask(record.msg)
        if record.args:
            record.args = tuple(
                mask(a) if isinstance(a, str) else a for a in record.args
            )
        return True


def setup_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    )
    handler.addFilter(MaskingFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        lg = logging.getLogger(name)
        lg.handlers.clear()
        lg.addFilter(MaskingFilter())
        lg.propagate = True
