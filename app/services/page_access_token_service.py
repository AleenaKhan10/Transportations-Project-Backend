from fastapi import APIRouter, HTTPException, status
from sqlmodel import Session
from typing import Optional
from uuid import UUID
from logic.auth.security import create_access_token
from models.page_access_token_model import PageAccessTokens
from db.database import engine
from pydantic import BaseModel

router = APIRouter(prefix="/api/page-access-tokens", tags=["page-access-tokens"])

# -----------------------------
# Pydantic Model
# -----------------------------
class PageAccessTokenRequest(BaseModel):
    page_name: str
    page_url: str
    filter: Optional[str] = None  # new optional field

# -----------------------------
# Service Layer
# -----------------------------
class PageAccessTokenService:
    @staticmethod
    def create_or_update_page_access_token(
        page_name: str,
        page_url: str,
        db: Session,
        filter: Optional[str] = None
    ) -> PageAccessTokens:
        """
        Create or update token considering page_name, page_url, and optional filter.
        """
        existing_record = db.query(PageAccessTokens).filter(
            PageAccessTokens.page_name == page_name,
            PageAccessTokens.page_url == page_url,
            PageAccessTokens.filter == filter  # check filter too
        ).first()

        token_data = {"page_name": page_name, "page_url": page_url, "filter": filter}
        jwt_token, _ = create_access_token(token_data)

        if existing_record:
            existing_record.page_access_token = jwt_token
            db.commit()
            db.refresh(existing_record)
            return existing_record

        new_token = PageAccessTokens(
            page_name=page_name,
            page_url=page_url,
            filter=filter,
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
    def nullify_token_only(token_id: UUID, db: Session) -> bool:
        token_record = db.get(PageAccessTokens, token_id)
        if token_record:
            token_record.page_access_token = None
            db.commit()
            return True
        return False

# -----------------------------
# Routes
# -----------------------------

@router.get("/get-all")
async def get_all_tokens():
    with Session(engine) as session:
        try:
            records = session.query(PageAccessTokens).all()
            return {
                "message": "All records fetched successfully",
                "data": records
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )

@router.post("/")
async def create_or_update_token(payload: PageAccessTokenRequest):
    with Session(engine) as session:
        try:
            token = PageAccessTokenService.create_or_update_page_access_token(
                payload.page_name,
                payload.page_url,
                session,
                payload.filter  # pass the optional filter
            )
            return {
                "message": "Token created or updated successfully",
                "data": token
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )

@router.get("/{token_id}")
async def get_token(token_id: UUID):
    with Session(engine) as session:
        token = PageAccessTokenService.get_page_access_token(token_id, session)
        if token:
            return token
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found"
        )

@router.delete("/{token_id}")
async def delete_token(token_id: UUID):
    with Session(engine) as session:
        if PageAccessTokenService.nullify_token_only(token_id, session):
            return {"message": "Token field set to NULL successfully"}
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found"
        )

@router.post("/verify-token")
async def verify_token(page_access_token: str):
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
                        "filter": token_record.filter,
                        "id": str(token_record.id),
                    },
                }

            return {
                "valid": False,
                "message": "",
                "data": None
            }

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
