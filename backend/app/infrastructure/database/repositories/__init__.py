"""
Database repositories package.
"""

from app.infrastructure.database.repositories.dashboard_repository import DashboardRepository
from app.infrastructure.database.repositories.document_repository import DocumentRepository
from app.infrastructure.database.repositories.person_repository import PersonRepository
from app.infrastructure.database.repositories.review_repository import ReviewRepository
from app.infrastructure.database.repositories.search_repository import SearchRepository
from app.infrastructure.database.repositories.user_repository import UserRepository

__all__ = [
    "UserRepository",
    "DocumentRepository",
    "PersonRepository",
    "ReviewRepository",
    "SearchRepository",
    "DashboardRepository",
]
