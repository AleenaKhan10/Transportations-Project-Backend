from typing import List, Optional, Dict, Any

from sqlmodel import SQLModel, Field, Session, select, text

from db import engine
from helpers import logger


class Driver(SQLModel, table=True):
    __tablename__ = "drivers"
    
    driverId: str = Field(primary_key=True)
    driver_data: Optional[str] = None
    driverCallingInfor: Optional[str] = None
    
    @classmethod
    def get_session(cls) -> Session:
        """Create a database session"""
        return Session(engine)
    
    @classmethod
    def get_all(cls, limit: int = 5000) -> List["Driver"]:
        """Get all drivers from the database"""
        logger.info('GetAllDriversData request reach out to correct service')
        
        with cls.get_session() as session:
            try:
                statement = select(cls).limit(limit)
                drivers = session.exec(statement).all()
                return list(drivers)
                
            except Exception as err:
                logger.error(f'Database query error: {err}', exc_info=True)
                return []
    
    @classmethod
    def get_all_raw(cls, limit: int = 5000) -> List[Dict[str, Any]]:
        """Get all drivers data as raw dictionary format"""
        logger.info('GetAllDriversData raw request reach out to correct service')
        
        with cls.get_session() as session:
            try:
                result = session.exec(text(
                    f"SELECT * FROM dev.drivers LIMIT {limit};"
                ))
                
                columns = result.keys()
                data = [dict(zip(columns, row)) for row in result.fetchall()]
                return data
                
            except Exception as err:
                logger.error(f'Database query error: {err}', exc_info=True)
                return []
    
    @classmethod
    def get_by_id(cls, driver_id: str) -> Optional["Driver"]:
        """Get a driver by ID"""
        with cls.get_session() as session:
            try:
                statement = select(cls).where(cls.driverId == driver_id)
                return session.exec(statement).first()
                
            except Exception as err:
                logger.error(f'Database query error: {err}', exc_info=True)
                return None
    
    @classmethod
    def bulk_update_calling_info(cls, updates: List["DriverCallUpdate"]) -> None:
        """Bulk update driver calling information"""
        logger.info('setDriverCalling request reach out to correct service')
        
        with cls.get_session() as session:
            try:
                for driver_update in updates:
                    session.exec(
                        text("""
                            INSERT INTO drivers (driverId, driverCallingInfor)
                            VALUES (:driverId, :driverCallingInfor)
                            ON DUPLICATE KEY UPDATE
                                driverCallingInfor = VALUES(driverCallingInfor);
                        """),
                        {
                            "driverId": driver_update.driverId,
                            "driverCallingInfor": driver_update.driverCallingInfor
                        }
                    )
                
                session.commit()
                
            except Exception as err:
                logger.error(f'Database query error: {err}', exc_info=True)
                session.rollback()
                raise
    
    def update_calling_info(self, calling_info: str) -> bool:
        """Update this driver's calling information"""
        logger.info(f'Updating driver {self.driverId} calling information')
        
        with self.get_session() as session:
            try:
                # Attach this instance to the session
                session.add(self)
                self.driverCallingInfor = calling_info
                session.commit()
                session.refresh(self)
                return True
                
            except Exception as err:
                logger.error(f'Database query error: {err}', exc_info=True)
                session.rollback()
                return False
    
    def save(self) -> bool:
        """Save or update this driver in the database"""
        with self.get_session() as session:
            try:
                session.add(self)
                session.commit()
                session.refresh(self)
                return True
                
            except Exception as err:
                logger.error(f'Database query error: {err}', exc_info=True)
                session.rollback()
                return False
    
    def delete(self) -> bool:
        """Delete this driver from the database"""
        with self.get_session() as session:
            try:
                session.delete(self)
                session.commit()
                return True
                
            except Exception as err:
                logger.error(f'Database query error: {err}', exc_info=True)
                session.rollback()
                return False
    
    @staticmethod
    def null_if_empty(value: Optional[str]) -> Optional[str]:
        """Return None if value is empty or falsy"""
        return value if value else None
    
    @staticmethod
    def parse_driver_data(driver_data: str) -> List[str]:
        """Parse driver_data string into a list"""
        return (driver_data
                .replace("/", "")
                .replace('"', "")
                .replace("\\", "")
                .replace("[", "")
                .replace("]", "")
                .split(","))
    
    @staticmethod
    def parse_calling_info(calling_info: str) -> List[str]:
        """Parse driverCallingInfor string into a list"""
        return (calling_info
                .replace(",", "")
                .replace('"', "")
                .split(","))
    
    def to_structured_response(self) -> "DriverResponse":
        """Convert this driver to a structured response format"""
        # Parse driver basic data
        basic_data = self.parse_driver_data(self.driver_data or "")
        
        # Parse driver calling information
        call_data = self.parse_calling_info(self.driverCallingInfor or "")
        
        # Create structured response with bounds checking
        return DriverResponse(
            driverId=self.null_if_empty(basic_data[0] if len(basic_data) > 0 else None),
            status=self.null_if_empty(basic_data[1] if len(basic_data) > 1 else None),
            firstName=self.null_if_empty(basic_data[2] if len(basic_data) > 2 else None),
            lastName=self.null_if_empty(basic_data[3] if len(basic_data) > 3 else None),
            truckId=self.null_if_empty(basic_data[4] if len(basic_data) > 4 else None),
            phoneNumber=self.null_if_empty(basic_data[5] if len(basic_data) > 5 else None),
            email=self.null_if_empty(basic_data[6] if len(basic_data) > 6 else None),
            hireOn=self.null_if_empty(basic_data[7] if len(basic_data) > 7 else None),
            updataOn=self.null_if_empty(basic_data[8] if len(basic_data) > 8 else None),
            company=self.null_if_empty(basic_data[9] if len(basic_data) > 9 else None),
            dispatcher=self.null_if_empty(basic_data[10] if len(basic_data) > 10 else None),
            firstLanguage=self.null_if_empty(call_data[0] if len(call_data) > 0 else None),
            secondLanguage=self.null_if_empty(call_data[1] if len(call_data) > 1 else None),
            globalDnd=self.null_if_empty(call_data[2] if len(call_data) > 2 else None),
            safetyCall=self.null_if_empty(call_data[3] if len(call_data) > 3 else None),
            safetyMessage=self.null_if_empty(call_data[4] if len(call_data) > 4 else None),
            hosSupport=self.null_if_empty(call_data[5] if len(call_data) > 5 else None),
            maintainanceCall=self.null_if_empty(call_data[6] if len(call_data) > 6 else None),
            maintainanceMessage=self.null_if_empty(call_data[7] if len(call_data) > 7 else None),
            dispatchCall=self.null_if_empty(call_data[8] if len(call_data) > 8 else None),
            dispatchMessage=self.null_if_empty(call_data[9] if len(call_data) > 9 else None),
            accountCall=self.null_if_empty(call_data[10] if len(call_data) > 10 else None),
            accountMessage=self.null_if_empty(call_data[11] if len(call_data) > 11 else None),
        )
    
    @classmethod
    def get_all_structured(cls, limit: int = 5000) -> List["DriverResponse"]:
        """Get all drivers as structured response format"""
        logger.info('GetAllDriversDataJson request reach out to correct service')
        
        drivers = cls.get_all(limit)
        return [driver.to_structured_response() for driver in drivers]


