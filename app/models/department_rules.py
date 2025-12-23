from typing import Optional, List, Dict, Union
from sqlmodel import Field, SQLModel, Session, select
from db import engine  # Assuming you have this configuration
import logging
from fastapi import HTTPException
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

class DepartmentRules(SQLModel, table=True):
    __tablename__ = "department_rules"
    __table_args__ = {"extend_existing": True}

    # Primary Key
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)

    # Department Identification
    department_key: str = Field(index=True)  # e.g., 'dispatch_reports'

    # Rule Identification
    rule_key: str = Field(index=True)       # e.g., 'low_fuel' (System usage)
    rule_name: str                          # e.g., 'Low Fuel Alert' (Display usage)

    # Rule Definition
    rule_type: str                          # 'number' or 'boolean'
    
    # Values (Only one will be used based on rule_type)
    threshold: Optional[float] = None       # Used if rule_type is 'number'
    boolean_value: Optional[bool] = None    # Used if rule_type is 'boolean'

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
    # GET ALL RECORDS (Raw Flat Data)
    # ---------------------------------------------------------------------
    @classmethod
    def get_all_rules(cls) -> List["DepartmentRules"]:
        """
        Fetches all rules from the database as flat rows.
        The Service layer will handle the grouping/transformation.
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
    # UPDATE SINGLE RULE
    # ---------------------------------------------------------------------
    @classmethod
    def update_rule_value(
        cls, 
        department_key: str, 
        rule_key: str, 
        new_value: Union[float, bool, int]
    ) -> Optional["DepartmentRules"]:
        """
        Updates a specific rule based on dept_key and rule_key.
        Smartly decides whether to update 'threshold' or 'boolean_value'
        based on the rule's type.
        """
        with cls.get_session() as session:
            # 1. Find the specific record
            statement = select(cls).where(
                cls.department_key == department_key,
                cls.rule_key == rule_key
            )
            record = session.exec(statement).first()

            if not record:
                return None

            # Update the correct column based on type
            # We do not want to put a boolean value into the threshold column or vice versa.
            if record.rule_type == 'number':
                # Ensure it's treated as a number
                record.threshold = float(new_value)
            elif record.rule_type == 'boolean':
                # Ensure it's treated as a boolean
                record.boolean_value = bool(new_value)

            record.updated_at = datetime.utcnow()
            
            session.add(record)
            session.commit()
            session.refresh(record)
            
            return record