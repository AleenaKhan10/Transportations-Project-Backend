from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import Optional
from uuid import UUID
from logic.auth.security import create_access_token
from models.page_access_token_model import PageAccessTokens
from db.database import engine
from pydantic import BaseModel


router = APIRouter(prefix="/api/page-access-tokens", tags=["page-access-tokens"])

class PageAccessTokenRequest(BaseModel):
    page_name: str
    page_url: str

class PageAccessTokenService:
    @staticmethod
    def create_page_access_token(
        page_name: str,
        page_url: str,
        db: Session
    ) -> PageAccessTokens:
        token_data = {"page_name": page_name, "page_url": page_url}
        jwt_token, _ = create_access_token(token_data)

        new_token = PageAccessTokens(
            page_name=page_name,
            page_url=page_url,
            page_access_token=jwt_token
        )

        db.add(new_token)
        db.commit()
        db.refresh(new_token)

        return new_token

    @staticmethod
    def get_page_access_token(token_id: UUID, db: Session) -> Optional[PageAccessTokens]:
        return db.get(PageAccessTokens, token_id)

    @staticmethod
    def delete_page_access_token(token_id: UUID, db: Session) -> bool:
        token = db.get(PageAccessTokens, token_id)
        if token:
            db.delete(token)
            db.commit()
            return True
        return False

@router.get("/get-all")
async def get_all_tokens():
    with Session(engine) as session:
        try:
            records = session.query(PageAccessTokens).all()
            return {"message": "All records fetched successfully", "data": records}
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/")
async def create_token(payload: PageAccessTokenRequest):
    with Session(engine) as session:
        try:
            token = PageAccessTokenService.create_page_access_token(
                payload.page_name,
                payload.page_url,
                session
            )
            return token
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{token_id}")
async def get_token(token_id: UUID):
    with Session(engine) as session:
        token = PageAccessTokenService.get_page_access_token(token_id, session)
        if token:
            return token
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found")


@router.delete("/{token_id}")
async def delete_token(token_id: UUID):
    with Session(engine) as session:
        if PageAccessTokenService.delete_page_access_token(token_id, session):
            return {"message": "Token deleted successfully"}
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found")

@router.post("/verify-token")
async def verify_token(page_access_token: str):
    """
    Verify if a given token exists in the database.
    """
    with Session(engine) as session:
        try:
            token_record = session.query(PageAccessTokens).filter(
                PageAccessTokens.page_access_token == page_access_token
            ).first()

            if token_record:
                return {
                    "valid": True,
                    "message": "Token verified successfully",
                    "data": {
                        "page_name": token_record.page_name,
                        "page_url": token_record.page_url,
                        "id": str(token_record.id),
                    },
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token"
                )

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            )
