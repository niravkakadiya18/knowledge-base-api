
from typing import List, Optional
from pydantic import BaseModel, EmailStr

# --- Login ---
class LoginRequest(BaseModel):
    email: str
    password: str

class OrganisationDTO(BaseModel):
    id: str
    name: str

class UserDTO(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: str
    organisation: Optional[str] = None
    organisations: List[OrganisationDTO] = []
    lastSelectedOrgId: Optional[str] = None

class LoginResponse(BaseModel):
    token: str
    user: UserDTO

# --- Password Reset ---
class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    password: str
    confirmPassword: str

class SetPasswordRequest(BaseModel):
    userId: Optional[int] = None
    token: Optional[str] = None
    password: str

# --- Token Refresh ---
class RefreshTokenRequest(BaseModel):
    refreshToken: str

class RefreshTokenResponse(BaseModel):
    token: str
    refreshToken: str
    expiresIn: int

# --- Common ---
class SuccessResponse(BaseModel):
    success: bool
    message: str
