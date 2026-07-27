from fastapi import APIRouter, Depends
from server.auth import get_optional_user
from server.models.user_model import PreferencesModel
from server.services.user_service import update_user_preferences
from server.auth import get_current_user
router = APIRouter()

@router.post("/preferences")
async def update_preferences(data: PreferencesModel, current_user=Depends(get_current_user)):
    return await update_user_preferences(data, current_user)
@router.get("/preferences")
async def get_preferences(current_user=Depends(get_current_user)):
    return {"preferences": current_user.get("preferences", [])}
