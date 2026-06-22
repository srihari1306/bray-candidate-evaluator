
from fastapi import Depends, HTTPException, status
from fastapi_azure_auth import SingleTenantAzureAuthorizationCodeBearer

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger("auth")

# Initialize lazily to avoid startup crash if env vars are missing
def get_azure_scheme():
    settings = get_settings()
    return SingleTenantAzureAuthorizationCodeBearer(
        app_client_id=settings.AZURE_CLIENT_ID or "unconfigured-client-id",
        tenant_id=settings.AZURE_TENANT_ID or "unconfigured-tenant-id",
        scopes={f"api://{settings.AZURE_CLIENT_ID}/access_as_user": "Access API"},
    )

async def get_current_user(user=Depends(get_azure_scheme())):
    """
    Get the current authenticated user.
    Validates Azure AD JWT token.
    """
    settings = get_settings()
    
    if not settings.AZURE_CLIENT_ID or settings.AZURE_CLIENT_ID == "your-client-id":
        logger.warning("Azure AD not configured. Returning mock admin user.")
        return {
            "oid": "mock-admin-id",
            "name": "Mock Admin",
            "preferred_username": "admin@mock.local",
            "roles": ["Admin", "Recruiter"],
        }
    
    return user

def require_role(required_role: str):
    """Dependency to require a specific role."""
    async def check_role(user=Depends(get_current_user)):
        roles = getattr(user, "roles", []) or user.get("roles", []) if isinstance(user, dict) else getattr(user, "claims", {}).get("roles", [])
        if required_role in roles:
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{required_role}' required",
        )
    return check_role
