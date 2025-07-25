from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime, timezone

class UserCreate(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=255, description="Unique user identifier")

class UserResponse(BaseModel):
    user_id: str = Field(..., description="Unique user identifier")
    created_at: datetime = Field(..., description="User creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = ConfigDict(from_attributes=True)

class UserUpdate(BaseModel):
    pass