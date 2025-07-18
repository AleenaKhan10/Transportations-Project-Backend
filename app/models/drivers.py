from typing import List, Optional, Dict, Any

from sqlmodel import SQLModel, Field, Session, select, text

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
    
    @classmethod
    def get_session(cls) -> Session:
        """Create a database session"""
        return Session(engine)
    
    @classmethod
    def get_all(cls, limit: int = 5000) -> List["Driver"]:
        """Get all drivers from the database"""
        # TODO: Need to add an offset logic as well.
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
                    session.execute(
                        text("""
                            INSERT INTO driversDirectory (
                                driverId, updatedOn, safetyMessage, status, companyId, hosSupport,
                                firstName, dispatcher, maintainanceCall, lastName, firstLanguage,
                                maintainanceMessage, truckId, secondLanguage, dispatchCall, phoneNumber,
                                globalDnd, dispatchMessage, email, safetyCall, accountCall, hiredOn, accountMessage
                            )
                            VALUES (
                                :driverId, :updatedOn, :safetyMessage, :status, :companyId, :hosSupport,
                                :firstName, :dispatcher, :maintainanceCall, :lastName, :firstLanguage,
                                :maintainanceMessage, :truckId, :secondLanguage, :dispatchCall, :phoneNumber,
                                :globalDnd, :dispatchMessage, :email, :safetyCall, :accountCall, :hiredOn, :accountMessage
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
                                accountMessage = VALUES(accountMessage);
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
                        }
                    )
                
                session.commit()
                
            except Exception as err:
                logger.error(f'Database query error: {err}', exc_info=True)
                session.rollback()
                raise


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
