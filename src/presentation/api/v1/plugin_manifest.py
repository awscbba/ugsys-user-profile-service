"""Plugin manifest endpoint — static JSON, presentation layer only."""

from fastapi import APIRouter

router = APIRouter(tags=["Plugin Manifest"])


@router.get("/plugin-manifest.json")
async def get_plugin_manifest() -> dict[str, object]:
    """Return the static plugin manifest for ugsys-user-profile-service."""
    return {
        "name": "user-profile-service",
        "version": "0.1.0",
        "entryPoint": "https://profiles.apps.cloud.org.bo/assets/index-DS4a0gmi.js",
        "healthEndpoint": "/health",
        "routes": [
            {
                "path": "/app/user-profile-service/users",
                "label": "Users",
                "requiredRoles": ["admin", "super_admin"],
            }
        ],
        "navigation": [
            {
                "label": "Users",
                "icon": "👤",
                "path": "/app/user-profile-service/users",
                "group": "Users",
                "order": 1,
                "requiredRoles": ["admin", "super_admin"],
            }
        ],
    }
