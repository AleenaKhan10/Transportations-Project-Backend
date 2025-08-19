from typing import Optional, List
from sqlmodel import SQLModel, Field, Session, select
from db import engine
from helpers import logger


class TempSensorMapping(SQLModel, table=True):
    __tablename__ = "temp_sensor_mapping"
    
    TempSensorNAME: str = Field(max_length=100, primary_key=True)
    TempSensorID: Optional[int] = None
    
    @classmethod
    def get_session(cls) -> Session:
        """Create a database session"""
        return Session(engine)
    
    @classmethod
    def get_all(cls, limit: int = 5000) -> List["TempSensorMapping"]:
        """Get all temp sensor mappings from the database"""
        logger.info('GetAllTempSensorMappings request reached the service')
        
        with cls.get_session() as session:
            try:
                statement = select(cls).limit(limit)
                mappings = session.exec(statement).all()
                return list(mappings)
                
            except Exception as err:
                logger.error(f'Database query error: {err}', exc_info=True)
                return []
    
    @classmethod
    def get_by_sensor_name(cls, sensor_name: str) -> Optional["TempSensorMapping"]:
        """Get a temp sensor mapping by TempSensorNAME"""
        with cls.get_session() as session:
            try:
                statement = select(cls).where(cls.TempSensorNAME == sensor_name)
                return session.exec(statement).first()
                
            except Exception as err:
                logger.error(f'Database query error: {err}', exc_info=True)
                return None
    
    @classmethod
    def get_by_sensor_id(cls, sensor_id: int) -> List["TempSensorMapping"]:
        """Get all temp sensor mappings by TempSensorID"""
        with cls.get_session() as session:
            try:
                statement = select(cls).where(cls.TempSensorID == sensor_id)
                mappings = session.exec(statement).all()
                return list(mappings)
                
            except Exception as err:
                logger.error(f'Database query error: {err}', exc_info=True)
                return []
    
    @classmethod
    def create(cls, sensor_name: str, sensor_id: Optional[int] = None) -> Optional["TempSensorMapping"]:
        """Create a new temp sensor mapping"""
        with cls.get_session() as session:
            try:
                mapping = cls(TempSensorNAME=sensor_name, TempSensorID=sensor_id)
                session.add(mapping)
                session.commit()
                session.refresh(mapping)
                return mapping
                
            except Exception as err:
                logger.error(f'Database insert error: {err}', exc_info=True)
                return None
    
    @classmethod
    def update(cls, sensor_name: str, sensor_id: Optional[int] = None) -> Optional["TempSensorMapping"]:
        """Update an existing temp sensor mapping"""
        with cls.get_session() as session:
            try:
                statement = select(cls).where(cls.TempSensorNAME == sensor_name)
                mapping = session.exec(statement).first()
                
                if mapping:
                    mapping.TempSensorID = sensor_id
                    session.add(mapping)
                    session.commit()
                    session.refresh(mapping)
                    return mapping
                return None
                
            except Exception as err:
                logger.error(f'Database update error: {err}', exc_info=True)
                return None
    
    @classmethod
    def delete(cls, sensor_name: str) -> bool:
        """Delete a temp sensor mapping"""
        with cls.get_session() as session:
            try:
                statement = select(cls).where(cls.TempSensorNAME == sensor_name)
                mapping = session.exec(statement).first()
                
                if mapping:
                    session.delete(mapping)
                    session.commit()
                    return True
                return False
                
            except Exception as err:
                logger.error(f'Database delete error: {err}', exc_info=True)
                return False


class TempSensorMappingCreate(SQLModel):
    """Schema for creating a temp sensor mapping"""
    TempSensorNAME: str = Field(max_length=100)
    TempSensorID: Optional[int] = None


class TempSensorMappingUpdate(SQLModel):
    """Schema for updating a temp sensor mapping"""
    TempSensorID: Optional[int] = None