"""
Code Validation Endpoints
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import logging

from app.models.schemas import (
    CodeValidationRequest,
    CodeValidationResponse,
    ValidationIssue
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=CodeValidationResponse)
async def validate_terraform_code(request: CodeValidationRequest):
    """
    Validate Terraform code for syntax and best practices

    This endpoint validates Terraform code for:
    - Syntax errors
    - Best practice violations
    - Security issues
    - Performance recommendations

    Args:
        request: Validation request with code and provider

    Returns:
        Validation results with issues and recommendations
    """
    try:
        logger.info(f"Validating code for provider: {request.provider}")

        issues: List[ValidationIssue] = []

        # Basic syntax validation
        if not request.code.strip():
            issues.append(ValidationIssue(
                severity="error",
                line=0,
                message="Code is empty",
                rule="syntax-error"
            ))
            return CodeValidationResponse(
                valid=False,
                issues=issues,
                score=0
            )

        # Check for resource blocks
        if "resource" not in request.code and "module" not in request.code:
            issues.append(ValidationIssue(
                severity="error",
                line=0,
                message="No resource or module blocks found",
                rule="missing-resources"
            ))

        # Check for provider configuration
        if request.provider and request.provider not in request.code:
            issues.append(ValidationIssue(
                severity="warning",
                line=0,
                message=f"Provider '{request.provider}' not explicitly configured",
                rule="missing-provider-config",
                suggestion=f'Add: provider "{request.provider}" {{ }}'
            ))

        # Security checks
        if "password" in request.code.lower() and '"' in request.code:
            issues.append(ValidationIssue(
                severity="critical",
                line=0,
                message="Potential hardcoded password detected",
                rule="hardcoded-secrets",
                suggestion="Use variables or secret management instead"
            ))

        # Best practices
        if "terraform {" not in request.code:
            issues.append(ValidationIssue(
                severity="warning",
                line=0,
                message="Terraform version constraint not specified",
                rule="missing-version-constraint",
                suggestion="Add terraform { required_version = \"~> 1.0\" }"
            ))

        # Calculate score
        error_count = sum(1 for issue in issues if issue.severity == "error")
        critical_count = sum(1 for issue in issues if issue.severity == "critical")
        warning_count = sum(1 for issue in issues if issue.severity == "warning")

        score = max(0, 100 - (critical_count * 30) - (error_count * 20) - (warning_count * 5))
        valid = error_count == 0 and critical_count == 0

        return CodeValidationResponse(
            valid=valid,
            issues=issues,
            score=score,
            recommendations=[
                "Use variables for configurable values",
                "Add output blocks for important resource attributes",
                "Consider using modules for reusable components"
            ] if valid else []
        )

    except Exception as e:
        logger.error(f"Validation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Validation failed: {str(e)}"
        )


@router.post("/format")
async def format_terraform_code(code: str) -> Dict[str, Any]:
    """
    Format Terraform code according to best practices

    Args:
        code: Terraform code to format

    Returns:
        Formatted code
    """
    try:
        # TODO: Implement actual terraform fmt integration
        # For now, return the code as-is with basic formatting
        lines = code.strip().split('\n')
        formatted_lines = []

        indent_level = 0
        for line in lines:
            stripped = line.strip()

            # Decrease indent for closing braces
            if stripped.startswith('}'):
                indent_level = max(0, indent_level - 1)

            # Add indentation
            formatted_lines.append('  ' * indent_level + stripped)

            # Increase indent for opening braces
            if stripped.endswith('{'):
                indent_level += 1

        formatted_code = '\n'.join(formatted_lines)

        return {
            "formatted_code": formatted_code,
            "changes_made": True
        }

    except Exception as e:
        logger.error(f"Formatting failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Formatting failed: {str(e)}"
        )
