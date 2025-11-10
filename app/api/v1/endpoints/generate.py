"""
Code Generation Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Optional, Dict, Any
import logging

from app.core.config import get_settings
from app.models.schemas import (
    CodeGenerationRequest,
    CodeGenerationResponse,
    GenerationStatus
)
from app.services.code_generation import CodeGenerationService
from app.services.ai_service import AIService
from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=CodeGenerationResponse)
async def generate_terraform_code(
    request: CodeGenerationRequest,
    background_tasks: BackgroundTasks,
    settings=Depends(get_settings)
):
    """
    Generate Terraform code based on requirements

    This endpoint accepts a natural language description and configuration
    parameters, then generates the corresponding Terraform code.

    Args:
        request: Code generation request with provider, resource type, and parameters
        background_tasks: FastAPI background tasks for async processing
        settings: Application settings

    Returns:
        Generated Terraform code with metadata

    Raises:
        HTTPException: If generation fails
    """
    try:
        logger.info(f"Generating code for provider: {request.provider}, "
                   f"resource: {request.resource_type}")

        # Initialize services
        ai_service = AIService(api_key=settings.OPENAI_API_KEY)
        cache_service = CacheService(redis_url=settings.REDIS_URL)
        code_gen_service = CodeGenerationService(
            ai_service=ai_service,
            cache_service=cache_service
        )

        # Check cache first
        cache_key = code_gen_service.generate_cache_key(request)
        cached_result = await cache_service.get(cache_key)

        if cached_result and not request.force_regenerate:
            logger.info("Returning cached result")
            return CodeGenerationResponse(
                code=cached_result["code"],
                provider=request.provider,
                resource_type=request.resource_type,
                metadata=cached_result.get("metadata", {}),
                cached=True
            )

        # Generate new code
        result = await code_gen_service.generate_code(request)

        # Cache the result in background
        background_tasks.add_task(
            cache_service.set,
            cache_key,
            result,
            ttl=settings.TEMPLATE_CACHE_TTL
        )

        return CodeGenerationResponse(
            code=result["code"],
            provider=request.provider,
            resource_type=request.resource_type,
            metadata=result.get("metadata", {}),
            cached=False
        )

    except Exception as e:
        logger.error(f"Code generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Code generation failed: {str(e)}"
        )


@router.post("/module", response_model=CodeGenerationResponse)
async def generate_terraform_module(
    module_name: str,
    module_type: str,
    description: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None,
    settings=Depends(get_settings)
):
    """
    Generate a complete Terraform module

    Args:
        module_name: Name of the module
        module_type: Type of module (vpc, ec2, s3, etc.)
        description: Optional description
        parameters: Module parameters

    Returns:
        Generated module code with file structure
    """
    try:
        logger.info(f"Generating module: {module_name} of type {module_type}")

        # Initialize services
        ai_service = AIService(api_key=settings.OPENAI_API_KEY)
        cache_service = CacheService(redis_url=settings.REDIS_URL)
        code_gen_service = CodeGenerationService(
            ai_service=ai_service,
            cache_service=cache_service
        )

        # Generate module
        result = await code_gen_service.generate_module(
            name=module_name,
            module_type=module_type,
            description=description,
            parameters=parameters or {}
        )

        return result

    except Exception as e:
        logger.error(f"Module generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Module generation failed: {str(e)}"
        )


@router.get("/status/{job_id}")
async def get_generation_status(job_id: str):
    """
    Get the status of a code generation job

    For long-running generation tasks, check the status using the job ID.

    Args:
        job_id: Unique job identifier

    Returns:
        Job status and result (if completed)
    """
    # TODO: Implement job status tracking with Celery
    return GenerationStatus(
        job_id=job_id,
        status="completed",
        progress=100,
        result=None
    )
