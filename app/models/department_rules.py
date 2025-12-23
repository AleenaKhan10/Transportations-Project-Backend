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
    
    # New Column to handle the Units
    unit: Optional[str] = Field(default=None) # e.g. 'Hours', 'Minutes', 'Miles'

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
        new_value: Union[float, bool, int],
        new_unit: Optional[str] = None  # <--- New Argument
    ) -> Optional["DepartmentRules"]:
        
        with cls.get_session() as session:
            statement = select(cls).where(
                cls.department_key == department_key,
                cls.rule_key == rule_key
            )
            record = session.exec(statement).first()

            if not record:
                return None

            # 1. Update Value (Purana Logic)
            if record.rule_type == 'number':
                record.threshold = float(new_value)
                
                # 2. Update Unit (Only for numbers)
                if new_unit is not None:
                    record.unit = new_unit  # <--- Save Unit (Hours/Minutes)
                    
            elif record.rule_type == 'boolean':
                record.boolean_value = bool(new_value)
                record.unit = None # Boolean ka unit null kardo safety k liye

            record.updated_at = datetime.utcnow()
            session.add(record)
            session.commit()
            session.refresh(record)
            
            return record