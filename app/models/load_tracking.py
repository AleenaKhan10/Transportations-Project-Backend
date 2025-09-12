from typing import List, Optional
from datetime import datetime
from decimal import Decimal

from sqlmodel import SQLModel, Field, Session, select, text
from pydantic import BaseModel

from db import engine
from helpers import logger


class ActiveLoadTracking(SQLModel, table=True):
    __tablename__ = "active_load_tracking"
    
    load_id: str = Field(primary_key=True, max_length=50)
    trip_id: Optional[str] = Field(default=None, max_length=50)
    vehicle_id: Optional[str] = Field(default=None, max_length=50)
    driver_name: Optional[str] = Field(default=None, max_length=50)
    driver_phone_number: Optional[str] = Field(default=None, max_length=50)
    truck_unit: Optional[int] = Field(default=None)
    start_time: Optional[datetime] = Field(default=None)
    start_odometer_miles: Optional[int] = Field(default=None)
    current_odometer_miles: Optional[int] = Field(default=None)
    miles_threshold: Optional[int] = Field(default=250)
    current_stop_start: Optional[datetime] = Field(default=None)
    total_distance_traveled: Optional[Decimal] = Field(default=Decimal('0'), max_digits=10, decimal_places=2)
    last_alert_sent: Optional[datetime] = Field(default=None)
    last_known_lat: Optional[float] = Field(default=None)
    last_known_lng: Optional[float] = Field(default=None)
    status: Optional[str] = Field(default='EnRouteToDelivery', max_length=50)
    violation_resolved: Optional[bool] = Field(default=False)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

    @classmethod
    def get_session(cls) -> Session:
        """Create a database session"""
        return Session(engine)

    @classmethod
    def get_all(cls, limit: int = 5000, sort_by: str = "created_at", sort_order: str = "desc") -> List["ActiveLoadTracking"]:
        """Get all active load tracking records"""
        logger.info(f'Getting all active load tracking records with limit: {limit}, sort: {sort_by} {sort_order}')
        
        with cls.get_session() as session:
            try:
                # Validate sort_by field
                valid_sort_fields = {
                    'load_id', 'trip_id', 'vehicle_id', 'driver_name', 'truck_unit', 
                    'start_time', 'miles_threshold', 'total_distance_traveled', 'status',
                    'created_at', 'updated_at'
                }
                if sort_by not in valid_sort_fields:
                    sort_by = "created_at"
                
                # Build query with sorting
                if sort_order.lower() == "asc":
                    statement = select(cls).order_by(getattr(cls, sort_by)).limit(limit)
                else:
                    statement = select(cls).order_by(getattr(cls, sort_by).desc()).limit(limit)
                
                records = session.exec(statement).all()
                return list(records)
                
            except Exception as err:
                logger.error(f'Database query error: {err}', exc_info=True)
                return []

    @classmethod
    def get_by_id(cls, load_id: str) -> Optional["ActiveLoadTracking"]:
        """Get an active load tracking record by ID"""
        with cls.get_session() as session:
            try:
                statement = select(cls).where(cls.load_id == load_id)
                return session.exec(statement).first()
                
            except Exception as err:
                logger.error(f'Database query error: {err}', exc_info=True)
                return None

    @classmethod
    def get_by_status(cls, status_filter: str, limit: int = 5000, sort_by: str = "created_at", sort_order: str = "desc") -> List["ActiveLoadTracking"]:
        """Get active load tracking records by status"""
        logger.info(f'Getting active load tracking records by status: {status_filter} with limit: {limit}, sort: {sort_by} {sort_order}')
        
        with cls.get_session() as session:
            try:
                # Validate sort_by field
                valid_sort_fields = {
                    'load_id', 'trip_id', 'vehicle_id', 'driver_name', 'truck_unit', 
                    'start_time', 'miles_threshold', 'total_distance_traveled', 'status',
                    'created_at', 'updated_at'
                }
                if sort_by not in valid_sort_fields:
                    sort_by = "created_at"
                
                # Build query with status filter and sorting
                statement = select(cls).where(cls.status == status_filter)
                
                if sort_order.lower() == "asc":
                    statement = statement.order_by(getattr(cls, sort_by)).limit(limit)
                else:
                    statement = statement.order_by(getattr(cls, sort_by).desc()).limit(limit)
                
                records = session.exec(statement).all()
                return list(records)
                
            except Exception as err:
                logger.error(f'Database query error: {err}', exc_info=True)
                return []

    @classmethod
    def get_by_created_at(cls, created_at_date: str, limit: int = 5000, sort_by: str = "created_at", sort_order: str = "desc") -> List["ActiveLoadTracking"]:
        """Get active load tracking records by created_at date (YYYY-MM-DD format)"""
        logger.info(f'Getting active load tracking records by created_at date: {created_at_date} with limit: {limit}, sort: {sort_by} {sort_order}')
        
        with cls.get_session() as session:
            try:
                # Parse the date string
                from datetime import datetime
                target_date = datetime.strptime(created_at_date, "%Y-%m-%d").date()
                
                # Validate sort_by field
                valid_sort_fields = {
                    'load_id', 'trip_id', 'vehicle_id', 'driver_name', 'truck_unit', 
                    'start_time', 'miles_threshold', 'total_distance_traveled', 'status',
                    'created_at', 'updated_at'
                }
                if sort_by not in valid_sort_fields:
                    sort_by = "created_at"
                
                # Build query with date filter (match date part only)
                statement = select(cls).where(text("DATE(created_at) = :target_date")).params(target_date=target_date)
                
                if sort_order.lower() == "asc":
                    statement = statement.order_by(getattr(cls, sort_by)).limit(limit)
                else:
                    statement = statement.order_by(getattr(cls, sort_by).desc()).limit(limit)
                
                records = session.exec(statement).all()
                return list(records)
                
            except ValueError as ve:
                logger.error(f'Invalid date format: {ve}', exc_info=True)
                return []
            except Exception as err:
                logger.error(f'Database query error: {err}', exc_info=True)
                return []

    @classmethod
    def create(cls, record_data: "ActiveLoadTrackingCreate") -> Optional["ActiveLoadTracking"]:
        """Create a new active load tracking record"""
        logger.info(f'Creating active load tracking record with ID: {record_data.load_id}')
        
        with cls.get_session() as session:
            try:
                record = cls(**record_data.model_dump(exclude_unset=True))
                session.add(record)
                session.commit()
                session.refresh(record)
                return record
                
            except Exception as err:
                logger.error(f'Database create error: {err}', exc_info=True)
                session.rollback()
                return None

    @classmethod
    def update(cls, load_id: str, record_data: "ActiveLoadTrackingUpdate") -> Optional["ActiveLoadTracking"]:
        """Update an active load tracking record"""
        logger.info(f'Updating active load tracking record with ID: {load_id}')
        
        with cls.get_session() as session:
            try:
                record = session.exec(select(cls).where(cls.load_id == load_id)).first()
                if not record:
                    return None
                
                update_data = record_data.model_dump(exclude_unset=True, exclude_none=True)
                for field, value in update_data.items():
                    setattr(record, field, value)
                
                record.updated_at = datetime.utcnow()
                session.add(record)
                session.commit()
                session.refresh(record)
                return record
                
            except Exception as err:
                logger.error(f'Database update error: {err}', exc_info=True)
                session.rollback()
                return None

    @classmethod
    def delete(cls, load_id: str) -> bool:
        """Delete an active load tracking record"""
        logger.info(f'Deleting active load tracking record with ID: {load_id}')
        
        with cls.get_session() as session:
            try:
                record = session.exec(select(cls).where(cls.load_id == load_id)).first()
                if not record:
                    return False
                
                session.delete(record)
                session.commit()
                return True
                
            except Exception as err:
                logger.error(f'Database delete error: {err}', exc_info=True)
                session.rollback()
                return False

    @classmethod
    def upsert(cls, record_data: "ActiveLoadTrackingUpsert") -> Optional["ActiveLoadTracking"]:
        """Upsert an active load tracking record (insert or update if exists)"""
        logger.info(f'Upserting active load tracking record with ID: {record_data.load_id}')
        
        with cls.get_session() as session:
            try:
                # Build dynamic SQL based on provided fields
                provided_fields = []
                provided_values = {}
                update_clauses = []
                
                # Always include load_id
                provided_fields.append("load_id")
                provided_values["load_id"] = record_data.load_id
                
                # Check each field and only include if it's not None
                field_mappings = {
                    "trip_id": record_data.trip_id,
                    "vehicle_id": record_data.vehicle_id,
                    "driver_name": record_data.driver_name,
                    "driver_phone_number": record_data.driver_phone_number,
                    "truck_unit": record_data.truck_unit,
                    "start_time": record_data.start_time,
                    "start_odometer_miles": record_data.start_odometer_miles,
                    "current_odometer_miles": record_data.current_odometer_miles,
                    "miles_threshold": record_data.miles_threshold,
                    "current_stop_start": record_data.current_stop_start,
                    "total_distance_traveled": record_data.total_distance_traveled,
                    "last_alert_sent": record_data.last_alert_sent,
                    "last_known_lat": record_data.last_known_lat,
                    "last_known_lng": record_data.last_known_lng,
                    "status": record_data.status,
                    "violation_resolved": record_data.violation_resolved,
                    "updated_at": datetime.utcnow()
                }
                
                for field_name, field_value in field_mappings.items():
                    if field_value is not None:
                        provided_fields.append(field_name)
                        provided_values[field_name] = field_value
                        update_clauses.append(f'"{field_name}" = EXCLUDED."{field_name}"')
                
                # Build the dynamic SQL
                fields_str = ", ".join([f'"{field}"' for field in provided_fields])
                values_str = ", ".join([f":{field}" for field in provided_fields])
                update_str = ", ".join(update_clauses)
                
                sql = f"""
                    INSERT INTO active_load_tracking ({fields_str})
                    VALUES ({values_str})
                    ON CONFLICT ("load_id") DO UPDATE SET {update_str}
                """
                
                session.execute(text(sql), provided_values)
                session.commit()
                
                # Return the updated/inserted record
                return cls.get_by_id(record_data.load_id)
                
            except Exception as err:
                logger.error(f'Database upsert error: {err}', exc_info=True)
                session.rollback()
                return None


