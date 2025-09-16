from typing import Optional, List
from sqlmodel import SQLModel, Field, Session, select, text
from db import engine
from helpers import logger


class TruckMapping(SQLModel, table=True):
    __tablename__ = "truck_mapping"
    
    TruckUnit: str = Field(max_length=50, primary_key=True)
    TruckId: Optional[int] = None
    TruckKey: Optional[str] = None
    
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
    def get_by_truck_key(cls, truck_key: str) -> Optional["TruckMapping"]:
        """Get truck mapping by TruckKey (returns first match)"""
        with cls.get_session() as session:
            try:
                statement = select(cls).where(cls.TruckKey == truck_key)
                return session.exec(statement).first()

            except Exception as err:
                logger.error(f'Database query error: {err}', exc_info=True)
                return None
    
    @classmethod
    def create(cls, truck_unit: str, truck_id: Optional[int] = None, truck_key: Optional[str] = None) -> Optional["TruckMapping"]:
        """Create a new truck mapping"""
        with cls.get_session() as session:
            try:
                mapping = cls(TruckUnit=truck_unit, TruckId=truck_id, TruckKey=truck_key)
                session.add(mapping)
                session.commit()
                session.refresh(mapping)
                return mapping
                
            except Exception as err:
                logger.error(f'Database insert error: {err}', exc_info=True)
                return None
    
    @classmethod
    def update(cls, truck_unit: str, truck_id: Optional[int] = None, truck_key: Optional[str] = None) -> Optional["TruckMapping"]:
        """Update an existing truck mapping"""
        with cls.get_session() as session:
            try:
                statement = select(cls).where(cls.TruckUnit == truck_unit)
                mapping = session.exec(statement).first()
                
                if mapping:
                    if truck_id is not None:
                        mapping.TruckId = truck_id
                    if truck_key is not None:
                        mapping.TruckKey = truck_key
                    session.add(mapping)
                    session.commit()
                    session.refresh(mapping)
                    return mapping
                return None
                
            except Exception as err:
                logger.error(f'Database update error: {err}', exc_info=True)
                return None
    
    @classmethod
    def upsert(cls, truck_unit: str, truck_id: Optional[int] = None, truck_key: Optional[str] = None) -> Optional["TruckMapping"]:
        """Upsert a truck mapping (insert or update if exists) - only updates provided fields"""
        logger.info(f'Upserting truck mapping for unit: {truck_unit}')
        
        with cls.get_session() as session:
            try:
                # Build dynamic SQL based on provided fields
                provided_fields = ["TruckUnit"]
                provided_values = {"TruckUnit": truck_unit}
                update_clauses = []
                
                # Only include TruckId if it's provided (not None)
                if truck_id is not None:
                    provided_fields.append("TruckId")
                    provided_values["TruckId"] = truck_id
                    update_clauses.append('"TruckId" = EXCLUDED."TruckId"')
                
                # Only include TruckKey if it's provided (not None)
                if truck_key is not None:
                    provided_fields.append("TruckKey")
                    provided_values["TruckKey"] = truck_key
                    update_clauses.append('"TruckKey" = EXCLUDED."TruckKey"')
                
                # If no fields to update besides TruckUnit, still need to handle upsert
                if not update_clauses:
                    # Just insert if not exists, do nothing on duplicate
                    sql = """
                        INSERT INTO truck_mapping ("TruckUnit")
                        VALUES (:TruckUnit)
                        ON CONFLICT ("TruckUnit") DO NOTHING
                    """
                else:
                    # Build the dynamic SQL with updates - quote column names for PostgreSQL
                    fields_str = ", ".join([f'"{field}"' for field in provided_fields])
                    values_str = ", ".join([f":{field}" for field in provided_fields])
                    update_str = ", ".join(update_clauses)
                    
                    sql = f"""
                        INSERT INTO truck_mapping ({fields_str})
                        VALUES ({values_str})
                        ON CONFLICT ("TruckUnit") DO UPDATE SET {update_str}
                    """
                
                session.execute(text(sql), provided_values)
                session.commit()
                
                # Return the updated/inserted truck mapping
                return cls.get_by_truck_unit(truck_unit)
                
            except Exception as err:
                logger.error(f'Database upsert error: {err}', exc_info=True)
                session.rollback()
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
    TruckKey: Optional[str] = None


class TruckMappingUpdate(SQLModel):
    """Schema for updating a truck mapping"""
    TruckId: Optional[int] = None
    TruckKey: Optional[str] = None