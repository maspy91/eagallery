from pydantic import BaseModel, EmailStr, Field


# ---- Requests ----

class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)
    turnstile_token: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=100)
    turnstile_token: str | None = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=100)


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class StaffInviteRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr


class AcceptInviteRequest(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=100)


# ---- Responses ----

class UserOut(BaseModel):
    # camelCase to match the frontend's AppUser type (src/lib/types.ts)
    # exactly, so the SvelteKit store can drop the response straight into
    # `currentUser` with no field remapping.
    id: str
    email: str
    name: str
    role: str
    avatarInitials: str
    emailVerified: bool


class MessageResponse(BaseModel):
    message: str
