from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional, Union, Any
from models.department_rules import DepartmentRules
import uuid

router = APIRouter(prefix="/department_rules", tags=["department_rules"])

# =====================================================================
# RESPONSE SCHEMAS (The Transformation Layer)
# =====================================================================

# 1. Single Rule Item (Frontend needs a generic 'value' field)
class RuleItemResponse(BaseModel):
    id: uuid.UUID
    rule_key: str
    rule_name: str
    rule_type: str 
    # Logic: 'value' can be a number OR a boolean.
    # Frontend will read this single field instead of checking two columns.
    value: Union[float, bool, int, None] 
    
    # NEW FIELD
    unit: Optional[str] = None  # Frontend ko milega: "Minutes" ya "Hours"
    
    enabled: bool

# 2. Grouped Department (The Box on UI)
class DepartmentGroupResponse(BaseModel):
    department_name: str  # Display Name (Derived from key)
    department_key: str   # Logic Key
    rules: List[RuleItemResponse]
    

# 3. Update Request Body
class UpdateRuleRequest(BaseModel):
    department_key: str
    rule_key: str
    value: Union[float, bool, int] # The new value to save
    # NEW FIELD (Optional because boolean rules doesn't have any units)
    unit: Optional[str] = None

# =====================================================================
# HELPER: GROUPING LOGIC
# =====================================================================
def format_department_name(key: str) -> str:
    """
    Simple helper to make 'dispatch_reports' look like 'Dispatch Reports'
    """
    return key.replace("_", " ").title()

# =====================================================================
# GET ENDPOINT - FETCH & GROUP CONFIGURATION
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

            final_value = None
            if record.rule_type == 'number':
                final_value = record.threshold
            elif record.rule_type == 'boolean':
                final_value = record.boolean_value

            # --- FIX IS HERE ---
            rule_obj = {
                "id": record.id,
                "rule_key": record.rule_key,
                "rule_name": record.rule_name,
                "rule_type": record.rule_type,
                "value": final_value, 
                
                # Unit is added here
                "unit": record.unit,   # <--- Now it will fetch unit from DB
                
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
# PUT ENDPOINT: UPDATE CONFIG
# =====================================================================
@router.put("/update", response_model=dict)
def update_rule_configuration(payload: UpdateRuleRequest):
    """
    Updates a single rule's value. 
    The logic in the Model handles whether to save to 'threshold' or 'boolean_value'.
    """
    try:
        updated_record = DepartmentRules.update_rule_value(
            department_key=payload.department_key,
            rule_key=payload.rule_key,
            new_value=payload.value,
            new_unit=payload.unit  # <--- Pass unit from payload
        )

        if not updated_record:
            raise HTTPException(status_code=404, detail="Rule not found")

        return {"message": "Rule updated successfully", "new_value": payload.value}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))