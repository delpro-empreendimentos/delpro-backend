"""This module sets up the API v1 routes."""

from fastapi import APIRouter

from delpro_backend.routes.v1.documents_router import documents_router
from delpro_backend.routes.v1.images_router import images_router
from delpro_backend.routes.v1.evaluate_router import test_router
from delpro_backend.routes.v1.whatsapp_router import whatsapp_router

router = APIRouter()
router.include_router(test_router)
router.include_router(documents_router)
router.include_router(images_router)
router.include_router(whatsapp_router)
