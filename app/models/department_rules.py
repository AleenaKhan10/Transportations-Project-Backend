from typing import Optional, List, Dict, Any
from sqlmodel import Field, SQLModel, Session, select
from db import engine
import logging
from fastapi import HTTPException
import uuid
from datetime import datetime

# --- IMPORTING POSTGRES JSONB SUPPORT ---
# SQLModel needs these SQLAlchemy imports to handle JSON columns
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB 

logger = logging.getLogger(__name__)

class DepartmentRules(SQLModel, table=True):
    __tablename__ = "department_rules"
    __table_args__ = {"extend_existing": True, "schema": "dev"} # Added schema 'dev' as per your SQL

    # Primary Key
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)

    # Department Identification
    department_key: str = Field(index=True)

    # Rule Identification
    rule_key: Optional[str] = Field(index=True)
    rule_name: str

    # Rule Type (Metadata)
    # We keep this so Frontend knows if it's a Checkbox or Number input
    rule_type: Optional[str] = None 

    # --- THE NEW HERO: JSONB CONFIGURATION ---
    # Instead of separate columns (threshold, unit, boolean_value), 
    # we store everything here.
    # sa_column=Column(JSONB) tells Postgres to use its special JSONB type.
    configuration: Optional[Dict[str, Any]] = Field(default={}, sa_column=Column(JSONB))

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
        """
        Fetches all rules. The 'configuration' column will automatically 
        be converted to a Python Dictionary by SQLModel.
        """
        try:
            with cls.get_session() as session:
                statement = select(cls)
                results = session.exec(statement).all()
                return results
        except Exception as e:
            logger.error(f"Error fetching department rules: {e}")
            raise e

    # ---------------------------------------------------------------------
    # UPDATE CONFIGURATION (New Logic)
    # ---------------------------------------------------------------------
    @classmethod
    def update_rule_config(
        cls, 
        department_key: str, 
        rule_key: str, 
        new_config: Dict[str, Any] # Accepting a full Dictionary now
    ) -> Optional["DepartmentRules"]:
        """
        Updates the JSON configuration directly.
        We no longer check for 'number' or 'boolean' types here.
        We simply overwrite the old JSON with the new JSON.
        """
        with cls.get_session() as session:
            # 1. Find the record
            statement = select(cls).where(
                cls.department_key == department_key,
                cls.rule_key == rule_key
            )
            record = session.exec(statement).first()

            if not record:
                return None

            # 2. Update the Configuration (JSONB)
            # This handles Value, Unit, Speed, Fuel, everything at once.
            record.configuration = new_config
            
            # 3. Save
            record.updated_at = datetime.utcnow()
            session.add(record)
            session.commit()
            session.refresh(record)
            
            return record
        
# ---------------------------------------------------------------------
    # CHECK DEPARTMENT STATUS (Any True = True)
    # ---------------------------------------------------------------------
    @classmethod
    def is_department_enabled(cls, department_key: str) -> bool:
        """
        Returns True if AT LEAST ONE rule in the department is enabled.
        Returns False only if ALL rules are disabled or no rules exist.
        """
        with cls.get_session() as session:
            # Logic: We need to find only one record that is enabled
            statement = select(cls).where(
                cls.department_key == department_key,
                cls.enabled == True
            )
            
            result = session.exec(statement).first()
            
            return True if result else False