class ActiveLoadTrackingCreate(BaseModel):
    load_id: str
    trip_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    driver_name: Optional[str] = None
    driver_phone_number: Optional[str] = None
    truck_unit: Optional[int] = None
    start_time: Optional[datetime] = None
    start_odometer_miles: Optional[int] = None
    current_odometer_miles: Optional[int] = None
    miles_threshold: Optional[int] = 250
    current_stop_start: Optional[datetime] = None
    total_distance_traveled: Optional[Decimal] = Decimal('0')
    last_alert_sent: Optional[datetime] = None
    last_known_lat: Optional[float] = None
    last_known_lng: Optional[float] = None
    status: Optional[str] = 'EnRouteToDelivery'
    violation_resolved: Optional[bool] = False


class ActiveLoadTrackingUpdate(BaseModel):
    trip_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    driver_name: Optional[str] = None
    driver_phone_number: Optional[str] = None
    truck_unit: Optional[int] = None
    start_time: Optional[datetime] = None
    start_odometer_miles: Optional[int] = None
    current_odometer_miles: Optional[int] = None
    miles_threshold: Optional[int] = None
    current_stop_start: Optional[datetime] = None
    total_distance_traveled: Optional[Decimal] = None
    last_alert_sent: Optional[datetime] = None
    last_known_lat: Optional[float] = None
    last_known_lng: Optional[float] = None
    status: Optional[str] = None
    violation_resolved: Optional[bool] = None


