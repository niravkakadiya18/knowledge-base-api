
from typing import List, Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime

class UserBase(BaseModel):
    fullName: Optional[str] = None
    email: EmailStr
    role: Optional[str] = "viewer"
    organisationIds: List[int] = []
    status: Optional[str] = "enabled"

class CreateUserRequest(BaseModel):
    fullName: str
    email: EmailStr
    username: str
    password: str
    role: str = "viewer"
    organisationIds: List[int] = []
    status: str = "enabled"

class UpdateUserRequest(BaseModel):
    fullName: Optional[str] = None
    role: Optional[str] = None
    organisationIds: Optional[List[int]] = None
    status: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    fullName: str
    username: str
    email: EmailStr
    role: str
    organisations: List[dict] # {id, name}
    status: str
    lastLoginDate: Optional[datetime] = None
    createdAt: Optional[datetime] = None

class UserListResponse(BaseModel):
    data: List[UserResponse]
    total: int
    page: int
    limit: int
    totalPages: int
