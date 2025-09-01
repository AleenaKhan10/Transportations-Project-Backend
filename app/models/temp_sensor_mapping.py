from typing import Optional, List
from sqlmodel import SQLModel, Field, Session, select, text
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
    def upsert(cls, sensor_name: str, sensor_id: Optional[int] = None) -> Optional["TempSensorMapping"]:
        """Upsert a temp sensor mapping (insert or update if exists) - only updates provided fields"""
        logger.info(f'Upserting temp sensor mapping for name: {sensor_name}')
        
        with cls.get_session() as session:
            try:
                # Build dynamic SQL based on provided fields
                provided_fields = ["TempSensorNAME"]
                provided_values = {"TempSensorNAME": sensor_name}
                update_clauses = []
                
                # Only include TempSensorID if it's provided (not None)
                if sensor_id is not None:
                    provided_fields.append("TempSensorID")
                    provided_values["TempSensorID"] = sensor_id
                    update_clauses.append('"TempSensorID" = EXCLUDED."TempSensorID"')
                
                # If no fields to update besides TempSensorNAME, still need to handle upsert
                if not update_clauses:
                    # Just insert if not exists, do nothing on duplicate
                    sql = """
                        INSERT INTO temp_sensor_mapping ("TempSensorNAME")
                        VALUES (:TempSensorNAME)
                        ON CONFLICT ("TempSensorNAME") DO NOTHING
                    """
                else:
                    # Build the dynamic SQL with updates - quote column names for PostgreSQL
                    fields_str = ", ".join([f'"{field}"' for field in provided_fields])
                    values_str = ", ".join([f":{field}" for field in provided_fields])
                    update_str = ", ".join(update_clauses)
                    
                    sql = f"""
                        INSERT INTO temp_sensor_mapping ({fields_str})
                        VALUES ({values_str})
                        ON CONFLICT ("TempSensorNAME") DO UPDATE SET {update_str}
                    """
                
                session.execute(text(sql), provided_values)
                session.commit()
                
                # Return the updated/inserted temp sensor mapping
                return cls.get_by_sensor_name(sensor_name)
                
            except Exception as err:
                logger.error(f'Database upsert error: {err}', exc_info=True)
                session.rollback()
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