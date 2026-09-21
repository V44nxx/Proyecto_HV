"""
Pipeline step protocol and base classes.
"""

from abc import ABC, abstractmethod
import structlog

from app.infrastructure.extraction.pipeline_context import ProcessingContext

logger = structlog.get_logger(__name__)


class PipelineStep(ABC):
    """
    Abstract base class for all extraction pipeline steps.
    Each step performs a focused transformation on the ProcessingContext.
    """

    @property
    @abstractmethod
    def step_name(self) -> str:
        """Name of the pipeline step."""
        ...

    @abstractmethod
    async def execute(self, context: ProcessingContext) -> ProcessingContext:
        """
        Execute the step's logic. Returns the updated context.
        """
        ...

    async def rollback(self, context: ProcessingContext) -> None:
        """
        Compensating action executed if a downstream step fails.
        Default is no-op.
        """
        logger.info("pipeline_step_rollback_noop", step=self.step_name, doc=str(context.document_id))
