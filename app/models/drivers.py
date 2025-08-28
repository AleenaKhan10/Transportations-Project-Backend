from typing import List, Optional

from sqlmodel import SQLModel, Field, Session, select, text
from pydantic import BaseModel

from db import engine
from helpers import logger


class Driver(SQLModel, table=True):
    __tablename__ = "driversdirectory"
    
    driverId: str = Field(primary_key=True)
    status: Optional[str] = None
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    truckId: Optional[str] = None
    phoneNumber: Optional[str] = None
    email: Optional[str] = None
    hiredOn: Optional[str] = None
    updatedOn: Optional[str] = None
    companyId: Optional[str] = None
    dispatcher: Optional[str] = None
    firstLanguage: Optional[str] = None
    secondLanguage: Optional[str] = None
    globalDnd: Optional[bool] = None
    safetyCall: Optional[bool] = None
    safetyMessage: Optional[bool] = None
    hosSupport: Optional[bool] = None
    maintainanceCall: Optional[bool] = None
    maintainanceMessage: Optional[bool] = None
    dispatchCall: Optional[bool] = None
    dispatchMessage: Optional[bool] = None
    accountCall: Optional[bool] = None
    accountMessage: Optional[bool] = None
    telegramId: Optional[str] = None

    
    @classmethod
    def get_session(cls) -> Session:
        """Create a database session"""
        return Session(engine)
    
    @classmethod
    def get_all(cls, limit: int = 5000) -> List["Driver"]:
        """Get all drivers from the database"""
        logger.info('GetAllDriversData request reach out to correct service')
        
        with cls.get_session() as session:
            try:
                statement = select(cls).limit(limit)
                drivers = session.exec(statement).all()
                return list(drivers)
                
            except Exception as err:
                logger.error(f'Database query error: {err}', exc_info=True)
                return []
    
    # @classmethod
    # def get_all_raw(cls, limit: int = 5000) -> List[Dict[str, Any]]:
    #     """Get all drivers data as raw dictionary format"""
    #     logger.info('GetAllDriversData raw request reach out to correct service')
        
    #     with cls.get_session() as session:
    #         try:
    #             result = session.exec(text(
    #                 f"SELECT * FROM dev.drivers LIMIT {limit};"
    #             ))
                
    #             columns = result.keys()
    #             data = [dict(zip(columns, row)) for row in result.fetchall()]
    #             return data
                
    #         except Exception as err:
    #             logger.error(f'Database query error: {err}', exc_info=True)
    #             return []
    
    @classmethod
    def get_by_id(cls, driver_id: str) -> Optional["Driver"]:
        """Get a driver by ID"""
        with cls.get_session() as session:
            try:
                statement = select(cls).where(cls.driverId == driver_id)
                return session.exec(statement).first()
                
            except Exception as err:
                logger.error(f'Database query error: {err}', exc_info=True)
                return None
    
    @classmethod
    def get_by_ids(cls, driver_ids: List[str]) -> List["Driver"]:
        """Get multiple drivers by their IDs in a single query"""
        with cls.get_session() as session:
            try:
                statement = select(cls).where(cls.driverId.in_(driver_ids))
                return list(session.exec(statement).all())
                
            except Exception as err:
                logger.error(f'Database query error: {err}', exc_info=True)
                return []
    
    @classmethod
    def upsert(cls, driver_data: "DriverCallUpdate") -> Optional["Driver"]:
        """Upsert a single driver (insert or update if exists) - only updates provided fields"""
        logger.info(f'Upserting driver with ID: {driver_data.driverId}')
        
        with cls.get_session() as session:
            try:
                # Build dynamic SQL based on provided fields
                provided_fields = []
                provided_values = {}
                update_clauses = []
                
                # Always include driverId
                provided_fields.append("driverId")
                provided_values["driverId"] = driver_data.driverId
                
                # Check each field and only include if it's not None
                field_mappings = {
                    "status": driver_data.status,
                    "firstName": driver_data.firstName,
                    "lastName": driver_data.lastName,
                    "truckId": driver_data.truckId,
                    "phoneNumber": driver_data.phoneNumber,
                    "email": driver_data.email,
                    "hiredOn": driver_data.hiredOn,
                    "updatedOn": driver_data.updatedOn,
                    "companyId": driver_data.companyId,
                    "dispatcher": driver_data.dispatcher,
                    "firstLanguage": driver_data.firstLanguage,
                    "secondLanguage": driver_data.secondLanguage,
                    "globalDnd": driver_data.globalDnd,
                    "safetyCall": driver_data.safetyCall,
                    "safetyMessage": driver_data.safetyMessage,
                    "hosSupport": driver_data.hosSupport,
                    "maintainanceCall": driver_data.maintainanceCall,
                    "maintainanceMessage": driver_data.maintainanceMessage,
                    "dispatchCall": driver_data.dispatchCall,
                    "dispatchMessage": driver_data.dispatchMessage,
                    "accountCall": driver_data.accountCall,
                    "accountMessage": driver_data.accountMessage,
                    "telegramId": driver_data.telegramId
                }
                
                for field_name, field_value in field_mappings.items():
                    if field_value is not None:
                        provided_fields.append(field_name)
                        provided_values[field_name] = field_value
                        update_clauses.append(f"{field_name} = EXCLUDED.{field_name}")
                
                # Build the dynamic SQL
                fields_str = ", ".join(provided_fields)
                values_str = ", ".join([f":{field}" for field in provided_fields])
                update_str = ", ".join(update_clauses)
                
                sql = f"""
                    INSERT INTO driversdirectory ({fields_str})
                    VALUES ({values_str})
                    ON CONFLICT ("driverId") DO UPDATE SET {update_str}
                """
                
                session.execute(text(sql), provided_values)
                session.commit()
                
                # Return the updated/inserted driver
                return cls.get_by_id(driver_data.driverId)
                
            except Exception as err:
                logger.error(f'Database upsert error: {err}', exc_info=True)
                session.rollback()
                return None

    @classmethod
    def bulk_upsert(cls, drivers_data: List["DriverCallUpdate"]) -> List["Driver"]:
        """Bulk upsert multiple drivers - only updates provided fields"""
        logger.info(f'Bulk upserting {len(drivers_data)} drivers')
        
        with cls.get_session() as session:
            try:
                for driver_data in drivers_data:
                    # Use the single upsert method for each driver to maintain consistency
                    cls._execute_single_upsert(session, driver_data)
                
                session.commit()
                
                # Get all upserted drivers
                driver_ids = [d.driverId for d in drivers_data if d.driverId]
                if driver_ids:
                    return cls.get_by_ids(driver_ids)
                
                return []
                
            except Exception as err:
                logger.error(f'Database bulk upsert error: {err}', exc_info=True)
                session.rollback()
                return []
    
    @classmethod
    def _execute_single_upsert(cls, session, driver_data: "DriverCallUpdate"):
        """Helper method to execute a single upsert within an existing session"""
        # Build dynamic SQL based on provided fields
        provided_fields = []
        provided_values = {}
        update_clauses = []
        
        # Always include driverId
        provided_fields.append("driverId")
        provided_values["driverId"] = driver_data.driverId
        
        # Check each field and only include if it's not None
        field_mappings = {
            "status": driver_data.status,
            "firstName": driver_data.firstName,
            "lastName": driver_data.lastName,
            "truckId": driver_data.truckId,
            "phoneNumber": driver_data.phoneNumber,
            "email": driver_data.email,
            "hiredOn": driver_data.hiredOn,
            "updatedOn": driver_data.updatedOn,
            "companyId": driver_data.companyId,
            "dispatcher": driver_data.dispatcher,
            "firstLanguage": driver_data.firstLanguage,
            "secondLanguage": driver_data.secondLanguage,
            "globalDnd": driver_data.globalDnd,
            "safetyCall": driver_data.safetyCall,
            "safetyMessage": driver_data.safetyMessage,
            "hosSupport": driver_data.hosSupport,
            "maintainanceCall": driver_data.maintainanceCall,
            "maintainanceMessage": driver_data.maintainanceMessage,
            "dispatchCall": driver_data.dispatchCall,
            "dispatchMessage": driver_data.dispatchMessage,
            "accountCall": driver_data.accountCall,
            "accountMessage": driver_data.accountMessage,
            "telegramId": driver_data.telegramId
        }
        
        for field_name, field_value in field_mappings.items():
            if field_value is not None:
                provided_fields.append(field_name)
                provided_values[field_name] = field_value
                update_clauses.append(f"{field_name} = EXCLUDED.{field_name}")
        
        # Build the dynamic SQL
        fields_str = ", ".join(provided_fields)
        values_str = ", ".join([f":{field}" for field in provided_fields])
        update_str = ", ".join(update_clauses)
        
        sql = f"""
            INSERT INTO driversdirectory ({fields_str})
            VALUES ({values_str})
            ON CONFLICT ("driverId") DO UPDATE SET {update_str}
        """
        
        session.execute(text(sql), provided_values)

    @classmethod
    def bulk_update_calling_info(cls, updates: List["DriverCallUpdate"]) -> None:
        """Bulk update driver calling information"""
        logger.info('setDriverCalling request reach out to correct service')
        
        with cls.get_session() as session:
            try:
                for driver_update in updates:
                    session.execute(
                        text("""
                            INSERT INTO driversdirectory (
                                "driverId", "updatedOn", "safetyMessage", status, "companyId", "hosSupport",
                                "firstName", dispatcher, "maintainanceCall", "lastName", "firstLanguage",
                                "maintainanceMessage", "truckId", "secondLanguage", "dispatchCall", "phoneNumber",
                                "globalDnd", "dispatchMessage", email, "safetyCall", "accountCall", "hiredOn", "accountMessage", "telegramId"
                            )
                            VALUES (
                                :driverId, :updatedOn, :safetyMessage, :status, :companyId, :hosSupport,
                                :firstName, :dispatcher, :maintainanceCall, :lastName, :firstLanguage,
                                :maintainanceMessage, :truckId, :secondLanguage, :dispatchCall, :phoneNumber,
                                :globalDnd, :dispatchMessage, :email, :safetyCall, :accountCall, :hiredOn, :accountMessage, :telegramId
                            )
                            ON CONFLICT ("driverId") DO UPDATE SET
                                "updatedOn" = COALESCE(EXCLUDED."updatedOn", driversdirectory."updatedOn"),
                                "safetyMessage" = COALESCE(EXCLUDED."safetyMessage", driversdirectory."safetyMessage"),
                                status = COALESCE(EXCLUDED.status, driversdirectory.status),
                                "companyId" = COALESCE(EXCLUDED."companyId", driversdirectory."companyId"),
                                "hosSupport" = COALESCE(EXCLUDED."hosSupport", driversdirectory."hosSupport"),
                                "firstName" = COALESCE(EXCLUDED."firstName", driversdirectory."firstName"),
                                dispatcher = COALESCE(EXCLUDED.dispatcher, driversdirectory.dispatcher),
                                "maintainanceCall" = COALESCE(EXCLUDED."maintainanceCall", driversdirectory."maintainanceCall"),
                                "lastName" = COALESCE(EXCLUDED."lastName", driversdirectory."lastName"),
                                "firstLanguage" = COALESCE(EXCLUDED."firstLanguage", driversdirectory."firstLanguage"),
                                "maintainanceMessage" = COALESCE(EXCLUDED."maintainanceMessage", driversdirectory."maintainanceMessage"),
                                "truckId" = COALESCE(EXCLUDED."truckId", driversdirectory."truckId"),
                                "secondLanguage" = COALESCE(EXCLUDED."secondLanguage", driversdirectory."secondLanguage"),
                                "dispatchCall" = COALESCE(EXCLUDED."dispatchCall", driversdirectory."dispatchCall"),
                                "phoneNumber" = COALESCE(EXCLUDED."phoneNumber", driversdirectory."phoneNumber"),
                                "globalDnd" = COALESCE(EXCLUDED."globalDnd", driversdirectory."globalDnd"),
                                "dispatchMessage" = COALESCE(EXCLUDED."dispatchMessage", driversdirectory."dispatchMessage"),
                                email = COALESCE(EXCLUDED.email, driversdirectory.email),
                                "safetyCall" = COALESCE(EXCLUDED."safetyCall", driversdirectory."safetyCall"),
                                "accountCall" = COALESCE(EXCLUDED."accountCall", driversdirectory."accountCall"),
                                "hiredOn" = COALESCE(EXCLUDED."hiredOn", driversdirectory."hiredOn"),
                                "accountMessage" = COALESCE(EXCLUDED."accountMessage", driversdirectory."accountMessage"),
                                "telegramId" = COALESCE(EXCLUDED."telegramId", driversdirectory."telegramId")
                            """),
                        {
                            "driverId": driver_update.driverId,
                            "updatedOn": driver_update.updatedOn,
                            "safetyMessage": driver_update.safetyMessage,
                            "status": driver_update.status,
                            "companyId": driver_update.companyId,
                            "hosSupport": driver_update.hosSupport,
                            "firstName": driver_update.firstName,
                            "dispatcher": driver_update.dispatcher,
                            "maintainanceCall": driver_update.maintainanceCall,
                            "lastName": driver_update.lastName,
                            "firstLanguage": driver_update.firstLanguage,
                            "maintainanceMessage": driver_update.maintainanceMessage,
                            "truckId": driver_update.truckId,
                            "secondLanguage": driver_update.secondLanguage,
                            "dispatchCall": driver_update.dispatchCall,
                            "phoneNumber": driver_update.phoneNumber,
                            "globalDnd": driver_update.globalDnd,
                            "dispatchMessage": driver_update.dispatchMessage,
                            "email": driver_update.email,
                            "safetyCall": driver_update.safetyCall,
                            "accountCall": driver_update.accountCall,
                            "hiredOn": driver_update.hiredOn,
                            "accountMessage": driver_update.accountMessage,
                            "telegramId": driver_update.telegramId
                        }
                    )
                
                session.commit()
                
            except Exception as err:
                logger.error(f'Database query error: {err}', exc_info=True)
                session.rollback()
                raise
    
    # def update_calling_info(self, calling_info: str) -> bool:
    #     """Update this driver's calling information"""
    #     logger.info(f'Updating driver {self.driverId} calling information')
        
    #     with self.get_session() as session:
    #         try:
    #             # Attach this instance to the session
    #             session.add(self)
    #             self.driverCallingInfor = calling_info
    #             session.commit()
    #             session.refresh(self)
    #             return True
                
    #         except Exception as err:
    #             logger.error(f'Database query error: {err}', exc_info=True)
    #             session.rollback()
    #             return False
    
    # def save(self) -> bool:
    #     """Save or update this driver in the database"""
    #     with self.get_session() as session:
    #         try:
    #             session.add(self)
    #             session.commit()
    #             session.refresh(self)
    #             return True
                
    #         except Exception as err:
    #             logger.error(f'Database query error: {err}', exc_info=True)
    #             session.rollback()
    #             return False
    
    # def delete(self) -> bool:
    #     """Delete this driver from the database"""
    #     with self.get_session() as session:
    #         try:
    #             session.delete(self)
    #             session.commit()
    #             return True
                
    #         except Exception as err:
    #             logger.error(f'Database query error: {err}', exc_info=True)
    #             session.rollback()
    #             return False
    
    # def to_structured_response(self) -> "DriverResponse":
    #     """Convert this driver to a structured response format"""    
    #     # Create structured response with bounds checking
    #     return DriverResponse(
    #         driverId=self.driverId,
    #         status=self.status,
    #         firstName=self.firstName,
    #         lastName=self.lastName,
    #         truckId=self.truckId,
    #         phoneNumber=self.phoneNumber,
    #         email=self.email,
    #         hiredOn=self.hiredOn,
    #         updatedOn=self.updatedOn,
    #         companyId=self.companyId,
    #         dispatcher=self.dispatcher,
    #         firstLanguage=self.firstLanguage,
    #         secondLanguage=self.secondLanguage,
    #         globalDnd=self.globalDnd,
    #         safetyCall=self.safetyCall,
    #         safetyMessage=self.safetyMessage,
    #         hosSupport=self.hosSupport,
    #         maintainanceCall=self.maintainanceCall,
    #         maintainanceMessage=self.maintainanceMessage,
    #         dispatchCall=self.dispatchCall,
    #         dispatchMessage=self.dispatchMessage,
    #         accountCall=self.accountCall,
    #         accountMessage=self.accountMessage,
    #     )
    
    # @classmethod
    # def get_all_structured(cls, limit: int = 5000) -> List["DriverResponse"]:
    #     """Get all drivers as structured response format"""
    #     logger.info('GetAllDriversDataJson request reach out to correct service')
        
    #     drivers = cls.get_all(limit)
    #     return [driver.to_structured_response() for driver in drivers]


