from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Union
import uuid

# Make sure the import path matches your project structure
from models.department_rules import DepartmentRules

router = APIRouter(prefix="/department_rules", tags=["department_rules"])

# =====================================================================
# 1. RESPONSE SCHEMAS
# =====================================================================

class RuleItemResponse(BaseModel):
    id: uuid.UUID
    rule_key: Optional[str]
    rule_name: str
    rule_type: Optional[str]
    # Always returning a List of Dictionaries for Frontend
    configuration: List[Dict[str, Any]] = [] 
    enabled: bool

class DepartmentGroupResponse(BaseModel):
    department_name: str
    department_key: str
    rules: List[RuleItemResponse]

class DepartmentStatusResponse(BaseModel):
    department_key: str
    is_active: bool

# =====================================================================
# 2. REQUEST SCHEMAS (Single & Bulk)
# =====================================================================

# A. Single Update Request
class UpdateRuleRequest(BaseModel):
    department_key: str
    rule_key: str
    configuration: List[Dict[str, Any]]

# B. Bulk Update Schemas (New Requirement)
class BulkRuleUpdateItem(BaseModel):
    id: Optional[uuid.UUID] = None
    rule_key: str
    rule_name: Optional[str] = None
    rule_type: Optional[str] = None
    enabled: bool  # We need to update this
    configuration: List[Dict[str, Any]] = [] # We need to update this

class BulkDepartmentItem(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    rules: List[BulkRuleUpdateItem]

# The Root Payload: Keys are department names (Dynamic)
BulkUpdatePayload = Dict[str, BulkDepartmentItem]

# =====================================================================
# 3. HELPER FUNCTIONS
# =====================================================================

def format_department_name(key: str) -> str:
    return key.replace("_", " ").title()

# =====================================================================
# 4. GET ENDPOINT - FETCH & UNWRAP
# =====================================================================


@router.get("/", response_model=List[DepartmentGroupResponse])
def get_department_rules_grouped():
    try:
        raw_records = DepartmentRules.get_all_rules()
        grouped_data = {}

        for record in raw_records:
            d_key = record.department_key

            if d_key not in grouped_data:
                grouped_data[d_key] = {
                    "department_name": format_department_name(d_key),
                    "department_key": d_key,
                    "rules": []
                }

            # --- NORMALIZATION LOGIC ---
            raw_config = record.configuration
            final_config_list = []

            if raw_config is None:
                final_config_list = []
            elif isinstance(raw_config, dict) and "values" in raw_config:
                final_config_list = raw_config["values"]
            elif isinstance(raw_config, list):
                final_config_list = raw_config
            elif isinstance(raw_config, dict):
                final_config_list = [raw_config]

            rule_obj = {
                "id": record.id,
                "rule_key": record.rule_key,
                "rule_name": record.rule_name,
                "rule_type": record.rule_type,
                "configuration": final_config_list,
                "enabled": record.enabled
            }

            grouped_data[d_key]["rules"].append(rule_obj)

        return list(grouped_data.values())

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error fetching rules: {str(e)}"
        )

# =====================================================================
# 5. SINGLE PUT ENDPOINT
# =====================================================================

@router.put("/update", response_model=dict)
def update_rule_configuration(payload: UpdateRuleRequest):
    try:
        updated_record = DepartmentRules.update_rule_config(
            department_key=payload.department_key,
            rule_key=payload.rule_key,
            new_config=payload.configuration 
        )

        if not updated_record:
            raise HTTPException(status_code=404, detail=f"Rule not found: {payload.rule_key}")

        return {
            "message": "Rule updated successfully",
            "new_configuration": payload.configuration
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================================
# 6. BULK PUT ENDPOINT 
# =====================================================================


@router.put("/bulk_update", response_model=dict)
def bulk_update_rules(payload: BulkUpdatePayload):
    """
    Updates multiple departments and rules in a single API call.
    Parses the nested dictionary structure provided by frontend.
    """
    try:
        updated_count = 0
        not_found_list = []

        # 1. Loop through Departments (key = "dispatch_reports", value = object)
        for dept_key, dept_data in payload.items():
            
            # 2. Loop through Rules in that Department
            for rule_item in dept_data.rules:
                
                # 3. Update DB
                success = DepartmentRules.update_rule_generic(
                    department_key=dept_key,
                    rule_key=rule_item.rule_key,
                    new_config=rule_item.configuration,
                    is_enabled=rule_item.enabled
                )

                if success:
                    updated_count += 1
                else:
                    not_found_list.append(f"{dept_key}:{rule_item.rule_key}")

        return {
            "message": "Bulk configuration updated",
            "total_updated": updated_count,
            "failed_records": not_found_list
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bulk update failed: {str(e)}")

# =====================================================================
# 7. STATUS ENDPOINT
# =====================================================================

@router.get("/status/{department_key}", response_model=DepartmentStatusResponse)
def check_department_status(department_key: str):
    try:
        status_bool = DepartmentRules.is_department_enabled(department_key)
        return {
            "department_key": department_key,
            "is_active": status_bool
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))