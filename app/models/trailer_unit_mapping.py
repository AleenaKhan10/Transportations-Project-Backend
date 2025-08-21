from typing import Optional, List
from sqlmodel import SQLModel, Field, Session, select, text
from db import engine
from helpers import logger


class TrailerUnitMapping(SQLModel, table=True):
    __tablename__ = "trailer_unit_mapping"
    
    TrailerUnit: str = Field(max_length=20, primary_key=True)
    TrailerID: Optional[int] = None
    
    @classmethod
    def get_session(cls) -> Session:
        """Create a database session"""
        return Session(engine)
    
    @classmethod
    def get_all(cls, limit: int = 5000) -> List["TrailerUnitMapping"]:
        """Get all trailer unit mappings from the database"""
        logger.info('GetAllTrailerUnitMappings request reached the service')
        
        with cls.get_session() as session:
            try:
                statement = select(cls).limit(limit)
                mappings = session.exec(statement).all()
                return list(mappings)
                
            except Exception as err:
                logger.error(f'Database query error: {err}', exc_info=True)
                return []
    
    @classmethod
    def get_by_trailer_unit(cls, trailer_unit: str) -> Optional["TrailerUnitMapping"]:
        """Get a trailer unit mapping by TrailerUnit"""
        with cls.get_session() as session:
            try:
                statement = select(cls).where(cls.TrailerUnit == trailer_unit)
                return session.exec(statement).first()
                
            except Exception as err:
                logger.error(f'Database query error: {err}', exc_info=True)
                return None
    
    @classmethod
    def get_by_trailer_id(cls, trailer_id: int) -> List["TrailerUnitMapping"]:
        """Get all trailer unit mappings by TrailerID"""
        with cls.get_session() as session:
            try:
                statement = select(cls).where(cls.TrailerID == trailer_id)
                mappings = session.exec(statement).all()
                return list(mappings)
                
            except Exception as err:
                logger.error(f'Database query error: {err}', exc_info=True)
                return []
    
    @classmethod
    def create(cls, trailer_unit: str, trailer_id: Optional[int] = None) -> Optional["TrailerUnitMapping"]:
        """Create a new trailer unit mapping"""
        with cls.get_session() as session:
            try:
                mapping = cls(TrailerUnit=trailer_unit, TrailerID=trailer_id)
                session.add(mapping)
                session.commit()
                session.refresh(mapping)
                return mapping
                
            except Exception as err:
                logger.error(f'Database insert error: {err}', exc_info=True)
                return None
    
    @classmethod
    def update(cls, trailer_unit: str, trailer_id: Optional[int] = None) -> Optional["TrailerUnitMapping"]:
        """Update an existing trailer unit mapping"""
        with cls.get_session() as session:
            try:
                statement = select(cls).where(cls.TrailerUnit == trailer_unit)
                mapping = session.exec(statement).first()
                
                if mapping:
                    mapping.TrailerID = trailer_id
                    session.add(mapping)
                    session.commit()
                    session.refresh(mapping)
                    return mapping
                return None
                
            except Exception as err:
                logger.error(f'Database update error: {err}', exc_info=True)
                return None
    
    @classmethod
    def upsert(cls, trailer_unit: str, trailer_id: Optional[int] = None) -> Optional["TrailerUnitMapping"]:
        """Upsert a trailer unit mapping (insert or update if exists) - only updates provided fields"""
        logger.info(f'Upserting trailer unit mapping for unit: {trailer_unit}')
        
        with cls.get_session() as session:
            try:
                # Build dynamic SQL based on provided fields
                provided_fields = ["TrailerUnit"]
                provided_values = {"TrailerUnit": trailer_unit}
                update_clauses = []
                
                # Only include TrailerID if it's provided (not None)
                if trailer_id is not None:
                    provided_fields.append("TrailerID")
                    provided_values["TrailerID"] = trailer_id
                    update_clauses.append("TrailerID = VALUES(TrailerID)")
                
                # If no fields to update besides TrailerUnit, still need to handle upsert
                if not update_clauses:
                    # Just insert if not exists, do nothing on duplicate
                    sql = """
                        INSERT IGNORE INTO trailer_unit_mapping (TrailerUnit)
                        VALUES (:TrailerUnit)
                    """
                else:
                    # Build the dynamic SQL with updates
                    fields_str = ", ".join(provided_fields)
                    values_str = ", ".join([f":{field}" for field in provided_fields])
                    update_str = ", ".join(update_clauses)
                    
                    sql = f"""
                        INSERT INTO trailer_unit_mapping ({fields_str})
                        VALUES ({values_str})
                        ON DUPLICATE KEY UPDATE {update_str}
                    """
                
                session.execute(text(sql), provided_values)
                session.commit()
                
                # Return the updated/inserted trailer unit mapping
                return cls.get_by_trailer_unit(trailer_unit)
                
            except Exception as err:
                logger.error(f'Database upsert error: {err}', exc_info=True)
                session.rollback()
                return None

    @classmethod
    def delete(cls, trailer_unit: str) -> bool:
        """Delete a trailer unit mapping"""
        with cls.get_session() as session:
            try:
                statement = select(cls).where(cls.TrailerUnit == trailer_unit)
                mapping = session.exec(statement).first()
                
                if mapping:
                    session.delete(mapping)
                    session.commit()
                    return True
                return False
                
            except Exception as err:
                logger.error(f'Database delete error: {err}', exc_info=True)
                return False


class TrailerUnitMappingCreate(SQLModel):
    """Schema for creating a trailer unit mapping"""
    TrailerUnit: str = Field(max_length=20)
    TrailerID: Optional[int] = None


class TrailerUnitMappingUpdate(SQLModel):
    """Schema for updating a trailer unit mapping"""
    TrailerID: Optional[int] = None