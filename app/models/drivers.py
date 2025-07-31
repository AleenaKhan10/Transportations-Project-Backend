from typing import List, Optional

from sqlmodel import SQLModel, Field, Session, select, text
from pydantic import BaseModel

from db import engine
from helpers import logger


class Driver(SQLModel, table=True):
    __tablename__ = "driversDirectory"
    
    driverId: str = Field(primary_key=True)
    status: Optional[str] = None
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    truckId: Optional[str] = None
    phoneNumber: Optional[str] = None
    email: Optional[str] = None
    hiredOn: Optional[str] = None
    updatedOn: Optional[str] = None
    companyId: Optional[str] = None
    dispatcher: Optional[str] = None
    firstLanguage: Optional[str] = None
    secondLanguage: Optional[str] = None
    globalDnd: Optional[bool] = None
    safetyCall: Optional[bool] = None
    safetyMessage: Optional[bool] = None
    hosSupport: Optional[bool] = None
    maintainanceCall: Optional[bool] = None
    maintainanceMessage: Optional[bool] = None
    dispatchCall: Optional[bool] = None
    dispatchMessage: Optional[bool] = None
    accountCall: Optional[bool] = None
    accountMessage: Optional[bool] = None
    telegramId: Optional[str] = None

    
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
    
    # @classmethod
    # def get_all_raw(cls, limit: int = 5000) -> List[Dict[str, Any]]:
    #     """Get all drivers data as raw dictionary format"""
    #     logger.info('GetAllDriversData raw request reach out to correct service')
        
    #     with cls.get_session() as session:
    #         try:
    #             result = session.exec(text(
    #                 f"SELECT * FROM dev.drivers LIMIT {limit};"
    #             ))
                
    #             columns = result.keys()
    #             data = [dict(zip(columns, row)) for row in result.fetchall()]
    #             return data
                
    #         except Exception as err:
    #             logger.error(f'Database query error: {err}', exc_info=True)
    #             return []
    
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
    def get_by_ids(cls, driver_ids: List[str]) -> List["Driver"]:
        """Get multiple drivers by their IDs in a single query"""
        with cls.get_session() as session:
            try:
                statement = select(cls).where(cls.driverId.in_(driver_ids))
                return list(session.exec(statement).all())
                
            except Exception as err:
                logger.error(f'Database query error: {err}', exc_info=True)
                return []
    
    @classmethod
    def bulk_update_calling_info(cls, updates: List["DriverCallUpdate"]) -> None:
        """Bulk update driver calling information"""
        logger.info('setDriverCalling request reach out to correct service')
        
        with cls.get_session() as session:
            try:
                for driver_update in updates:
                    session.execute(
                        text("""
                            INSERT INTO driversDirectory (
                                driverId, updatedOn, safetyMessage, status, companyId, hosSupport,
                                firstName, dispatcher, maintainanceCall, lastName, firstLanguage,
                                maintainanceMessage, truckId, secondLanguage, dispatchCall, phoneNumber,
                                globalDnd, dispatchMessage, email, safetyCall, accountCall, hiredOn, accountMessage, telegramId
                            )
                            VALUES (
                                :driverId, :updatedOn, :safetyMessage, :status, :companyId, :hosSupport,
                                :firstName, :dispatcher, :maintainanceCall, :lastName, :firstLanguage,
                                :maintainanceMessage, :truckId, :secondLanguage, :dispatchCall, :phoneNumber,
                                :globalDnd, :dispatchMessage, :email, :safetyCall, :accountCall, :hiredOn, :accountMessage, :telegramId
                            )
                            ON DUPLICATE KEY UPDATE
                                updatedOn = VALUES(updatedOn),
                                safetyMessage = VALUES(safetyMessage),
                                status = VALUES(status),
                                companyId = VALUES(companyId),
                                hosSupport = VALUES(hosSupport),
                                firstName = VALUES(firstName),
                                dispatcher = VALUES(dispatcher),
                                maintainanceCall = VALUES(maintainanceCall),
                                lastName = VALUES(lastName),
                                firstLanguage = VALUES(firstLanguage),
                                maintainanceMessage = VALUES(maintainanceMessage),
                                truckId = VALUES(truckId),
                                secondLanguage = VALUES(secondLanguage),
                                dispatchCall = VALUES(dispatchCall),
                                phoneNumber = VALUES(phoneNumber),
                                globalDnd = VALUES(globalDnd),
                                dispatchMessage = VALUES(dispatchMessage),
                                email = VALUES(email),
                                safetyCall = VALUES(safetyCall),
                                accountCall = VALUES(accountCall),
                                hiredOn = VALUES(hiredOn),
                                accountMessage = VALUES(accountMessage),
                                telegramId = VALUES(telegramId)
                            """),
                        {
                            "driverId": driver_update.driverId,
                            "updatedOn": driver_update.updatedOn,
                            "safetyMessage": driver_update.safetyMessage,
                            "status": driver_update.status,
                            "companyId": driver_update.companyId,
                            "hosSupport": driver_update.hosSupport,
                            "firstName": driver_update.firstName,
                            "dispatcher": driver_update.dispatcher,
                            "maintainanceCall": driver_update.maintainanceCall,
                            "lastName": driver_update.lastName,
                            "firstLanguage": driver_update.firstLanguage,
                            "maintainanceMessage": driver_update.maintainanceMessage,
                            "truckId": driver_update.truckId,
                            "secondLanguage": driver_update.secondLanguage,
                            "dispatchCall": driver_update.dispatchCall,
                            "phoneNumber": driver_update.phoneNumber,
                            "globalDnd": driver_update.globalDnd,
                            "dispatchMessage": driver_update.dispatchMessage,
                            "email": driver_update.email,
                            "safetyCall": driver_update.safetyCall,
                            "accountCall": driver_update.accountCall,
                            "hiredOn": driver_update.hiredOn,
                            "accountMessage": driver_update.accountMessage,
                            "telegramId": driver_update.telegramId
                        }
                    )
                
                session.commit()
                
            except Exception as err:
                logger.error(f'Database query error: {err}', exc_info=True)
                session.rollback()
                raise
    
    # def update_calling_info(self, calling_info: str) -> bool:
    #     """Update this driver's calling information"""
    #     logger.info(f'Updating driver {self.driverId} calling information')
        
    #     with self.get_session() as session:
    #         try:
    #             # Attach this instance to the session
    #             session.add(self)
    #             self.driverCallingInfor = calling_info
    #             session.commit()
    #             session.refresh(self)
    #             return True
                
    #         except Exception as err:
    #             logger.error(f'Database query error: {err}', exc_info=True)
    #             session.rollback()
    #             return False
    
    # def save(self) -> bool:
    #     """Save or update this driver in the database"""
    #     with self.get_session() as session:
    #         try:
    #             session.add(self)
    #             session.commit()
    #             session.refresh(self)
    #             return True
                
    #         except Exception as err:
    #             logger.error(f'Database query error: {err}', exc_info=True)
    #             session.rollback()
    #             return False
    
    # def delete(self) -> bool:
    #     """Delete this driver from the database"""
    #     with self.get_session() as session:
    #         try:
    #             session.delete(self)
    #             session.commit()
    #             return True
                
    #         except Exception as err:
    #             logger.error(f'Database query error: {err}', exc_info=True)
    #             session.rollback()
    #             return False
    
    # def to_structured_response(self) -> "DriverResponse":
    #     """Convert this driver to a structured response format"""    
    #     # Create structured response with bounds checking
    #     return DriverResponse(
    #         driverId=self.driverId,
    #         status=self.status,
    #         firstName=self.firstName,
    #         lastName=self.lastName,
    #         truckId=self.truckId,
    #         phoneNumber=self.phoneNumber,
    #         email=self.email,
    #         hiredOn=self.hiredOn,
    #         updatedOn=self.updatedOn,
    #         companyId=self.companyId,
    #         dispatcher=self.dispatcher,
    #         firstLanguage=self.firstLanguage,
    #         secondLanguage=self.secondLanguage,
    #         globalDnd=self.globalDnd,
    #         safetyCall=self.safetyCall,
    #         safetyMessage=self.safetyMessage,
    #         hosSupport=self.hosSupport,
    #         maintainanceCall=self.maintainanceCall,
    #         maintainanceMessage=self.maintainanceMessage,
    #         dispatchCall=self.dispatchCall,
    #         dispatchMessage=self.dispatchMessage,
    #         accountCall=self.accountCall,
    #         accountMessage=self.accountMessage,
    #     )
    
    # @classmethod
    # def get_all_structured(cls, limit: int = 5000) -> List["DriverResponse"]:
    #     """Get all drivers as structured response format"""
    #     logger.info('GetAllDriversDataJson request reach out to correct service')
        
    #     drivers = cls.get_all(limit)
    #     return [driver.to_structured_response() for driver in drivers]


