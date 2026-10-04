from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import current_user
from ..db import get_db
from ..models import RiskProfile, User
from ..schemas import ProfileIn, ProfileOut

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.put("", response_model=ProfileOut)
def upsert_profile(body: ProfileIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.profile is None:
        user.profile = RiskProfile(**body.model_dump())
    else:
        for k, v in body.model_dump().items():
            setattr(user.profile, k, v)
    db.commit()
    return user.profile