class ActiveLoadTrackingUpsert(BaseModel):
    load_id: str
    trip_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    driver_name: Optional[str] = None
    driver_phone_number: Optional[str] = None
    truck_unit: Optional[int] = None
    start_time: Optional[datetime] = None
    start_odometer_miles: Optional[int] = None
    current_odometer_miles: Optional[int] = None
    miles_threshold: Optional[int] = None
    current_stop_start: Optional[datetime] = None
    total_distance_traveled: Optional[Decimal] = None
    last_alert_sent: Optional[datetime] = None
    last_known_lat: Optional[float] = None
    last_known_lng: Optional[float] = None
    status: Optional[str] = None
    violation_resolved: Optional[bool] = None


class ViolationAlert(SQLModel, table=True):
    __tablename__ = "violation_alerts"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    load_id: Optional[str] = Field(default=None, max_length=50)
    vehicle_id: Optional[str] = Field(default=None, max_length=50)
    violation_time: Optional[datetime] = Field(default=None)
    location_lat: Optional[float] = Field(default=None)
    location_lng: Optional[float] = Field(default=None)
    distance_traveled_miles: Optional[Decimal] = Field(default=None, max_digits=10, decimal_places=2)
    current_odometer_miles: Optional[Decimal] = Field(default=None, max_digits=10, decimal_places=2)
    stop_duration_minutes: Optional[int] = Field(default=None)
    current_speed: Optional[Decimal] = Field(default=None, max_digits=5, decimal_places=2)
    alert_sent_to_slack: Optional[bool] = Field(default=True)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

    @classmethod
    def get_session(cls) -> Session:
        """Create a database session"""
        return Session(engine)

    @classmethod
    def get_all(cls, limit: int = 5000, sort_by: str = "created_at", sort_order: str = "desc") -> List["ViolationAlert"]:
        """Get all violation alerts"""
        logger.info(f'Getting all violation alerts with limit: {limit}, sort: {sort_by} {sort_order}')
        
        with cls.get_session() as session:
            try:
                # Validate sort_by field
                valid_sort_fields = {
                    'id', 'load_id', 'vehicle_id', 'violation_time', 'distance_traveled_miles',
                    'current_odometer_miles', 'stop_duration_minutes', 'current_speed', 'created_at'
                }
                if sort_by not in valid_sort_fields:
                    sort_by = "created_at"
                
                # Build query with sorting
                if sort_order.lower() == "asc":
                    statement = select(cls).order_by(getattr(cls, sort_by)).limit(limit)
                else:
                    statement = select(cls).order_by(getattr(cls, sort_by).desc()).limit(limit)
                
                records = session.exec(statement).all()
                return list(records)
                
            except Exception as err:
                logger.error(f'Database query error: {err}', exc_info=True)
                return []

    @classmethod
    def get_by_id(cls, record_id: int) -> Optional["ViolationAlert"]:
        """Get a violation alert by ID"""
        with cls.get_session() as session:
            try:
                statement = select(cls).where(cls.id == record_id)
                return session.exec(statement).first()
                
            except Exception as err:
                logger.error(f'Database query error: {err}', exc_info=True)
                return None

    @classmethod
    def create(cls, record_data: "ViolationAlertCreate") -> Optional["ViolationAlert"]:
        """Create a new violation alert"""
        logger.info('Creating violation alert record')
        
        with cls.get_session() as session:
            try:
                record = cls(**record_data.model_dump(exclude_unset=True))
                session.add(record)
                session.commit()
                session.refresh(record)
                return record
                
            except Exception as err:
                logger.error(f'Database create error: {err}', exc_info=True)
                session.rollback()
                return None

    @classmethod
    def update(cls, record_id: int, record_data: "ViolationAlertUpdate") -> Optional["ViolationAlert"]:
        """Update a violation alert"""
        logger.info(f'Updating violation alert with ID: {record_id}')
        
        with cls.get_session() as session:
            try:
                record = session.exec(select(cls).where(cls.id == record_id)).first()
                if not record:
                    return None
                
                update_data = record_data.model_dump(exclude_unset=True, exclude_none=True)
                for field, value in update_data.items():
                    setattr(record, field, value)
                
                session.add(record)
                session.commit()
                session.refresh(record)
                return record
                
            except Exception as err:
                logger.error(f'Database update error: {err}', exc_info=True)
                session.rollback()
                return None

    @classmethod
    def delete(cls, record_id: int) -> bool:
        """Delete a violation alert"""
        logger.info(f'Deleting violation alert with ID: {record_id}')
        
        with cls.get_session() as session:
            try:
                record = session.exec(select(cls).where(cls.id == record_id)).first()
                if not record:
                    return False
                
                session.delete(record)
                session.commit()
                return True
                
            except Exception as err:
                logger.error(f'Database delete error: {err}', exc_info=True)
                session.rollback()
                return False

    @classmethod
    def upsert(cls, record_data: "ViolationAlertUpsert") -> Optional["ViolationAlert"]:
        """Upsert a violation alert (insert or update if exists)"""
        logger.info('Upserting violation alert record')
        
        with cls.get_session() as session:
            try:
                if record_data.id:
                    # Update existing record
                    record = session.exec(select(cls).where(cls.id == record_data.id)).first()
                    if record:
                        update_data = record_data.model_dump(exclude_unset=True, exclude_none=True)
                        for field, value in update_data.items():
                            if field != 'id':
                                setattr(record, field, value)
                        session.add(record)
                        session.commit()
                        session.refresh(record)
                        return record
                
                # Create new record
                record_dict = record_data.model_dump(exclude_unset=True)
                if 'id' in record_dict and record_dict['id'] is None:
                    del record_dict['id']
                record = cls(**record_dict)
                session.add(record)
                session.commit()
                session.refresh(record)
                return record
                
            except Exception as err:
                logger.error(f'Database upsert error: {err}', exc_info=True)
                session.rollback()
                return None


