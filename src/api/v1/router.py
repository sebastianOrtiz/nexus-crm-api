"""
API v1 root router.

All feature routers are registered here under the ``/api/v1`` prefix.
Adding a new feature only requires importing its router and calling
``v1_router.include_router()``.
"""

from fastapi import APIRouter

from src.api.v1.routers.activities import router as activities_router
from src.api.v1.routers.auth import router as auth_router
from src.api.v1.routers.companies import router as companies_router
from src.api.v1.routers.contacts import router as contacts_router
from src.api.v1.routers.dashboard import router as dashboard_router
from src.api.v1.routers.deals import router as deals_router
from src.api.v1.routers.events import router as events_router
from src.api.v1.routers.organization import router as organization_router
from src.api.v1.routers.pipeline_stages import router as pipeline_stages_router
from src.api.v1.routers.search import router as search_router
from src.api.v1.routers.users import router as users_router

v1_router = APIRouter(prefix="/api/v1")

v1_router.include_router(auth_router)
v1_router.include_router(organization_router)
v1_router.include_router(users_router)
v1_router.include_router(contacts_router)
v1_router.include_router(companies_router)
v1_router.include_router(pipeline_stages_router)
v1_router.include_router(deals_router)
v1_router.include_router(activities_router)
v1_router.include_router(dashboard_router)
v1_router.include_router(events_router)
v1_router.include_router(search_router)
