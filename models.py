from pydantic import BaseModel, Field
from typing import Optional

class LeadCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150)
    phone: str = Field(..., min_length=7, max_length=30)
    course: Optional[str] = "Umumiy"
    source: Optional[str] = "Instagram Ads"
    ad_name: Optional[str] = "Joylinks Target"
    notes: Optional[str] = ""
    time_pref: Optional[str] = None
    level: Optional[str] = None
    branch: Optional[str] = None

class StatusUpdate(BaseModel):
    status: str
    assigned_to: Optional[str] = "Admin"
    note: Optional[str] = None
    trial_date: Optional[str] = None
    cancel_reason: Optional[str] = None

class NoteCreate(BaseModel):
    note: str
    author: Optional[str] = "Admin"

class SettingsPayload(BaseModel):
    bot_token: Optional[str] = ""
    telegram_group_id: Optional[str] = ""
    telegram_channel_url: Optional[str] = ""
    meta_pixel_id: Optional[str] = ""
    center_name: Optional[str] = "Joylinks"