class DriverResponse(SQLModel):
    """Response model for cleaned driver data"""
    driverId: Optional[str] = None
    status: Optional[str] = None
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    truckId: Optional[str] = None
    phoneNumber: Optional[str] = None
    email: Optional[str] = None
    hiredOn: Optional[str] = None
    updatedOn: Optional[str] = None
    companyId: Optional[str] = None
    dispatcher: Optional[str] = None
    firstLanguage: Optional[str] = None
    secondLanguage: Optional[str] = None
    globalDnd: Optional[bool] = None
    safetyCall: Optional[bool] = None
    safetyMessage: Optional[bool] = None
    hosSupport: Optional[bool] = None
    maintainanceCall: Optional[bool] = None
    maintainanceMessage: Optional[bool] = None
    dispatchCall: Optional[bool] = None
    dispatchMessage: Optional[bool] = None
    accountCall: Optional[bool] = None
    accountMessage: Optional[bool] = None
    telegramId: Optional[str] = None
    
    # def to_dict(self) -> Dict[str, Any]:
    #     """Convert to dictionary"""
    #     return self.model_dump()
    
    # @classmethod
    # def from_driver(cls, driver: Driver) -> "DriverResponse":
    #     """Create DriverResponse from Driver instance"""
    #     return driver.to_structured_response()