class DriverResponse(SQLModel):
    """Response model for cleaned driver data"""
    driverId: Optional[str] = None
    status: Optional[str] = None
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    truckId: Optional[str] = None
    phoneNumber: Optional[str] = None
    email: Optional[str] = None
    hiredOn: Optional[str] = None
    updatedOn: Optional[str] = None
    companyId: Optional[str] = None
    dispatcher: Optional[str] = None
    firstLanguage: Optional[str] = None
    secondLanguage: Optional[str] = None
    globalDnd: Optional[bool] = None
    safetyCall: Optional[bool] = None
    safetyMessage: Optional[bool] = None
    hosSupport: Optional[bool] = None
    maintainanceCall: Optional[bool] = None
    maintainanceMessage: Optional[bool] = None
    dispatchCall: Optional[bool] = None
    dispatchMessage: Optional[bool] = None
    accountCall: Optional[bool] = None
    accountMessage: Optional[bool] = None
    telegramId: Optional[str] = None
    
    # def to_dict(self) -> Dict[str, Any]:
    #     """Convert to dictionary"""
    #     return self.model_dump()
    
    # @classmethod
    # def from_driver(cls, driver: Driver) -> "DriverResponse":
    #     """Create DriverResponse from Driver instance"""
    #     return driver.to_structured_response()


