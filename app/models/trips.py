from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from sqlmodel import SQLModel, Field, Session, select, text
from db import engine
from helpers import logger


class Trip(SQLModel, table=True):
    __tablename__ = "trips"
    
    tripId: str = Field(max_length=50, primary_key=True)
    lastModified: Optional[datetime] = None
    primaryDriverId: Optional[str] = Field(max_length=50, default=None)
    truckId: Optional[str] = Field(max_length=20, default=None)
    fuelPercent: Optional[float] = None
    primaryTrailerId: Optional[str] = Field(max_length=20, default=None)
    trlCheck: Optional[str] = Field(max_length=10, default=None)
    subStatusLabel: Optional[str] = Field(max_length=100, default=None)
    checkCall: Optional[str] = Field(max_length=20, default=None)
    mph: Optional[float] = None
    milesLeft: Optional[float] = None
    outOfRoute: Optional[str] = Field(max_length=10, default=None)
    etaTimeDifference: Optional[str] = Field(max_length=100, default=None)
    aiETA: Optional[datetime] = None
    samsaraLocation: Optional[str] = Field(max_length=500, default=None)
    liveSharingUrl: Optional[str] = None
    customerName: Optional[str] = Field(max_length=500, default=None)
    emptyDrivingDistance: Optional[float] = None
    loadedDrivingDistance: Optional[float] = None
    shipperName: Optional[str] = Field(max_length=500, default=None)
    loadingCity: Optional[str] = Field(max_length=200, default=None)
    destinationName: Optional[str] = Field(max_length=500, default=None)
    destinationCity: Optional[str] = Field(max_length=200, default=None)
    puArrival: Optional[str] = Field(max_length=50, default=None)
    puTime: Optional[datetime] = None
    puTimeLatest: Optional[datetime] = None
    arrivedToPU: Optional[datetime] = None
    leftFromPU: Optional[datetime] = None
    delArrival: Optional[str] = Field(max_length=50, default=None)
    deliveryEarliest: Optional[datetime] = None
    deliveryLatest: Optional[datetime] = None
    arrivedToDelivery: Optional[datetime] = None
    onTimeStatus: Optional[str] = Field(max_length=50, default=None)
    sensorName: Optional[str] = Field(max_length=100, default=None)
    ditatSetPoint: Optional[float] = None
    tempC: Optional[float] = None
    tempF: Optional[float] = None
    reeferModeLabel: Optional[str] = Field(max_length=50, default=None)
    ditatGpsSpeed: Optional[float] = None
    
    @classmethod
    def get_session(cls) -> Session:
        """Create a database session"""
        return Session(engine)
    
    @classmethod
    def get_all(cls, limit: int = 5000) -> List["Trip"]:
        """Get all trips from the database"""
        logger.info('GetAllTrips request reached the service')
        
        with cls.get_session() as session:
            try:
                statement = select(cls).limit(limit)
                trips = session.exec(statement).all()
                return list(trips)
                
            except Exception as err:
                logger.error(f'Database query error: {err}', exc_info=True)
                return []
    
    @classmethod
    def get_by_trip_id(cls, trip_id: str) -> Optional["Trip"]:
        """Get a trip by tripId"""
        with cls.get_session() as session:
            try:
                statement = select(cls).where(cls.tripId == trip_id)
                return session.exec(statement).first()
                
            except Exception as err:
                logger.error(f'Database query error: {err}', exc_info=True)
                return None
    
    @classmethod
    def get_by_driver_id(cls, driver_id: str) -> List["Trip"]:
        """Get all trips by driver ID"""
        with cls.get_session() as session:
            try:
                statement = select(cls).where(cls.primaryDriverId == driver_id)
                trips = session.exec(statement).all()
                return list(trips)
                
            except Exception as err:
                logger.error(f'Database query error: {err}', exc_info=True)
                return []
    
    @classmethod
    def create(cls, **kwargs) -> Optional["Trip"]:
        """Create a new trip"""
        with cls.get_session() as session:
            try:
                trip = cls(**kwargs)
                session.add(trip)
                session.commit()
                session.refresh(trip)
                return trip
                
            except Exception as err:
                logger.error(f'Database insert error: {err}', exc_info=True)
                return None
    
    @classmethod
    def update(cls, trip_id: str, **kwargs) -> Optional["Trip"]:
        """Update an existing trip"""
        with cls.get_session() as session:
            try:
                statement = select(cls).where(cls.tripId == trip_id)
                trip = session.exec(statement).first()
                
                if trip:
                    for key, value in kwargs.items():
                        if hasattr(trip, key):
                            setattr(trip, key, value)
                    
                    session.add(trip)
                    session.commit()
                    session.refresh(trip)
                    return trip
                return None
                
            except Exception as err:
                logger.error(f'Database update error: {err}', exc_info=True)
                return None
    
    @classmethod
    def upsert(cls, trip_id: str, **kwargs) -> Optional["Trip"]:
        """Upsert a trip (insert or update if exists) - only updates provided fields"""
        logger.info(f'Upserting trip for ID: {trip_id}')
        
        with cls.get_session() as session:
            try:
                # Build dynamic SQL based on provided fields
                provided_fields = ["tripId"]
                provided_values = {"tripId": trip_id}
                update_clauses = []
                
                # Add all non-None fields to the upsert
                for key, value in kwargs.items():
                    if value is not None and hasattr(cls, key):
                        provided_fields.append(key)
                        provided_values[key] = value
                        update_clauses.append(f"{key} = VALUES({key})")
                
                # If no fields to update besides tripId, still need to handle upsert
                if not update_clauses:
                    # Just insert if not exists, do nothing on duplicate
                    sql = """
                        INSERT IGNORE INTO trips (tripId)
                        VALUES (:tripId)
                    """
                else:
                    # Build the dynamic SQL with updates
                    fields_str = ", ".join(provided_fields)
                    values_str = ", ".join([f":{field}" for field in provided_fields])
                    update_str = ", ".join(update_clauses)
                    
                    sql = f"""
                        INSERT INTO trips ({fields_str})
                        VALUES ({values_str})
                        ON DUPLICATE KEY UPDATE {update_str}
                    """
                
                session.execute(text(sql), provided_values)
                session.commit()
                
                # Return the updated/inserted trip
                return cls.get_by_trip_id(trip_id)
                
            except Exception as err:
                logger.error(f'Database upsert error: {err}', exc_info=True)
                session.rollback()
                return None

    @classmethod
    def delete(cls, trip_id: str) -> bool:
        """Delete a trip"""
        with cls.get_session() as session:
            try:
                statement = select(cls).where(cls.tripId == trip_id)
                trip = session.exec(statement).first()
                
                if trip:
                    session.delete(trip)
                    session.commit()
                    return True
                return False
                
            except Exception as err:
                logger.error(f'Database delete error: {err}', exc_info=True)
                return False


