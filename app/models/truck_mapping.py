from typing import Optional, List
from sqlmodel import SQLModel, Field, Session, select
from db import engine
from helpers import logger


class TruckMapping(SQLModel, table=True):
    __tablename__ = "truck_mapping"
    
    TruckUnit: str = Field(max_length=50, primary_key=True)
    TruckId: Optional[int] = None
    
    @classmethod
    def get_session(cls) -> Session:
        """Create a database session"""
        return Session(engine)
    
    @classmethod
    def get_all(cls, limit: int = 5000) -> List["TruckMapping"]:
        """Get all truck mappings from the database"""
        logger.info('GetAllTruckMappings request reached the service')
        
        with cls.get_session() as session:
            try:
                statement = select(cls).limit(limit)
                mappings = session.exec(statement).all()
                return list(mappings)
                
            except Exception as err:
                logger.error(f'Database query error: {err}', exc_info=True)
                return []
    
    @classmethod
    def get_by_truck_unit(cls, truck_unit: str) -> Optional["TruckMapping"]:
        """Get a truck mapping by TruckUnit"""
        with cls.get_session() as session:
            try:
                statement = select(cls).where(cls.TruckUnit == truck_unit)
                return session.exec(statement).first()
                
            except Exception as err:
                logger.error(f'Database query error: {err}', exc_info=True)
                return None
    
    @classmethod
    def get_by_truck_id(cls, truck_id: int) -> List["TruckMapping"]:
        """Get all truck mappings by TruckId"""
        with cls.get_session() as session:
            try:
                statement = select(cls).where(cls.TruckId == truck_id)
                mappings = session.exec(statement).all()
                return list(mappings)
                
            except Exception as err:
                logger.error(f'Database query error: {err}', exc_info=True)
                return []
    
    @classmethod
    def create(cls, truck_unit: str, truck_id: Optional[int] = None) -> Optional["TruckMapping"]:
        """Create a new truck mapping"""
        with cls.get_session() as session:
            try:
                mapping = cls(TruckUnit=truck_unit, TruckId=truck_id)
                session.add(mapping)
                session.commit()
                session.refresh(mapping)
                return mapping
                
            except Exception as err:
                logger.error(f'Database insert error: {err}', exc_info=True)
                return None
    
    @classmethod
    def update(cls, truck_unit: str, truck_id: Optional[int] = None) -> Optional["TruckMapping"]:
        """Update an existing truck mapping"""
        with cls.get_session() as session:
            try:
                statement = select(cls).where(cls.TruckUnit == truck_unit)
                mapping = session.exec(statement).first()
                
                if mapping:
                    mapping.TruckId = truck_id
                    session.add(mapping)
                    session.commit()
                    session.refresh(mapping)
                    return mapping
                return None
                
            except Exception as err:
                logger.error(f'Database update error: {err}', exc_info=True)
                return None
    
    @classmethod
    def delete(cls, truck_unit: str) -> bool:
        """Delete a truck mapping"""
        with cls.get_session() as session:
            try:
                statement = select(cls).where(cls.TruckUnit == truck_unit)
                mapping = session.exec(statement).first()
                
                if mapping:
                    session.delete(mapping)
                    session.commit()
                    return True
                return False
                
            except Exception as err:
                logger.error(f'Database delete error: {err}', exc_info=True)
                return False


class TruckMappingCreate(SQLModel):
    """Schema for creating a truck mapping"""
    TruckUnit: str = Field(max_length=50)
    TruckId: Optional[int] = None


class TruckMappingUpdate(SQLModel):
    """Schema for updating a truck mapping"""
    TruckId: Optional[int] = None