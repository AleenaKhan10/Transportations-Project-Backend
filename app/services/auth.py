from datetime import timedelta

from fastapi.security import OAuth2PasswordRequestForm
from fastapi import APIRouter, Depends, HTTPException, status

from config import settings
from db.models import User, UserCreate
from logic.auth import create_user as create_user_service, authenticate_user, create_access_token


router = APIRouter(prefix=settings.AUTH_ROUTER_PREFIX)

@router.post("/users", response_model=User)
def create_user(user: UserCreate):
    return create_user_service(user)

@router.post(settings.TOKEN_ENDPOINT)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(User(username=form_data.username, password=form_data.password))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