class ViolationAlertCreate(BaseModel):
    load_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    violation_time: Optional[datetime] = None
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    distance_traveled_miles: Optional[Decimal] = None
    current_odometer_miles: Optional[Decimal] = None
    stop_duration_minutes: Optional[int] = None
    current_speed: Optional[Decimal] = None
    alert_sent_to_slack: Optional[bool] = True


class ViolationAlertUpdate(BaseModel):
    load_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    violation_time: Optional[datetime] = None
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    distance_traveled_miles: Optional[Decimal] = None
    current_odometer_miles: Optional[Decimal] = None
    stop_duration_minutes: Optional[int] = None
    current_speed: Optional[Decimal] = None
    alert_sent_to_slack: Optional[bool] = None


class ViolationAlertUpsert(BaseModel):
    id: Optional[int] = None
    load_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    violation_time: Optional[datetime] = None
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    distance_traveled_miles: Optional[Decimal] = None
    current_odometer_miles: Optional[Decimal] = None
    stop_duration_minutes: Optional[int] = None
    current_speed: Optional[Decimal] = None
    alert_sent_to_slack: Optional[bool] = None


class DispatchedTrip(SQLModel, table=True):
    __tablename__ = "dispatched_trips"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    trip_key: Optional[int] = Field(default=None, unique=True)
    trip_id: Optional[str] = Field(default=None, max_length=50)
    created_by: Optional[int] = Field(default=None)
    created_on: Optional[datetime] = Field(default=None)
    derived_driver_key: Optional[int] = Field(default=None)
    derivedtrailerkey: Optional[int] = Field(default=None)
    derivedtruckkey: Optional[int] = Field(default=None)
    dispatchedby: Optional[int] = Field(default=None)

    @classmethod
    def get_session(cls) -> Session:
        """Create a database session"""
        return Session(engine)

    @classmethod
    def get_all(cls, limit: int = 5000, sort_by: str = "created_on", sort_order: str = "desc") -> List["DispatchedTrip"]:
        """Get all dispatched trips"""
        logger.info(f'Getting all dispatched trips with limit: {limit}, sort: {sort_by} {sort_order}')
        
        with cls.get_session() as session:
            try:
                # Validate sort_by field
                valid_sort_fields = {
                    'id', 'trip_key', 'trip_id', 'created_by', 'created_on', 'derived_driver_key',
                    'derivedtrailerkey', 'derivedtruckkey', 'dispatchedby'
                }
                if sort_by not in valid_sort_fields:
                    sort_by = "created_on"
                
                # Build query with sorting
                if sort_order.lower() == "asc":
                    statement = select(cls).order_by(getattr(cls, sort_by)).limit(limit)
                else:
                    statement = select(cls).order_by(getattr(cls, sort_by).desc()).limit(limit)
                
                records = session.exec(statement).all()
                return list(records)
                
            except Exception as err:
                logger.error(f'Database query error: {err}', exc_info=True)
                return []

    @classmethod
    def get_by_id(cls, trip_id: str) -> Optional["DispatchedTrip"]:
        """Get a dispatched trip by trip_id"""
        with cls.get_session() as session:
            try:
                statement = select(cls).where(cls.trip_id == trip_id)
                return session.exec(statement).first()
                
            except Exception as err:
                logger.error(f'Database query error: {err}', exc_info=True)
                return None

    @classmethod
    def create(cls, record_data: "DispatchedTripCreate") -> Optional["DispatchedTrip"]:
        """Create a new dispatched trip"""
        logger.info('Creating dispatched trip record')
        
        with cls.get_session() as session:
            try:
                record = cls(**record_data.model_dump(exclude_unset=True))
                session.add(record)
                session.commit()
                session.refresh(record)
                return record
                
            except Exception as err:
                logger.error(f'Database create error: {err}', exc_info=True)
                session.rollback()
                return None

    @classmethod
    def update(cls, trip_id: str, record_data: "DispatchedTripUpdate") -> Optional["DispatchedTrip"]:
        """Update a dispatched trip"""
        logger.info(f'Updating dispatched trip with trip_id: {trip_id}')
        
        with cls.get_session() as session:
            try:
                record = session.exec(select(cls).where(cls.trip_id == trip_id)).first()
                if not record:
                    return None
                
                update_data = record_data.model_dump(exclude_unset=True, exclude_none=True)
                for field, value in update_data.items():
                    setattr(record, field, value)
                
                session.add(record)
                session.commit()
                session.refresh(record)
                return record
                
            except Exception as err:
                logger.error(f'Database update error: {err}', exc_info=True)
                session.rollback()
                return None

    @classmethod
    def delete(cls, trip_id: str) -> bool:
        """Delete a dispatched trip"""
        logger.info(f'Deleting dispatched trip with trip_id: {trip_id}')
        
        with cls.get_session() as session:
            try:
                record = session.exec(select(cls).where(cls.trip_id == trip_id)).first()
                if not record:
                    return False
                
                session.delete(record)
                session.commit()
                return True
                
            except Exception as err:
                logger.error(f'Database delete error: {err}', exc_info=True)
                session.rollback()
                return False

    @classmethod
    def delete_by_trip_key(cls, trip_key: int) -> bool:
        """Delete a dispatched trip by trip_key"""
        logger.info(f'Deleting dispatched trip with trip_key: {trip_key}')
        
        with cls.get_session() as session:
            try:
                record = session.exec(select(cls).where(cls.trip_key == trip_key)).first()
                if not record:
                    return False
                
                session.delete(record)
                session.commit()
                return True
                
            except Exception as err:
                logger.error(f'Database delete error: {err}', exc_info=True)
                session.rollback()
                return False

    @classmethod
    def upsert(cls, record_data: "DispatchedTripUpsert") -> Optional["DispatchedTrip"]:
        """Upsert a dispatched trip (insert or update if exists)"""
        logger.info('Upserting dispatched trip record')
        
        with cls.get_session() as session:
            try:
                # Build dynamic SQL based on provided fields
                provided_fields = []
                provided_values = {}
                update_clauses = []
                
                # Check each field and only include if it's not None
                field_mappings = {
                    "trip_key": record_data.trip_key,
                    "trip_id": record_data.trip_id,
                    "created_by": record_data.created_by,
                    "created_on": record_data.created_on,
                    "derived_driver_key": record_data.derived_driver_key,
                    "derivedtrailerkey": record_data.derivedtrailerkey,
                    "derivedtruckkey": record_data.derivedtruckkey,
                    "dispatchedby": record_data.dispatchedby
                }
                
                for field_name, field_value in field_mappings.items():
                    if field_value is not None:
                        provided_fields.append(field_name)
                        provided_values[field_name] = field_value
                        update_clauses.append(f'"{field_name}" = EXCLUDED."{field_name}"')
                
                if not provided_fields:
                    return None
                
                # Use trip_key as the conflict field if it's provided
                if record_data.trip_key is not None:
                    # Build the dynamic SQL
                    fields_str = ", ".join([f'"{field}"' for field in provided_fields])
                    values_str = ", ".join([f":{field}" for field in provided_fields])
                    update_str = ", ".join(update_clauses)
                    
                    sql = f"""
                        INSERT INTO dispatched_trips ({fields_str})
                        VALUES ({values_str})
                        ON CONFLICT ("trip_key") DO UPDATE SET {update_str}
                    """
                    
                    session.execute(text(sql), provided_values)
                    session.commit()
                    
                    # Return the updated/inserted record
                    return session.exec(select(cls).where(cls.trip_key == record_data.trip_key)).first()
                else:
                    # Create new record without conflict handling
                    record_dict = record_data.model_dump(exclude_unset=True)
                    if 'id' in record_dict and record_dict['id'] is None:
                        del record_dict['id']
                    record = cls(**record_dict)
                    session.add(record)
                    session.commit()
                    session.refresh(record)
                    return record
                
            except Exception as err:
                logger.error(f'Database upsert error: {err}', exc_info=True)
                session.rollback()
                return None


class DispatchedTripCreate(BaseModel):
    trip_key: Optional[int] = None
    trip_id: Optional[str] = None
    created_by: Optional[int] = None
    created_on: Optional[datetime] = None
    derived_driver_key: Optional[int] = None
    derivedtrailerkey: Optional[int] = None
    derivedtruckkey: Optional[int] = None
    dispatchedby: Optional[int] = None


class DispatchedTripUpdate(BaseModel):
    trip_key: Optional[int] = None
    trip_id: Optional[str] = None
    created_by: Optional[int] = None
    created_on: Optional[datetime] = None
    derived_driver_key: Optional[int] = None
    derivedtrailerkey: Optional[int] = None
    derivedtruckkey: Optional[int] = None
    dispatchedby: Optional[int] = None


class DispatchedTripUpsert(BaseModel):
    id: Optional[int] = None
    trip_key: Optional[int] = None
    trip_id: Optional[str] = None
    created_by: Optional[int] = None
    created_on: Optional[datetime] = None
    derived_driver_key: Optional[int] = None
    derivedtrailerkey: Optional[int] = None
    derivedtruckkey: Optional[int] = None
    dispatchedby: Optional[int] = None