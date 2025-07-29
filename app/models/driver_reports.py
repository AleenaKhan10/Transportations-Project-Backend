from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field, Session, select, Relationship
from db import engine
from helpers import logger


class DriverReport(SQLModel, table=True):
    __tablename__ = "driver_reports"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    tripId: Optional[str] = None
    dispatcherName: Optional[str] = None
    driverIdPrimary: Optional[str] = None
    driverIdSecondary: Optional[str] = None
    Calculation: Optional[str] = None
    onTimeStatus: Optional[str] = None
    eta: Optional[str] = None
    pickupTime: Optional[str] = None
    deliveryTime: Optional[str] = None
    milesRemaining: Optional[float] = None
    gpsSpeed: Optional[float] = None
    currentLocation: Optional[str] = None
    destinationCity: Optional[str] = None
    destinationState: Optional[str] = None
    etaNotes: Optional[str] = None
    loadingCity: Optional[str] = None
    loadingState: Optional[str] = None
    arrivedLoading: Optional[str] = None
    departedLoading: Optional[str] = None
    arrivedDelivery: Optional[str] = None
    leftDelivery: Optional[str] = None
    deliveryLateAfterTime: Optional[str] = None
    tripStatusText: Optional[int] = None
    subStatus: Optional[int] = None
    driverFeeling: Optional[str] = None
    driverName: Optional[str] = None
    onTime: Optional[str] = None
    driverETAfeedback: Optional[str] = None
    delayReason: Optional[str] = None
    additionalDriverNotes: Optional[str] = None
    slackPosted: Optional[str] = None
    callStatus: Optional[str] = None
    reportDate: Optional[str] = None
    createdAt: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updatedAt: Optional[datetime] = Field(default_factory=datetime.utcnow)

    @classmethod
    def get_session(cls) -> Session:
        """Create a database session"""
        return Session(engine)
    
    @classmethod
    def get_all(cls, limit: int = 1000) -> list["DriverReport"]:
        """Get all driver reports"""
        with cls.get_session() as session:
            try:
                statement = select(cls).limit(limit).order_by(cls.createdAt.desc())
                reports = session.exec(statement).all()
                return list(reports)
            except Exception as err:
                logger.error(f'Database query error: {err}', exc_info=True)
                return []
    
    @classmethod
    def get_by_trip_id(cls, trip_id: str) -> Optional["DriverReport"]:
        """Get report by trip ID"""
        with cls.get_session() as session:
            try:
                statement = select(cls).where(cls.tripId == trip_id)
                return session.exec(statement).first()
            except Exception as err:
                logger.error(f'Database query error: {err}', exc_info=True)
                return None


class DriverMorningReport(SQLModel, table=True):
    __tablename__ = "driver_morning_report"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    tripId: Optional[str] = None
    dispatcherName: Optional[str] = None
    driverIdPrimary: str = Field(index=True, unique=True)
    MPH: Optional[float] = None
    MilesLEFT: Optional[float] = None
    Location2: Optional[str] = None
    currentLocation: Optional[str] = None
    AI_ETA: Optional[datetime] = None
    loadingCity: Optional[str] = None
    loadingState: Optional[str] = None
    destinationCity: Optional[str] = None
    destinationState: Optional[str] = None
    pickupTime: Optional[datetime] = None
    deliveryTime: Optional[datetime] = None
    DeliveryLATEAfterTime: Optional[datetime] = None
    arrivedLoading: Optional[datetime] = None
    departedLoading: Optional[datetime] = None
    Ditat_ETA: Optional[datetime] = None
    ETA_NOTES: Optional[str] = None
    arrivedDelivery: Optional[datetime] = None
    leftDelivery: Optional[datetime] = None
    tripStatusText: Optional[str] = None
    subStatus: Optional[str] = None
    driverFeeling: Optional[str] = None
    driverName: Optional[str] = None
    onTime: Optional[str] = None
    driverETAfeedback: Optional[str] = None
    delayReason: Optional[str] = None
    additionalDriverNotes: Optional[str] = None
    slackPosted: Optional[bool] = None
    callStatus: Optional[str] = None
    reportDate: Optional[datetime] = None
    ETA_Notes_1: Optional[str] = None
    workflowTrigger: Optional[str] = None
    loadGroup: Optional[str] = None
    createdAt: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updatedAt: Optional[datetime] = Field(default_factory=datetime.utcnow)

    @classmethod
    def get_session(cls) -> Session:
        """Create a database session"""
        return Session(engine)
    
    @classmethod
    def get_all(cls, limit: int = 1000) -> list["DriverMorningReport"]:
        """Get all morning reports"""
        with cls.get_session() as session:
            try:
                statement = select(cls).limit(limit).order_by(cls.createdAt.desc())
                reports = session.exec(statement).all()
                return list(reports)
            except Exception as err:
                logger.error(f'Database query error: {err}', exc_info=True)
                return []
    
    @classmethod
    def get_by_driver_id(cls, driver_id: str) -> Optional["DriverMorningReport"]:
        """Get morning report by driver ID"""
        with cls.get_session() as session:
            try:
                statement = select(cls).where(cls.driverIdPrimary == driver_id)
                return session.exec(statement).first()
            except Exception as err:
                logger.error(f'Database query error: {err}', exc_info=True)
                return None