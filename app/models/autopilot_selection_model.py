from typing import Optional, List, Dict, Any
from sqlmodel import Field, SQLModel, Session, select, col
from sqlalchemy import update, case # New Imports
from db import engine  
import logging
from fastapi import HTTPException
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

class AutopilotSelection(SQLModel, table=True):
   
    __tablename__ = "autopilot_selection"
    __table_args__ = {"schema": "dev"} 

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    driverid: str = Field(nullable=False, index=True) 
    drivername: str = Field(nullable=False)
    dispatch_selection: bool = Field(default=False)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # ---------------------------------------------------------------------
    # DB Session Helper
    # ---------------------------------------------------------------------
    @classmethod
    def get_session(cls) -> Session:
        return Session(engine)

    # ---------------------------------------------------------------------
    # GET ALL RECORDS
    # ---------------------------------------------------------------------
    @classmethod
    def get_all_drivers(cls) -> List["AutopilotSelection"]:
        """
        Fetch all drivers to show current selection status on frontend
        """
        with cls.get_session() as session:
            # Simple Select query
            statement = select(cls).order_by(cls.drivername)
            results = session.exec(statement).all()
            return results

    @classmethod
    def sync_drivers_status(cls, active_driver_ids: List[str]) -> Dict:
        """
        Input: ['DRV-1', 'DRV-2']
        Logic: 
        UPDATE autopilot_selection
        SET dispatch_selection = CASE 
            WHEN driverid IN ('DRV-1', 'DRV-2') THEN TRUE 
            ELSE FALSE 
        END,
        updated_at = NOW();
        """
        try:
            with cls.get_session() as session:
                
                status_case = case(
                    (col(cls.driverid).in_(active_driver_ids), True),
                    else_=False
                )

                
                statement = (
                    update(cls)
                    .values(
                        dispatch_selection=status_case,
                        updated_at=datetime.utcnow()
                    )
                )

                # 3. Execute
                result = session.exec(statement)
                session.commit()

                
                total_rows_affected = result.rowcount

                return {
                    "message": "Driver selection synchronized successfully",
                    "active_drivers_count": len(active_driver_ids),
                    "total_rows_processed": total_rows_affected
                }

        except Exception as e:
            logger.error(f"Error in sync_drivers_status: {e}")
            raise e