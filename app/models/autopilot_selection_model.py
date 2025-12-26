from typing import Optional, List, Dict, Any
from sqlmodel import Field, SQLModel, Session, select, col
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

    @classmethod
    def get_session(cls) -> Session:
        return Session(engine)

    # ---------------------------------------------------------------------
    # GET ALL RECORDS
    # ---------------------------------------------------------------------
    @classmethod
    def get_all_drivers(cls) -> List["AutopilotSelection"]:
        with cls.get_session() as session:
            statement = select(cls).order_by(cls.drivername)
            results = session.exec(statement).all()
            return results

    # ---------------------------------------------------------------------
    # SELECTIVE BULK UPDATE 
    # ---------------------------------------------------------------------
    @classmethod
    def bulk_update_drivers_status(cls, updates_payload: List[Dict[str, Any]]) -> Dict:
        """
        Input: [{'driverid': 'A', 'dispatch_selection': False}, ...]
        Logic: 
        1. List se IDs nikalo.
        2. DB se sirf un IDs ka data mangwao.
        3. Match karke update karo.
        4. Save karo. (Baqi kisi ko touch nahi karega)
        """
        
        # Step 1: Make Payload Fastlookup Dictioanry (Optimization)
        # Map: {'TEST_001': False, '584AARON': True}
        updates_map = {item['driverid']: item['dispatch_selection'] for item in updates_payload}
        
        # Sirf in IDs ko fetch karna hai
        target_ids = list(updates_map.keys())

        updated_count = 0
        
        try:
            with cls.get_session() as session:
                # Step 2: Fetch only Target Drivers (Engineering Efficiency)
                # Query: SELECT * FROM table WHERE driverid IN ('TEST_001', '584AARON')
                statement = select(cls).where(col(cls.driverid).in_(target_ids))
                existing_records = session.exec(statement).all()

                # Step 3: Loop through Memory (Not DB)
                for record in existing_records:
                    # Check if status is actually changing (Avoid useless updates)
                    new_status = updates_map[record.driverid]
                    
                    if record.dispatch_selection != new_status:
                        record.dispatch_selection = new_status
                        record.updated_at = datetime.utcnow()
                        session.add(record) # Mark dirty
                        updated_count += 1
                    else:
                        # Even if value didn't change, we count it as "processed/checked"
                        # But technically "updated" means changed in DB.
                        # Senior asked for 'updated_count', let's count matching rows.
                        updated_count += 1 

                # Step 4: Atomic Commit (Ek baar save hoga)
                session.commit()
                
                return {
                    "message": "Bulk update processed successfully",
                    "requested_count": len(target_ids),
                    "updated_count": updated_count,
                    "ignored_count": len(target_ids) - len(existing_records) # Jo IDs DB mein nahi milin
                }

        except Exception as e:
            logger.error(f"Error in bulk_update_drivers_status: {e}")
            raise e