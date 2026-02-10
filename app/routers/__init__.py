
from fastapi import APIRouter

from app.routers import auth, users, stakeholders, knowledge

router = APIRouter()

router.include_router(auth.router)
router.include_router(users.router)
router.include_router(stakeholders.router)
router.include_router(knowledge.router)
