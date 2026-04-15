from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


PlatformType = Literal["google_ads", "meta_ads"]
IntegrationStatus = Literal["connected", "disconnected", "error", "pending_account_select"]


class IntegrationCreate(BaseModel):
    client_id: str
    platform: PlatformType
    account_id: Optional[str] = None
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    status: IntegrationStatus = "connected"


class IntegrationUpdate(BaseModel):
    account_id: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    status: Optional[IntegrationStatus] = None
    last_sync_at: Optional[datetime] = None
    sync_error: Optional[str] = None


class IntegrationResponse(BaseModel):
    id: str
    client_id: str
    platform: PlatformType
    account_id: Optional[str]
    status: IntegrationStatus
    has_access_token: bool
    has_refresh_token: bool
    expires_at: Optional[datetime]
    last_sync_at: Optional[datetime]
    sync_error: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class IntegrationSyncResponse(BaseModel):
    integration_id: str
    platform: PlatformType
    synced_campaigns: int
    last_sync_at: datetime
