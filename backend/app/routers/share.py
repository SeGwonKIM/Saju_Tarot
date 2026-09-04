"""공유 링크 열람과 상담자용 목록 (PRD §10.3).

공유는 **읽기 전용**이다. 토큰을 아는 사람은 그 리포트만 볼 수 있고
다른 리포트에는 닿지 못한다.
"""

from fastapi import APIRouter, Depends, HTTPException, Path

from ..admin_auth import require_admin
from pydantic import BaseModel

from ..storage import Storage, get_storage, redact_for_share

router = APIRouter(tags=["share"])


class SharedReading(BaseModel):
    id: str
    payload: dict
    """계산 결과와 리포트. 이름·생년월일은 들어 있지 않다"""


class ListItem(BaseModel):
    id: str
    masked_name: str
    gender: str
    created_at: str
    expires_at: str


@router.get("/share/{token}", response_model=SharedReading)
def read_shared(
    token: str = Path(min_length=10, max_length=64),
    storage: Storage = Depends(get_storage),
) -> SharedReading:
    """만료·부재를 구분하지 않고 404 로 통일한다 — 존재 여부가 새면 안 된다 (§10.6)."""
    stored = storage.get_by_share(token)
    if stored is None:
        raise HTTPException(
            status_code=404, detail="링크가 만료되었거나 없는 페이지입니다."
        )
    return SharedReading(id=stored.id, payload=redact_for_share(stored.payload))


@router.get(
    "/readings-list",
    response_model=list[ListItem],
    dependencies=[Depends(require_admin)],
)
def list_recent(storage: Storage = Depends(get_storage)) -> list[ListItem]:
    """상담자용 최근 목록 — **X-Admin-Token 헤더 필요**.

    이 창구가 열려 있으면 누구나 모든 리포트 id 를 받아 전체 내용을 볼 수 있다
    (점검에서 실제로 뚫려 있었다). 이름은 마스킹해서 보낸다 (PRD §12.14).
    """
    return [
        ListItem(
            id=r.id,
            masked_name=r.masked_name,
            gender=r.gender,
            created_at=r.created_at.isoformat(timespec="minutes"),
            expires_at=r.expires_at.isoformat(timespec="minutes"),
        )
        for r in storage.recent()
    ]
