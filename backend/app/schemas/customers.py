from pydantic import BaseModel


class CustomerOut(BaseModel):
    id: str
    email: str
    name: str
    avatarInitials: str
    emailVerified: bool
    isActive: bool
    createdAt: str  # ISO 8601


class CustomerStatusRequest(BaseModel):
    isActive: bool


class CustomerStatsOut(BaseModel):
    totalCount: int
