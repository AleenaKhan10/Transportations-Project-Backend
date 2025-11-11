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


# -----------------------------
# Service Layer
# -----------------------------
class PageAccessTokenService:
    @staticmethod
    def create_or_update_page_access_token(
        page_name: str,
        page_url: str,
        db: Session
    ) -> PageAccessTokens:
        """
        If record with same page_name & page_url exists → update its token.
        If not → create new record.
        """
        existing_record = db.query(PageAccessTokens).filter(
            PageAccessTokens.page_name == page_name,
            PageAccessTokens.page_url == page_url
        ).first()

        # Always generate a fresh token
        token_data = {"page_name": page_name, "page_url": page_url}
        jwt_token, _ = create_access_token(token_data)

        if existing_record:
            # ✅ Update existing token only
            existing_record.page_access_token = jwt_token
            db.commit()
            db.refresh(existing_record)
            return existing_record

        # ✅ Otherwise create a new record
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
    def nullify_token_only(token_id: UUID, db: Session) -> bool:
        """
        Set page_access_token to None instead of deleting record.
        """
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
    """
    Fetch all page access token records.
    """
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
    """
    Create or update a token for the given page.
    - If record exists (even with token=None) → update token.
    - If no record exists → create new one.
    """
    with Session(engine) as session:
        try:
            token = PageAccessTokenService.create_or_update_page_access_token(
                payload.page_name,
                payload.page_url,
                session
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
    """
    Fetch a specific token record by ID.
    """
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
    """
    Nullify the page_access_token instead of deleting the record.
    """
    with Session(engine) as session:
        if PageAccessTokenService.nullify_token_only(token_id, session):
            return {"message": "Token field set to NULL successfully"}
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found"
        )


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
