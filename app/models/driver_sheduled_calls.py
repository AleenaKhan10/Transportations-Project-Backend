from typing import Optional, List, Dict
from sqlmodel import Field, SQLModel, Session, select
from db import engine
import logging
from fastapi import HTTPException
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

class DriverSheduledCalls(SQLModel, table=True):
    __tablename__ = "driver_sheduled_calls_data"
    __table_args__ = {"extend_existing": True}

    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    schedule_group_id: uuid.UUID = Field(index=True)

    # Yeh wo column hai jahan wo lambi string store hogi
    driver: Optional[str] = None 
    reminder: Optional[str] = None
    violation: Optional[str] = None

    call_scheduled_date_time: datetime

    status: bool = True 

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
    def get_all_sheduled_call_records(cls) -> List["DriverSheduledCalls"]:
        with cls.get_session() as session:
            statement = select(cls)
            results = session.exec(statement).all()
            return results

    # ---------------------------------------------------------------------
    # CREATE BULK RECORDS (Updated Logic)
    # ---------------------------------------------------------------------
    @classmethod
    def create_bulk_schedule(cls, payload) -> Dict:
        """
        Now this function will treat 'drivers' list as generic strings.
        """
        # 1. Generate unique Group ID
        group_id = uuid.uuid4()
        
        # 2. Process Reminders/Violations lists to String
        reminders_str = ", ".join(payload.reminders) if payload.reminders else None
        violations_str = ", ".join(payload.violations) if payload.violations else None
        
        new_records = []

        try:
            with cls.get_session() as session:
                # 3. Loop through the array of strings (Selected Checkbox values)
                for driver_input_string in payload.drivers:
                    
                    # Har string (checkbox selection) k liye aik row
                    record = cls(
                        schedule_group_id=group_id,
                        driver=driver_input_string,  # Jo bhi lambi string aayi, wo yahan save hogi
                        reminder=reminders_str,
                        violation=violations_str,
                        call_scheduled_date_time=payload.call_scheduled_date_time,
                        status=False,  # Requirements k mutabik False
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    session.add(record)
                    new_records.append(record)
                
                # 4. Commit (Save)
                session.commit()
                
                return {
                    "message": "Schedule created successfully",
                    "schedule_group_id": str(group_id),
                    "total_records": len(new_records),
                }
                
        except Exception as e:
            logger.error(f"Error in create_bulk_schedule: {e}")
            raise e
    
    # ---------------------------------------------------------------------
    # GET BY ID OR GROUP ID (Smart Search)
    # ---------------------------------------------------------------------
    @classmethod
    def get_by_id_or_group(cls, search_id: uuid.UUID) -> List["DriverSheduledCalls"]:
        """
        Yeh function pehly check karega ke kya yeh ID kisi specific record ki hai?
        Agar nahi, tow check karega ke kya yeh Group ID hai?
        """
        with cls.get_session() as session:
            # 1. Pehly check: Kya yeh Primary Key (Record ID) hai?
            # Hum .all() use kar rhy hain taaky return hamesha List hi ho
            statement_pk = select(cls).where(cls.id == search_id)
            results_pk = session.exec(statement_pk).all()

            if results_pk:
                # Agar record mil gaya tow wapas bhej do
                return results_pk

            # 2. Dusra check: Agar uper nahi mila, tow kya yeh Group ID hai?
            statement_group = select(cls).where(cls.schedule_group_id == search_id)
            results_group = session.exec(statement_group).all()

            return results_group