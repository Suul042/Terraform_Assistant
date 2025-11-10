"""
Pydantic models for API request/response serialization
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, validator


class CloudProvider(str, Enum):
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"


class TerraformAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    IMPORT = "import"


class TemplateType(str, Enum):
    MAIN = "main"
    VARIABLES = "variables"
    OUTPUTS = "outputs"
    MODULE = "module"


# Request Models
class PerformanceRequirements(BaseModel):
    """Performance requirements for generated infrastructure"""
    max_response_time_ms: Optional[int] = Field(None, description="Maximum response time in milliseconds")
    throughput_rps: Optional[int] = Field(None, description="Required throughput in requests per second")
    availability_percentage: Optional[float] = Field(None, ge=0, le=100, description="Required availability percentage")


class SecurityRequirements(BaseModel):
    """Security requirements for generated infrastructure"""
    encryption_at_rest: bool = Field(True, description="Require encryption at rest")
    encryption_in_transit: bool = Field(True, description="Require encryption in transit")
    compliance_standards: Optional[List[str]] = Field(None, description="Required compliance standards")
    access_control: Optional[str] = Field(None, description="Access control requirements")


class CostConstraints(BaseModel):
    """Cost constraints for generated infrastructure"""
    max_monthly_cost: Optional[float] = Field(None, ge=0, description="Maximum monthly cost")
    cost_optimization_level: Optional[str] = Field("balanced", description="Cost optimization level")
    preferred_instance_types: Optional[List[str]] = Field(None, description="Preferred instance types")


class ComplianceRequirements(BaseModel):
    """Compliance requirements"""
    required_standards: Optional[List[str]] = Field(None, description="Required compliance standards")
    data_residency: Optional[str] = Field(None, description="Data residency requirements")
    audit_logging: bool = Field(True, description="Require audit logging")


class InfrastructureContext(BaseModel):
    """Existing infrastructure context"""
    existing_resources: Optional[Dict[str, Any]] = Field(None, description="Existing resources")
    network_configuration: Optional[Dict[str, Any]] = Field(None, description="Network configuration")
    security_groups: Optional[List[str]] = Field(None, description="Existing security groups")


class OrganizationStandards(BaseModel):
    """Organization-specific standards"""
    naming_convention: Optional[str] = Field(None, description="Naming convention pattern")
    required_tags: Optional[Dict[str, str]] = Field(None, description="Required tags")
    approved_regions: Optional[List[str]] = Field(None, description="Approved regions")


class GenerationRequest(BaseModel):
    """Request for code generation"""
    provider: CloudProvider = Field(..., description="Cloud provider")
    resource_type: str = Field(..., description="Terraform resource type")
    action: TerraformAction = Field(TerraformAction.CREATE, description="Terraform action")
    
    # Enhanced inputs
    natural_language_request: Optional[str] = Field(None, description="Natural language description")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Resource parameters")
    
    # Requirements
    requirements: Dict[str, Any] = Field(default_factory=dict, description="Requirements")
    
    # Context
    existing_infrastructure: Optional[InfrastructureContext] = Field(None, description="Existing infrastructure")
    team_standards: Optional[OrganizationStandards] = Field(None, description="Team standards")
    deployment_environment: Optional[str] = Field("dev", description="Deployment environment")
    
    # Output preferences
    output_format: List[TemplateType] = Field(default=[TemplateType.MAIN], description="Output formats")
    include_comments: bool = Field(True, description="Include comments in generated code")
    
    @validator('resource_type')
    def validate_resource_type(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('resource_type cannot be empty')
        return v.strip()


class GeneratedCode(BaseModel):
    """Generated Terraform code"""
    main: Optional[str] = Field(None, description="Main Terraform configuration")
    variables: Optional[str] = Field(None, description="Variables configuration")
    outputs: Optional[str] = Field(None, description="Outputs configuration")
    module: Optional[str] = Field(None, description="Module configuration")
    readme: Optional[str] = Field(None, description="README documentation")
    
    # Metadata
    generation_metadata: Dict[str, Any] = Field(default_factory=dict, description="Generation metadata")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations")
    warnings: List[str] = Field(default_factory=list, description="Warnings")


class ValidationResult(BaseModel):
    """Code validation result"""
    is_valid: bool = Field(..., description="Whether code is valid")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    suggestions: List[str] = Field(default_factory=list, description="Improvement suggestions")


class Suggestion(BaseModel):
    """AI suggestion for code improvement"""
    type: str = Field(..., description="Suggestion type")
    title: str = Field(..., description="Suggestion title")
    description: str = Field(..., description="Suggestion description")
    code_snippet: Optional[str] = Field(None, description="Code snippet")
    priority: str = Field("medium", description="Suggestion priority")


class CodeContext(BaseModel):
    """Context for code suggestions"""
    current_code: str = Field(..., description="Current code")
    cursor_position: Optional[int] = Field(None, description="Cursor position")
    provider: CloudProvider = Field(..., description="Cloud provider")
    resource_type: Optional[str] = Field(None, description="Resource type")


# Response Models
class CloudProviderResponse(BaseModel):
    """Cloud provider response"""
    id: int
    name: str
    display_name: str
    documentation_base_url: Optional[str]
    sync_status: str
    last_sync_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class ResourceTypeResponse(BaseModel):
    """Resource type response"""
    id: int
    resource_type: str
    category: Optional[str]
    subcategory: Optional[str]
    description: Optional[str]
    documentation_url: Optional[str]
    provider: CloudProviderResponse
    
    class Config:
        from_attributes = True


class ResourceParameterResponse(BaseModel):
    """Resource parameter response"""
    id: int
    parameter_name: str
    parameter_type: Optional[str]
    is_required: bool
    is_computed: bool
    default_value: Optional[str]
    description: Optional[str]
    example_value: Optional[str]
    validation_rules: Optional[Dict[str, Any]]
    
    class Config:
        from_attributes = True


class SmartTemplateResponse(BaseModel):
    """Smart template response"""
    id: int
    template_name: str
    template_type: str
    use_cases: Optional[Dict[str, Any]]
    complexity_score: int
    best_practices: Optional[Dict[str, Any]]
    
    class Config:
        from_attributes = True


class GenerationRequestResponse(BaseModel):
    """Generation request response"""
    id: UUID
    provider: str
    resource_type: str
    action: str
    status: str
    processing_time_ms: Optional[int]
    tokens_used: Optional[int]
    created_at: datetime
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class UserProjectResponse(BaseModel):
    """User project response"""
    id: UUID
    project_name: str
    description: Optional[str]
    default_provider: Optional[str]
    default_region: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Filter Models
class ResourceTypeFilter(BaseModel):
    """Filter for resource types"""
    provider: Optional[CloudProvider] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    search: Optional[str] = None


class TemplateFilter(BaseModel):
    """Filter for templates"""
    resource_type_id: Optional[int] = None
    template_type: Optional[TemplateType] = None
    complexity_score: Optional[int] = None
    search: Optional[str] = None


# API Response Wrapper
class APIResponse(BaseModel):
    """Standard API response wrapper"""
    success: bool = Field(..., description="Request success status")
    data: Optional[Any] = Field(None, description="Response data")
    error: Optional[Dict[str, Any]] = Field(None, description="Error details")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Response metadata")


# Project Models
class ProjectData(BaseModel):
    """Data for creating a project"""
    project_name: str = Field(..., description="Project name")
    description: Optional[str] = Field(None, description="Project description")
    default_provider: Optional[CloudProvider] = Field(None, description="Default provider")
    default_region: Optional[str] = Field(None, description="Default region")
    project_config: Optional[Dict[str, Any]] = Field(None, description="Project configuration")


class TemplateData(BaseModel):
    """Data for creating a template"""
    resource_type_id: int = Field(..., description="Resource type ID")
    template_name: str = Field(..., description="Template name")
    template_type: TemplateType = Field(..., description="Template type")
    template_content: str = Field(..., description="Template content")
    use_cases: Optional[Dict[str, Any]] = Field(None, description="Use cases")
    complexity_score: int = Field(1, ge=1, le=5, description="Complexity score")
    best_practices: Optional[Dict[str, Any]] = Field(None, description="Best practices")
    security_considerations: Optional[Dict[str, Any]] = Field(None, description="Security considerations")
    variables: Optional[Dict[str, Any]] = Field(None, description="Template variables")
    conditions: Optional[Dict[str, Any]] = Field(None, description="Template conditions")


# Additional Models for API Endpoints

class CodeGenerationRequest(BaseModel):
    """Request for code generation"""
    provider: str = Field(..., description="Cloud provider (aws, azure, gcp)")
    resource_type: str = Field(..., description="Resource type to generate")
    description: Optional[str] = Field(None, description="Natural language description")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Resource parameters")
    force_regenerate: bool = Field(False, description="Force regeneration, skip cache")


class CodeGenerationResponse(BaseModel):
    """Response for code generation"""
    code: str = Field(..., description="Generated Terraform code")
    provider: str = Field(..., description="Cloud provider")
    resource_type: str = Field(..., description="Resource type")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Generation metadata")
    cached: bool = Field(False, description="Whether result was cached")


class GenerationStatus(BaseModel):
    """Status of a generation job"""
    job_id: str = Field(..., description="Job identifier")
    status: str = Field(..., description="Job status (pending, running, completed, failed)")
    progress: int = Field(..., ge=0, le=100, description="Progress percentage")
    result: Optional[Dict[str, Any]] = Field(None, description="Result if completed")


class ValidationIssue(BaseModel):
    """A validation issue"""
    severity: str = Field(..., description="Issue severity (error, warning, info)")
    line: int = Field(..., description="Line number")
    message: str = Field(..., description="Issue message")
    rule: str = Field(..., description="Rule that was violated")
    suggestion: Optional[str] = Field(None, description="Suggested fix")


class CodeValidationRequest(BaseModel):
    """Request for code validation"""
    code: str = Field(..., description="Terraform code to validate")
    provider: Optional[str] = Field(None, description="Cloud provider")


class CodeValidationResponse(BaseModel):
    """Response for code validation"""
    valid: bool = Field(..., description="Whether code is valid")
    issues: List[ValidationIssue] = Field(default_factory=list, description="Validation issues")
    score: int = Field(..., ge=0, le=100, description="Code quality score")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations")


class TemplateResponse(BaseModel):
    """Template response"""
    id: str = Field(..., description="Template ID")
    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    provider: str = Field(..., description="Cloud provider")
    category: str = Field(..., description="Template category")
    code: str = Field(..., description="Template code")
    variables: Dict[str, Any] = Field(default_factory=dict, description="Template variables")
    tags: List[str] = Field(default_factory=list, description="Template tags")


class TemplateListResponse(BaseModel):
    """List of templates response"""
    templates: List[Dict[str, Any]] = Field(..., description="List of templates")
    total: int = Field(..., description="Total number of templates")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Page size")


class TemplateCreateRequest(BaseModel):
    """Request to create a template"""
    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    provider: str = Field(..., description="Cloud provider")
    category: str = Field(..., description="Template category")
    code: str = Field(..., description="Template code")
    variables: Optional[Dict[str, Any]] = Field(None, description="Template variables")
    tags: Optional[List[str]] = Field(None, description="Template tags")