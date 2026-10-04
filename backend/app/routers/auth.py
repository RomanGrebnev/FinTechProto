from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import create_token, current_user, hash_password, verify_password
from ..db import get_db
from ..models import Recommendation, User
from ..schemas import Credentials, DeleteAccount, Me, Token

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup", response_model=Token, status_code=201)
def signup(body: Credentials, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "An account with this email already exists")
    user = User(email=email, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    return Token(access_token=create_token(user.id))


@router.post("/login", response_model=Token)
def login(body: Credentials, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    return Token(access_token=create_token(user.id))


@router.get("/me", response_model=Me)
def me(user: User = Depends(current_user)):
    return Me(id=user.id, email=user.email, profile=user.profile)


@router.delete("/me", status_code=204)
def delete_me(body: DeleteAccount, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """GDPR Art. 17: erase the account and all its data (profile, holdings, recommendations)."""
    if not verify_password(body.password, user.password_hash):
        raise HTTPException(403, "Incorrect password")
    # Recommendations are removed explicitly, then the user (cascades to profile and holdings)
    db.query(Recommendation).filter(Recommendation.user_id == user.id).delete(synchronize_session=False)
    db.expire(user)
    db.delete(user)
    db.commit()
    return Response(status_code=204)
