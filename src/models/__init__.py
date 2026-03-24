"""
SQLAlchemy model registry.

Importing all models here ensures Alembic's ``env.py`` can discover every
table by doing ``from src.models import *``.
"""

from src.models.activity import Activity
from src.models.base import Base
from src.models.company import Company
from src.models.contact import Contact
from src.models.deal import Deal
from src.models.organization import Organization
from src.models.pipeline_stage import PipelineStage
from src.models.user import User

__all__ = [
    "Base",
    "Organization",
    "User",
    "Company",
    "Contact",
    "PipelineStage",
    "Deal",
    "Activity",
]
