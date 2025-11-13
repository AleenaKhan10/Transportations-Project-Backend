from fastapi import APIRouter, HTTPException, status
from sqlmodel import Session, select
from datetime import datetime
from db import engine
from models.driver_model_prompt import DriverPrompts
from typing import Optional
from pydantic import BaseModel
from uuid import UUID

router = APIRouter(prefix="/driver-prompts", tags=["Driver Prompts Service"])


# -------------------------------
# Request body model for update
# -------------------------------
class UpdateDriverPromptRequest(BaseModel):
    prompt_name: str
    condition_true_prompt: Optional[str] = None
    condition_false_prompt: Optional[str] = None
    
class SystemPromptPayload(BaseModel):
    prompt_name: str
# -------------------------------
# GET ALL PROMPTS
# -------------------------------
@router.get("/")
async def get_all_prompts():
    with Session(engine) as session:
        prompts = session.exec(select(DriverPrompts)).all()
        return {"message": "All prompts fetched successfully", "data": prompts}

# -------------------------------
# GET PROMPT BY NAME
# -------------------------------
@router.get("/{prompt_name}")
async def get_prompt_by_name(prompt_name: str):
    with Session(engine) as session:
        prompt = session.exec(select(DriverPrompts).where(DriverPrompts.prompt_name == prompt_name)).first()
        if not prompt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
        return {"message": "Prompt fetched successfully", "data": prompt}


@router.put("/update-prompt")
async def update_prompt(request: UpdateDriverPromptRequest):
    with Session(engine) as session:
        # Find prompt by name from JSON body
        prompt = session.exec(
            select(DriverPrompts).where(DriverPrompts.prompt_name == request.prompt_name)
        ).first()

        if not prompt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
        
        # Update only if provided
        if request.condition_true_prompt is not None:
            prompt.condition_true_prompt = request.condition_true_prompt
        if request.condition_false_prompt is not None:
            prompt.condition_false_prompt = request.condition_false_prompt
        
        # Update last_modified timestamp
        prompt.last_modified = datetime.utcnow()
        session.add(prompt)
        session.commit()
        session.refresh(prompt)
        
        return {"message": "Prompt updated successfully", "data": prompt}



# # -------------------------------
# # UPDATE TRUE/FALSE PROMPTS PROMPT NAME IN PARAMS (JSON BODY)
# # -------------------------------
# @router.put("/{prompt_name}")
# async def update_prompt(prompt_name: str, request: UpdateDriverPromptRequest):
#     with Session(engine) as session:
#         prompt = session.exec(select(DriverPrompts).where(DriverPrompts.prompt_name == prompt_name)).first()
#         if not prompt:
#             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
        
#         # Update only if provided
#         if request.condition_true_prompt is not None:
#             prompt.condition_true_prompt = request.condition_true_prompt
#         if request.condition_false_prompt is not None:
#             prompt.condition_false_prompt = request.condition_false_prompt
        
#         # Update last_modified timestamp
#         prompt.last_modified = datetime.utcnow()
#         session.add(prompt)
#         session.commit()
#         session.refresh(prompt)
        
#         return {"message": "Prompt updated successfully", "data": prompt}
    
