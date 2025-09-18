from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Session, select, text, func, or_
from db import engine
from helpers import logger


class DriverMapping(SQLModel, table=True):
    __tablename__ = "driver_mapping"
    __table_args__ = {'schema': 'dev'}

    driverid: str = Field(primary_key=True)
    driverkey: Optional[str] = None
    driverfullname: Optional[str] = Field(max_length=255)

    @classmethod
    def get_session(cls) -> Session:
        """Create a database session"""
        return Session(engine)

    @classmethod
    def get_with_filters(
        cls,
        driverid: Optional[str] = None,
        driverkey: Optional[str] = None,
        driverfullname: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        sort: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get driver mappings with flexible filtering

        Args:
            driverid: Filter by driver ID
            driverkey: Filter by driver key
            driverfullname: Filter by driver full name (partial match)
            limit: Number of records to return (max 1000)
            offset: Pagination offset
            sort: Sort field (e.g., "driverid", "-driverid" for DESC)

        Returns:
            Dict containing data, pagination info, and success status
        """
        logger.info(f'Getting driver mappings with filters - driverid: {driverid}, driverkey: {driverkey}, driverfullname: {driverfullname}')

        # Enforce max limit
        limit = min(limit, 1000)

        with cls.get_session() as session:
            try:
                # Build base query
                statement = select(cls)

                # Apply filters
                conditions = []

                if driverid is not None:
                    conditions.append(cls.driverid == driverid)

                if driverkey is not None:
                    conditions.append(cls.driverkey == driverkey)

                if driverfullname is not None:
                    # Case-insensitive partial match
                    conditions.append(func.lower(cls.driverfullname).contains(driverfullname.lower()))

                # Apply all conditions with AND logic
                if conditions:
                    statement = statement.where(*conditions)

                # Get total count for pagination
                count_statement = select(func.count()).select_from(cls)
                if conditions:
                    count_statement = count_statement.where(*conditions)
                total_count = session.exec(count_statement).first()

                # Apply sorting
                if sort:
                    if sort.startswith('-'):
                        # Descending order
                        field_name = sort[1:]
                        if hasattr(cls, field_name):
                            statement = statement.order_by(getattr(cls, field_name).desc())
                    else:
                        # Ascending order
                        if hasattr(cls, sort):
                            statement = statement.order_by(getattr(cls, sort))

                # Apply pagination
                statement = statement.offset(offset).limit(limit)

                # Execute query
                mappings = session.exec(statement).all()

                return {
                    "success": True,
                    "data": list(mappings),
                    "pagination": {
                        "total": total_count or 0,
                        "limit": limit,
                        "offset": offset
                    }
                }

            except Exception as err:
                logger.error(f'Database query error: {err}', exc_info=True)
                return {
                    "success": False,
                    "data": [],
                    "pagination": {
                        "total": 0,
                        "limit": limit,
                        "offset": offset
                    },
                    "error": str(err)
                }

    @classmethod
    def get_by_driverid(cls, driverid: str) -> Optional["DriverMapping"]:
        """Get a driver mapping by driverid"""
        with cls.get_session() as session:
            try:
                statement = select(cls).where(cls.driverid == driverid)
                return session.exec(statement).first()

            except Exception as err:
                logger.error(f'Database query error: {err}', exc_info=True)
                return None

    @classmethod
    def get_by_driverkey(cls, driverkey: str) -> List["DriverMapping"]:
        """Get all driver mappings by driverkey"""
        with cls.get_session() as session:
            try:
                statement = select(cls).where(cls.driverkey == driverkey)
                mappings = session.exec(statement).all()
                return list(mappings)

            except Exception as err:
                logger.error(f'Database query error: {err}', exc_info=True)
                return []

    @classmethod
    def create(cls, driverid: str, driverkey: Optional[str] = None, driverfullname: Optional[str] = None) -> Optional["DriverMapping"]:
        """Create a new driver mapping"""
        with cls.get_session() as session:
            try:
                mapping = cls(
                    driverid=driverid,
                    driverkey=driverkey,
                    driverfullname=driverfullname
                )
                session.add(mapping)
                session.commit()
                session.refresh(mapping)
                return mapping

            except Exception as err:
                logger.error(f'Database insert error: {err}', exc_info=True)
                return None

    @classmethod
    def update(cls, driverid: str, driverkey: Optional[str] = None, driverfullname: Optional[str] = None) -> Optional["DriverMapping"]:
        """Update an existing driver mapping"""
        with cls.get_session() as session:
            try:
                statement = select(cls).where(cls.driverid == driverid)
                mapping = session.exec(statement).first()

                if mapping:
                    if driverkey is not None:
                        mapping.driverkey = driverkey
                    if driverfullname is not None:
                        mapping.driverfullname = driverfullname
                    session.add(mapping)
                    session.commit()
                    session.refresh(mapping)
                    return mapping
                return None

            except Exception as err:
                logger.error(f'Database update error: {err}', exc_info=True)
                return None

    @classmethod
    def delete(cls, driverid: str) -> bool:
        """Delete a driver mapping"""
        with cls.get_session() as session:
            try:
                statement = select(cls).where(cls.driverid == driverid)
                mapping = session.exec(statement).first()

                if mapping:
                    session.delete(mapping)
                    session.commit()
                    return True
                return False

            except Exception as err:
                logger.error(f'Database delete error: {err}', exc_info=True)
                return False


class DriverMappingCreate(SQLModel):
    """Schema for creating a driver mapping"""
    driverid: str
    driverkey: Optional[str] = None
    driverfullname: Optional[str] = Field(max_length=255, default=None)


class DriverMappingUpdate(SQLModel):
    """Schema for updating a driver mapping"""
    driverkey: Optional[str] = None
    driverfullname: Optional[str] = Field(max_length=255, default=None)


class DriverMappingResponse(SQLModel):
    """Response schema for driver mapping queries"""
    driverid: str
    driverkey: Optional[str] = None
    driverfullname: Optional[str] = None