class DriverCallUpdate(SQLModel):
    """Model for driver call updates"""
    driverId: Optional[str] = None
    status: Optional[str] = None
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    truckId: Optional[str] = None
    phoneNumber: Optional[str] = None
    email: Optional[str] = None
    hiredOn: Optional[str] = None
    updatedOn: Optional[str] = None
    companyId: Optional[str] = None
    dispatcher: Optional[str] = None
    firstLanguage: Optional[str] = None
    secondLanguage: Optional[str] = None
    globalDnd: Optional[bool] = None
    safetyCall: Optional[bool] = None
    safetyMessage: Optional[bool] = None
    hosSupport: Optional[bool] = None
    maintainanceCall: Optional[bool] = None
    maintainanceMessage: Optional[bool] = None
    dispatchCall: Optional[bool] = None
    dispatchMessage: Optional[bool] = None
    accountCall: Optional[bool] = None
    accountMessage: Optional[bool] = None
    telegramId: Optional[str] = None

    
    # def apply_to_driver(self, driver: Driver) -> Driver:
    #     """Apply this update to a driver instance"""
    #     driver.driverCallingInfor = self.driverCallingInfor
    #     return driver

#     @classmethod
#     def create_batch(
#         cls, updates: List[Dict[str, str] | "DriverCallUpdate"]
#     ) -> List["DriverCallUpdate"]:
#         """Create a batch of DriverCallUpdate instances"""
#         return [
#             cls(**update) if isinstance(update, dict) else update
#             for update in updates
#             if isinstance(update, (dict, cls))
#         ]


class CreateDriverRequest(BaseModel):
    firstName: str
    lastName: str
    phoneNumber: str
    status: str = "Active"
    truckId: str = None
    email: str = None
    hiredOn: str = None
    companyId: str = "COMP_001"
    dispatcher: str = None
    firstLanguage: str = "English"
    secondLanguage: str = None
    globalDnd: bool = False
    safetyCall: bool = True
    safetyMessage: bool = True
    hosSupport: bool = True
    maintainanceCall: bool = True
    maintainanceMessage: bool = True
    dispatchCall: bool = True
    dispatchMessage: bool = True
    accountCall: bool = True
    accountMessage: bool = True
    telegramId: str = None