class DriverCallUpdate(SQLModel):
    """Model for driver call updates"""
    driverId: Optional[str] = None
    status: Optional[str] = None
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    truckId: Optional[str] = None
    phoneNumber: Optional[str] = None
    email: Optional[str] = None
    hiredOn: Optional[str] = None
    updatedOn: Optional[str] = None
    companyId: Optional[str] = None
    dispatcher: Optional[str] = None
    firstLanguage: Optional[str] = None
    secondLanguage: Optional[str] = None
    globalDnd: Optional[bool] = None
    safetyCall: Optional[bool] = None
    safetyMessage: Optional[bool] = None
    hosSupport: Optional[bool] = None
    maintainanceCall: Optional[bool] = None
    maintainanceMessage: Optional[bool] = None
    dispatchCall: Optional[bool] = None
    dispatchMessage: Optional[bool] = None
    accountCall: Optional[bool] = None
    accountMessage: Optional[bool] = None
    telegramId: Optional[str] = None

    
    # def apply_to_driver(self, driver: Driver) -> Driver:
    #     """Apply this update to a driver instance"""
    #     driver.driverCallingInfor = self.driverCallingInfor
    #     return driver

#     @classmethod
#     def create_batch(
#         cls, updates: List[Dict[str, str] | "DriverCallUpdate"]
#     ) -> List["DriverCallUpdate"]:
#         """Create a batch of DriverCallUpdate instances"""
#         return [
#             cls(**update) if isinstance(update, dict) else update
#             for update in updates
#             if isinstance(update, (dict, cls))
#         ]


class CreateDriverRequest(BaseModel):
    firstName: str
    lastName: str
    phoneNumber: str
    status: str = "Active"
    truckId: str = None
    email: str = None
    hiredOn: str = None
    companyId: str = "COMP_001"
    dispatcher: str = None
    firstLanguage: str = "English"
    secondLanguage: str = None
    globalDnd: bool = False
    safetyCall: bool = True
    safetyMessage: bool = True
    hosSupport: bool = True
    maintainanceCall: bool = True
    maintainanceMessage: bool = True
    dispatchCall: bool = True
    dispatchMessage: bool = True
    accountCall: bool = True
    accountMessage: bool = True
    telegramId: str = None
