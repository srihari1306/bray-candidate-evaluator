"""
Azure AD authentication using fastapi-azure-auth.
"""

from fastapi import Depends, HTTPException, status
from typing import Optional

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger("auth")


class MockUser:
    """Mock user for development without Azure AD."""
    def __init__(self):
        self.name = "Dev User"
        self.preferred_username = "dev@example.com"
        self.roles = ["Recruiter", "Admin"]
        self.oid = "mock-user-id"
        self.claims = {"name": self.name, "preferred_username": self.preferred_username}


async def get_current_user():
    """
    Get the current authenticated user.
    In mock mode, returns a mock user.
    In production, validates Azure AD JWT token.
    """
    settings = get_settings()

    if settings.MOCK_MODE:
        return MockUser()

    # Production Azure AD validation
    # This would use fastapi-azure-auth:
    #
    # from fastapi_azure_auth import SingleTenantAzureAuthorizationCodeBearer
    #
    # azure_scheme = SingleTenantAzureAuthorizationCodeBearer(
    #     app_client_id=settings.AZURE_CLIENT_ID,
    #     tenant_id=settings.AZURE_TENANT_ID,
    #     scopes={f"api://{settings.AZURE_CLIENT_ID}/access_as_user": "Access API"},
    # )
    #
    # Then use as dependency: user = Depends(azure_scheme)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Azure AD not configured. Set MOCK_MODE=true for development.",
    )


def require_role(required_role: str):
    """Dependency to require a specific role."""
    async def check_role(user=Depends(get_current_user)):
        if hasattr(user, "roles") and required_role in user.roles:
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{required_role}' required",
        )
    return check_role
