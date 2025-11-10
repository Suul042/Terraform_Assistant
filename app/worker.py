"""
Celery Worker Configuration for Background Tasks
"""
import logging
from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure

from app.core.config import get_settings

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Celery application
celery_app = Celery(
    "terraform_assistant",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=['app.tasks']
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)


# Task signals
@task_prerun.connect
def task_prerun_handler(task_id, task, *args, **kwargs):
    """Log task start"""
    logger.info(f"Task {task.name} [{task_id}] started")


@task_postrun.connect
def task_postrun_handler(task_id, task, *args, **kwargs):
    """Log task completion"""
    logger.info(f"Task {task.name} [{task_id}] completed")


@task_failure.connect
def task_failure_handler(task_id, exception, *args, **kwargs):
    """Log task failure"""
    logger.error(f"Task [{task_id}] failed: {exception}")


# Celery tasks
@celery_app.task(name="app.worker.sync_documentation")
def sync_documentation_task(provider: str):
    """
    Sync documentation for a cloud provider

    Args:
        provider: Cloud provider (aws, azure, gcp)

    Returns:
        Sync result
    """
    try:
        logger.info(f"Starting documentation sync for {provider}")
        from app.services.documentation_sync import DocumentationSyncService

        sync_service = DocumentationSyncService()
        result = sync_service.sync_provider(provider)

        logger.info(f"Documentation sync completed for {provider}")
        return {
            "status": "success",
            "provider": provider,
            "resources_synced": result.get("resources_synced", 0)
        }

    except Exception as e:
        logger.error(f"Documentation sync failed for {provider}: {e}")
        return {
            "status": "failed",
            "provider": provider,
            "error": str(e)
        }


@celery_app.task(name="app.worker.generate_code_async")
def generate_code_async_task(
    provider: str,
    resource_type: str,
    parameters: dict
):
    """
    Generate Terraform code asynchronously

    Args:
        provider: Cloud provider
        resource_type: Resource type
        parameters: Generation parameters

    Returns:
        Generated code
    """
    try:
        logger.info(f"Starting async code generation: {provider}/{resource_type}")
        from app.services.code_generation import CodeGenerationService
        from app.services.ai_service import AIService
        from app.services.cache_service import CacheService

        ai_service = AIService(api_key=settings.OPENAI_API_KEY)
        cache_service = CacheService(redis_url=settings.REDIS_URL)
        code_gen_service = CodeGenerationService(
            ai_service=ai_service,
            cache_service=cache_service
        )

        result = code_gen_service.generate_code_sync(
            provider=provider,
            resource_type=resource_type,
            parameters=parameters
        )

        logger.info(f"Async code generation completed: {provider}/{resource_type}")
        return {
            "status": "success",
            "code": result["code"],
            "metadata": result.get("metadata", {})
        }

    except Exception as e:
        logger.error(f"Async code generation failed: {e}")
        return {
            "status": "failed",
            "error": str(e)
        }


@celery_app.task(name="app.worker.validate_code_async")
def validate_code_async_task(code: str, provider: str):
    """
    Validate Terraform code asynchronously

    Args:
        code: Terraform code to validate
        provider: Cloud provider

    Returns:
        Validation result
    """
    try:
        logger.info(f"Starting async code validation for {provider}")

        # TODO: Implement actual validation logic
        # For now, return a simple result
        issues = []

        if not code.strip():
            issues.append({
                "severity": "error",
                "line": 0,
                "message": "Code is empty"
            })

        logger.info(f"Async code validation completed")
        return {
            "status": "success",
            "valid": len(issues) == 0,
            "issues": issues
        }

    except Exception as e:
        logger.error(f"Async code validation failed: {e}")
        return {
            "status": "failed",
            "error": str(e)
        }


@celery_app.task(name="app.worker.cleanup_old_cache")
def cleanup_old_cache_task():
    """
    Cleanup old cache entries

    This task should be run periodically to remove stale cache entries.

    Returns:
        Cleanup result
    """
    try:
        logger.info("Starting cache cleanup")
        from app.services.cache_service import CacheService

        cache_service = CacheService(redis_url=settings.REDIS_URL)
        # TODO: Implement actual cleanup logic

        logger.info("Cache cleanup completed")
        return {
            "status": "success",
            "items_removed": 0
        }

    except Exception as e:
        logger.error(f"Cache cleanup failed: {e}")
        return {
            "status": "failed",
            "error": str(e)
        }


# Periodic tasks (if celery-beat is enabled)
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    'sync-documentation-daily': {
        'task': 'app.worker.sync_documentation',
        'schedule': crontab(hour=2, minute=0),  # Run at 2:00 AM UTC daily
        'args': ('aws',)
    },
    'cleanup-cache-hourly': {
        'task': 'app.worker.cleanup_old_cache',
        'schedule': crontab(minute=0),  # Run every hour
    },
}


if __name__ == '__main__':
    celery_app.start()
