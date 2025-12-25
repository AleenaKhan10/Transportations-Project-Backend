from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Union
import uuid

# Make sure the import path matches your project structure
from models.department_rules import DepartmentRules

router = APIRouter(prefix="/department_rules", tags=["department_rules"])

# =====================================================================
# 1. RESPONSE SCHEMAS (DTOs)
# =====================================================================

class RuleItemResponse(BaseModel):
    """
    Represents a single rule sent to Frontend.
    'configuration' is always a LIST of objects to support dynamic UI generation.
    """
    id: uuid.UUID
    rule_key: Optional[str]
    rule_name: str
    rule_type: Optional[str]
    
    # RESPONSE CHANGE:
    # Always returning a List of Dictionaries. 
    # Example: [ {key: 'fuel', threshold: 30}, {key: 'speed', threshold: 40} ]
    configuration: List[Dict[str, Any]] = []
    
    enabled: bool

class DepartmentGroupResponse(BaseModel):
    """
    Represents a group of rules categorized by department.
    """
    department_name: str
    department_key: str
    rules: List[RuleItemResponse]

class UpdateRuleRequest(BaseModel):
    """
    Payload for updating a rule configuration.
    Expects a direct List of objects as per the new requirement.
    """
    department_key: str
    rule_key: str
    
    # REQUEST CHANGE:
    # Frontend sends the array directly: [ {...}, {...} ]
    configuration: List[Dict[str, Any]]

# =====================================================================
# 2. HELPER FUNCTIONS
# =====================================================================

def format_department_name(key: str) -> str:
    """
    Converts keys like 'dispatch_reports' to 'Dispatch Reports'.
    """
    return key.replace("_", " ").title()

# =====================================================================
# 3. GET ENDPOINT - FETCH, UNWRAP & GROUP
# =====================================================================

@router.get("/", response_model=List[DepartmentGroupResponse])
def get_department_rules_grouped():
    """
    Fetches rules and ensures 'configuration' is always a clean List.
    Handles legacy data formats (Wrapper Objects vs Arrays).
    """
    try:
        # 1. Fetch raw data from DB
        raw_records = DepartmentRules.get_all_rules()
        grouped_data = {}

        for record in raw_records:
            d_key = record.department_key

            # 2. Initialize Department Group if needed
            if d_key not in grouped_data:
                grouped_data[d_key] = {
                    "department_name": format_department_name(d_key),
                    "department_key": d_key,
                    "rules": []
                }

            # ====================================================
            # DATA NORMALIZATION LOGIC (The "Un-wrapping")
            # ====================================================
            raw_config = record.configuration
            final_config_list = []

            if raw_config is None:
                # Case 1: Null in DB -> Return empty list
                final_config_list = []
                
            elif isinstance(raw_config, dict) and "values" in raw_config:
                # Case 2: Wrapped Object { "values": [...] } -> Extract the list
                final_config_list = raw_config["values"]
                
            elif isinstance(raw_config, list):
                # Case 3: Already an Array [...] -> Use as is
                final_config_list = raw_config
                
            elif isinstance(raw_config, dict):
                # Case 4: Single Object without wrapper -> Wrap in list
                final_config_list = [raw_config]

            # 3. Create the Rule Object
            rule_obj = {
                "id": record.id,
                "rule_key": record.rule_key,
                "rule_name": record.rule_name,
                "rule_type": record.rule_type,
                "configuration": final_config_list, # Normalized List
                "enabled": record.enabled
            }

            grouped_data[d_key]["rules"].append(rule_obj)

        # 4. Return List of Groups
        return list(grouped_data.values())

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error fetching rules: {str(e)}"
        )

# =====================================================================
# 4. PUT ENDPOINT - UPDATE CONFIGURATION
# =====================================================================

@router.put("/update", response_model=dict)
def update_rule_configuration(payload: UpdateRuleRequest):
    """
    Updates the rule configuration.
    Accepts a List[Dict] and saves it directly to the JSONB column.
    """
    try:
        # Calling Model method to update DB
        updated_record = DepartmentRules.update_rule_config(
            department_key=payload.department_key,
            rule_key=payload.rule_key,
            new_config=payload.configuration 
        )

        if not updated_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Rule not found: {payload.rule_key}"
            )

        return {
            "message": "Rule configuration updated successfully",
            "department": payload.department_key,
            "rule": payload.rule_key,
            "new_configuration": payload.configuration
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error updating rule: {str(e)}"
        )
        

# Response Schema
class DepartmentStatusResponse(BaseModel):
    department_key: str
    is_active: bool

# Endpoint
@router.get("/status/{department_key}", response_model=DepartmentStatusResponse)
def check_department_status(department_key: str):
    """
    Checks if the department has any active rules.
    """
    try:
        # Model function call
        status_bool = DepartmentRules.is_department_enabled(department_key)
        
        return {
            "department_key": department_key,
            "is_active": status_bool
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))