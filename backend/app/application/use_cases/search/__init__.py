"""
Search use cases package.
"""

from app.application.use_cases.search.classify_candidate_profession import (
    ClassifyCandidateProfessionUseCase,
)
from app.application.use_cases.search.exceptions import (
    CandidateNotFoundError,
    SearchError,
)
from app.application.use_cases.search.get_candidate_detail import (
    GetCandidateDetailUseCase,
)
from app.application.use_cases.search.get_filter_options import (
    GetFilterOptionsUseCase,
)
from app.application.use_cases.search.get_search_facets import (
    GetSearchFacetsUseCase,
)
from app.application.use_cases.search.search_candidates import (
    SearchCandidatesUseCase,
)

__all__ = [
    "SearchCandidatesUseCase",
    "GetCandidateDetailUseCase",
    "GetSearchFacetsUseCase",
    "GetFilterOptionsUseCase",
    "ClassifyCandidateProfessionUseCase",
    "SearchError",
    "CandidateNotFoundError",
]
