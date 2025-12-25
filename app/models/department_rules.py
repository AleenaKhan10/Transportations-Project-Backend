from typing import Optional, List, Dict, Any, Union
from sqlmodel import Field, SQLModel, Session, select
from db import engine
import logging
from fastapi import HTTPException
import uuid
from datetime import datetime

# --- IMPORTING POSTGRES JSONB SUPPORT ---
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB 

logger = logging.getLogger(__name__)

class DepartmentRules(SQLModel, table=True):
    __tablename__ = "department_rules"
    __table_args__ = {"extend_existing": True, "schema": "dev"}

    # Primary Key
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)

    # Department Identification
    department_key: str = Field(index=True)

    # Rule Identification
    rule_key: Optional[str] = Field(index=True)
    rule_name: str

    # Rule Type (Metadata for Frontend)
    rule_type: Optional[str] = None 

    # --- JSONB CONFIGURATION ---
    # sa_column=Column(JSONB) handles both Dict and List automatically
    # Type is 'Any' to accept both Arrays [] and Objects {}
    configuration: Optional[Any] = Field(default=None, sa_column=Column(JSONB))

    # Control
    enabled: bool = Field(default=True)
    description: Optional[str] = None

    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

    # ---------------------------------------------------------------------
    # DB Session
    # ---------------------------------------------------------------------
    @classmethod
    def get_session(cls) -> Session:
        return Session(engine)

    # ---------------------------------------------------------------------
    # GET ALL RECORDS
    # ---------------------------------------------------------------------
    @classmethod
    def get_all_rules(cls) -> List["DepartmentRules"]:
        try:
            with cls.get_session() as session:
                statement = select(cls)
                results = session.exec(statement).all()
                return results
        except Exception as e:
            logger.error(f"Error fetching department rules: {e}")
            raise e

    # ---------------------------------------------------------------------
    # UPDATE CONFIGURATION (Single Rule)
    # ---------------------------------------------------------------------
    @classmethod
    def update_rule_config(
        cls, 
        department_key: str, 
        rule_key: str, 
        new_config: Union[List[Dict[str, Any]], Dict[str, Any]]
    ) -> Optional["DepartmentRules"]:
        """
        Updates ONLY the JSON configuration.
        """
        with cls.get_session() as session:
            statement = select(cls).where(
                cls.department_key == department_key,
                cls.rule_key == rule_key
            )
            record = session.exec(statement).first()

            if not record:
                return None

            record.configuration = new_config
            record.updated_at = datetime.utcnow()
            
            session.add(record)
            session.commit()
            session.refresh(record)
            return record

    # ---------------------------------------------------------------------
    # BULK UPDATE HELPER (Config + Enabled)
    # ---------------------------------------------------------------------
    @classmethod
    def update_rule_generic(
        cls, 
        department_key: str, 
        rule_key: str, 
        new_config: List[Dict[str, Any]],
        is_enabled: bool
    ) -> bool:
        """
        Updates Configuration AND Enabled status based on keys.
        Used by the Bulk PUT API.
        """
        with cls.get_session() as session:
            statement = select(cls).where(
                cls.department_key == department_key,
                cls.rule_key == rule_key
            )
            record = session.exec(statement).first()

            if not record:
                return False

            # Update both fields
            record.configuration = new_config
            record.enabled = is_enabled
            record.updated_at = datetime.utcnow()
            
            session.add(record)
            session.commit()
            return True

    # ---------------------------------------------------------------------
    # CHECK DEPARTMENT STATUS (Any True = True)
    # ---------------------------------------------------------------------
    @classmethod
    def is_department_enabled(cls, department_key: str) -> bool:
        """
        Returns True if AT LEAST ONE rule in the department is enabled.
        """
        with cls.get_session() as session:
            statement = select(cls).where(
                cls.department_key == department_key,
                cls.enabled == True
            )
            result = session.exec(statement).first()
            return True if result else False