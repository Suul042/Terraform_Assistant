"""
Custom exceptions for Terraform Assistant
"""


class TerraformAssistantError(Exception):
    """Base exception for Terraform Assistant"""
    pass


class DatabaseError(TerraformAssistantError):
    """Database related errors"""
    pass


class CodeGenerationError(TerraformAssistantError):
    """Code generation related errors"""
    pass


class TemplateNotFoundError(CodeGenerationError):
    """Template not found error"""
    pass


class AIServiceError(TerraformAssistantError):
    """AI service related errors"""
    pass


class CacheError(TerraformAssistantError):
    """Cache related errors"""
    pass


class ValidationError(TerraformAssistantError):
    """Validation related errors"""
    pass


class DocumentationSyncError(TerraformAssistantError):
    """Documentation sync related errors"""
    pass


class AuthenticationError(TerraformAssistantError):
    """Authentication related errors"""
    pass


class AuthorizationError(TerraformAssistantError):
    """Authorization related errors"""
    pass


class RateLimitError(TerraformAssistantError):
    """Rate limiting related errors"""
    pass


class ConfigurationError(TerraformAssistantError):
    """Configuration related errors"""
    pass