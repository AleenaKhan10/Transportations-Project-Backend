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
    customerGroup: Optional[str] = Field(max_length=200, default=None)
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
    dispatcher: Optional[str] = Field(max_length=100, default=None)
    dispatcher: Optional[str] = Field(max_length=100, default=None)
    
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
    def get_active_trip_by_driver_id(cls, driver_id: str) -> Optional["Trip"]:
        """
        Get the active trip for a driver by filtering on subStatusLabel.

        Active trip substatus values:
        - 'en route to pickup'
        - 'en route to pick up'
        - 'loading'
        - 'en route to delivery'
        - 'en route to waypoint'
        - 'unloading'

        Excludes 'assigned' status as those are not active trips.
        Returns the first matching trip or None if no active trip found.
        """
        # Define active substatus values (case-insensitive matching)
        active_substatus_values = [
            'en route to pickup',
            'en route to pick up',
            'loading',
            'en route to delivery',
            'en route to waypoint',
            'unloading',
        ]

        with cls.get_session() as session:
            try:
                # Get all trips for the driver
                statement = select(cls).where(cls.primaryDriverId == driver_id)
                trips = session.exec(statement).all()

                # Filter by substatus (case-insensitive)
                for trip in trips:
                    if trip.subStatusLabel:
                        substatus_lower = trip.subStatusLabel.lower().strip()
                        if substatus_lower in active_substatus_values:
                            logger.info(f'Found active trip {trip.tripId} for driver {driver_id} with substatus: {trip.subStatusLabel}')
                            return trip

                logger.info(f'No active trip found for driver {driver_id}')
                return None

            except Exception as err:
                logger.error(f'Database query error getting active trip: {err}', exc_info=True)
                return None
    
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
                        update_clauses.append(f'"{key}" = EXCLUDED."{key}"')
                
                # If no fields to update besides tripId, still need to handle upsert
                if not update_clauses:
                    # Just insert if not exists, do nothing on duplicate
                    sql = """
                        INSERT INTO trips ("tripId")
                        VALUES (:tripId)
                        ON CONFLICT ("tripId") DO NOTHING
                    """
                else:
                    # Build the dynamic SQL with updates - quote column names for PostgreSQL
                    fields_str = ", ".join([f'"{field}"' for field in provided_fields])
                    values_str = ", ".join([f":{field}" for field in provided_fields])
                    update_str = ", ".join(update_clauses)
                    
                    sql = f"""
                        INSERT INTO trips ({fields_str})
                        VALUES ({values_str})
                        ON CONFLICT ("tripId") DO UPDATE SET {update_str}
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

    @classmethod
    def delete_by_field(cls, field_name: str, field_value: str) -> dict:
        """
        Delete trips by matching a specific field name and value.

        Args:
            field_name: The column name to search (e.g., 'tripId', 'primaryDriverId')
            field_value: The value to match

        Returns:
            dict with success status, message, and deleted count
        """
        # Validate field exists on the model
        if not hasattr(cls, field_name):
            return {
                "success": False,
                "message": f"Invalid field name: '{field_name}'. Field does not exist on Trip model.",
                "deleted_count": 0
            }

        with cls.get_session() as session:
            try:
                # Get the column attribute dynamically
                column = getattr(cls, field_name)

                # Find matching records
                statement = select(cls).where(column == field_value)
                trips = session.exec(statement).all()

                if not trips:
                    return {
                        "success": True,
                        "message": f"No trips found with {field_name}='{field_value}'",
                        "deleted_count": 0
                    }

                deleted_count = len(trips)

                # Delete all matching records
                for trip in trips:
                    session.delete(trip)

                session.commit()

                logger.info(f"Deleted {deleted_count} trips where {field_name}='{field_value}'")

                return {
                    "success": True,
                    "message": f"Successfully deleted {deleted_count} trip(s) where {field_name}='{field_value}'",
                    "deleted_count": deleted_count
                }

            except Exception as err:
                logger.error(f'Database delete by field error: {err}', exc_info=True)
                session.rollback()
                return {
                    "success": False,
                    "message": f"Database error: {str(err)}",
                    "deleted_count": 0
                }
    
    @classmethod
    def truncate_table(cls, timeout_seconds: int = 300) -> dict:
        """Truncate the trips table (delete all records)

        Args:
            timeout_seconds: Statement timeout in seconds (default: 300 = 5 minutes)
        """
        with cls.get_session() as session:
            try:
                # Count records before truncation
                count_before = session.exec(select(cls)).all()
                count_before = len(count_before)

                logger.info(f'Truncating trips table with {count_before} records')

                # Set statement timeout (convert seconds to milliseconds)
                timeout_ms = timeout_seconds * 1000
                logger.info(f'Setting statement timeout to {timeout_seconds} seconds ({timeout_ms}ms)')
                session.execute(text(f'SET statement_timeout = {timeout_ms}'))

                # Use TRUNCATE for better performance (resets identity columns)
                # TRUNCATE is faster than DELETE for removing all rows
                session.execute(text('TRUNCATE TABLE trips RESTART IDENTITY CASCADE'))
                session.commit()

                logger.info(f'Successfully truncated trips table. Deleted {count_before} records')

                return {
                    "success": True,
                    "message": f"Successfully truncated trips table",
                    "deleted_count": count_before
                }

            except Exception as err:
                logger.error(f'Database truncate error: {err}', exc_info=True)
                session.rollback()

                # Fallback to DELETE if TRUNCATE fails (e.g., due to foreign key constraints)
                try:
                    logger.info('TRUNCATE failed, attempting DELETE fallback')

                    # Set timeout for DELETE as well
                    timeout_ms = timeout_seconds * 1000
                    session.execute(text(f'SET statement_timeout = {timeout_ms}'))

                    deleted = session.exec(select(cls)).all()
                    count = len(deleted)

                    for trip in deleted:
                        session.delete(trip)

                    session.commit()
                    logger.info(f'Successfully deleted all {count} records using DELETE')

                    return {
                        "success": True,
                        "message": f"Successfully deleted all trips (using DELETE)",
                        "deleted_count": count
                    }

                except Exception as delete_err:
                    logger.error(f'Database delete fallback error: {delete_err}', exc_info=True)
                    session.rollback()
                    return {
                        "success": False,
                        "message": f"Failed to truncate table: {str(delete_err)}",
                        "deleted_count": 0
                    }


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
    customerGroup: Optional[str] = Field(max_length=200, default=None)
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
    dispatcher: Optional[str] = Field(max_length=100, default=None)
    dispatcher: Optional[str] = Field(max_length=100, default=None)


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
    customerGroup: Optional[str] = Field(max_length=200, default=None)
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
    dispatcher: Optional[str] = Field(max_length=100, default=None)