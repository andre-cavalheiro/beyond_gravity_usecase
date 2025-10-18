from fastapi import APIRouter


from fury_api.domain import paths
from fury_api.domain.health_check.controllers import health_router
from fury_api.domain.organizations.controllers import organization_router
from fury_api.domain.users.controllers import user_router
from fury_api.domain.earthquakes.controllers import earthquake_router

__all__ = ["create_router"]


def create_router() -> APIRouter:
    router = APIRouter(prefix=paths.API_ROOT)

    router.include_router(health_router, tags=["Health Check"])
    router.include_router(organization_router, tags=["Organizations"])
    router.include_router(user_router, tags=["Users"])
    router.include_router(earthquake_router, tags=["Earthquakes"])

    return router
