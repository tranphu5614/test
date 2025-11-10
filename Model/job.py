import datetime
from typing import List, Dict, Any
from pydantic import BaseModel, Field

class UploadResponse(BaseModel):
    uploadUrl: str = Field(..., alias="uploadUrl")

class CreateJobRequest(BaseModel):
    # For this mock, we'll simplify to a single URL
    audioUrls: List[str] = Field(..., alias="audioUrls")

class Job(BaseModel):
    id: str
    status: str
    createdAt: datetime.datetime = Field(..., alias="createdAt")
    completedAt: datetime.datetime | None = Field(None, alias="completedAt")
    results: List[Dict[str, Any]] | None = None
    error: str | None = None