class DriverResponse(SQLModel):
    """Response model for cleaned driver data"""
    driverId: Optional[str] = None
    status: Optional[str] = None
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    truckId: Optional[str] = None
    phoneNumber: Optional[str] = None
    email: Optional[str] = None
    hireOn: Optional[str] = None
    updataOn: Optional[str] = None
    company: Optional[str] = None
    dispatcher: Optional[str] = None
    firstLanguage: Optional[str] = None
    secondLanguage: Optional[str] = None
    globalDnd: Optional[str] = None
    safetyCall: Optional[str] = None
    safetyMessage: Optional[str] = None
    hosSupport: Optional[str] = None
    maintainanceCall: Optional[str] = None
    maintainanceMessage: Optional[str] = None
    dispatchCall: Optional[str] = None
    dispatchMessage: Optional[str] = None
    accountCall: Optional[str] = None
    accountMessage: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return self.model_dump()
    
    @classmethod
    def from_driver(cls, driver: Driver) -> "DriverResponse":
        """Create DriverResponse from Driver instance"""
        return driver.to_structured_response()


class DriverCallUpdate(SQLModel):
    """Model for driver call updates"""
    driverId: str
    driverCallingInfor: str
    
    def apply_to_driver(self, driver: Driver) -> Driver:
        """Apply this update to a driver instance"""
        driver.driverCallingInfor = self.driverCallingInfor
        return driver

    @classmethod
    def create_batch(
        cls, updates: List[Dict[str, str] | "DriverCallUpdate"]
    ) -> List["DriverCallUpdate"]:
        """Create a batch of DriverCallUpdate instances"""
        return [
            cls(**update) if isinstance(update, dict) else update
            for update in updates
            if isinstance(update, (dict, cls))
        ]