class TripCreate(SQLModel):
    """Schema for creating a trip"""
    tripId: str = Field(max_length=50)
    lastModified: Optional[datetime] = None
    primaryDriverId: Optional[str] = Field(max_length=50, default=None)
    truckId: Optional[str] = Field(max_length=20, default=None)
    fuelPercent: Optional[float] = None
    primaryTrailerId: Optional[str] = Field(max_length=20, default=None)
    trlCheck: Optional[str] = Field(max_length=10, default=None)
    subStatusLabel: Optional[str] = Field(max_length=100, default=None)
    checkCall: Optional[str] = Field(max_length=20, default=None)
    mph: Optional[float] = None
    milesLeft: Optional[float] = None
    outOfRoute: Optional[str] = Field(max_length=10, default=None)
    etaTimeDifference: Optional[str] = Field(max_length=100, default=None)
    aiETA: Optional[datetime] = None
    samsaraLocation: Optional[str] = Field(max_length=500, default=None)
    liveSharingUrl: Optional[str] = None
    customerName: Optional[str] = Field(max_length=500, default=None)
    emptyDrivingDistance: Optional[float] = None
    loadedDrivingDistance: Optional[float] = None
    shipperName: Optional[str] = Field(max_length=500, default=None)
    loadingCity: Optional[str] = Field(max_length=200, default=None)
    destinationName: Optional[str] = Field(max_length=500, default=None)
    destinationCity: Optional[str] = Field(max_length=200, default=None)
    puArrival: Optional[str] = Field(max_length=50, default=None)
    puTime: Optional[datetime] = None
    puTimeLatest: Optional[datetime] = None
    arrivedToPU: Optional[datetime] = None
    leftFromPU: Optional[datetime] = None
    delArrival: Optional[str] = Field(max_length=50, default=None)
    deliveryEarliest: Optional[datetime] = None
    deliveryLatest: Optional[datetime] = None
    arrivedToDelivery: Optional[datetime] = None
    onTimeStatus: Optional[str] = Field(max_length=50, default=None)
    sensorName: Optional[str] = Field(max_length=100, default=None)
    ditatSetPoint: Optional[float] = None
    tempC: Optional[float] = None
    tempF: Optional[float] = None
    reeferModeLabel: Optional[str] = Field(max_length=50, default=None)
    ditatGpsSpeed: Optional[float] = None


class TripUpdate(SQLModel):
    """Schema for updating a trip"""
    lastModified: Optional[datetime] = None
    primaryDriverId: Optional[str] = Field(max_length=50, default=None)
    truckId: Optional[str] = Field(max_length=20, default=None)
    fuelPercent: Optional[float] = None
    primaryTrailerId: Optional[str] = Field(max_length=20, default=None)
    trlCheck: Optional[str] = Field(max_length=10, default=None)
    subStatusLabel: Optional[str] = Field(max_length=100, default=None)
    checkCall: Optional[str] = Field(max_length=20, default=None)
    mph: Optional[float] = None
    milesLeft: Optional[float] = None
    outOfRoute: Optional[str] = Field(max_length=10, default=None)
    etaTimeDifference: Optional[str] = Field(max_length=100, default=None)
    aiETA: Optional[datetime] = None
    samsaraLocation: Optional[str] = Field(max_length=500, default=None)
    liveSharingUrl: Optional[str] = None
    customerName: Optional[str] = Field(max_length=500, default=None)
    emptyDrivingDistance: Optional[float] = None
    loadedDrivingDistance: Optional[float] = None
    shipperName: Optional[str] = Field(max_length=500, default=None)
    loadingCity: Optional[str] = Field(max_length=200, default=None)
    destinationName: Optional[str] = Field(max_length=500, default=None)
    destinationCity: Optional[str] = Field(max_length=200, default=None)
    puArrival: Optional[str] = Field(max_length=50, default=None)
    puTime: Optional[datetime] = None
    puTimeLatest: Optional[datetime] = None
    arrivedToPU: Optional[datetime] = None
    leftFromPU: Optional[datetime] = None
    delArrival: Optional[str] = Field(max_length=50, default=None)
    deliveryEarliest: Optional[datetime] = None
    deliveryLatest: Optional[datetime] = None
    arrivedToDelivery: Optional[datetime] = None
    onTimeStatus: Optional[str] = Field(max_length=50, default=None)
    sensorName: Optional[str] = Field(max_length=100, default=None)
    ditatSetPoint: Optional[float] = None
    tempC: Optional[float] = None
    tempF: Optional[float] = None
    reeferModeLabel: Optional[str] = Field(max_length=50, default=None)
    ditatGpsSpeed: Optional[float] = None