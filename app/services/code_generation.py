"""
Intelligent code generation engine for Terraform
"""
import hashlib
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from jinja2 import Environment, BaseLoader, TemplateError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.database import ResourceType, ResourceParameter, SmartTemplate, GenerationRequest
from app.models.schemas import (
    GenerationRequest as GenerationRequestSchema,
    GeneratedCode,
    InferredIntent,
    CodeContext
)
from app.services.ai_service import AIReasoningService
from app.services.cache_service import CacheService
from app.core.exceptions import CodeGenerationError, TemplateNotFoundError

logger = logging.getLogger(__name__)


class TemplateEngine:
    """Template engine for Terraform code generation"""
    
    def __init__(self, cache_service: CacheService):
        self.cache_service = cache_service
        self.jinja_env = Environment(loader=BaseLoader())
        
    async def render_template(self, template_content: str, variables: Dict[str, Any]) -> str:
        """Render Jinja2 template with variables"""
        try:
            template = self.jinja_env.from_string(template_content)
            return template.render(**variables)
        except TemplateError as e:
            raise CodeGenerationError(f"Template rendering error: {str(e)}")
    
    async def get_template(self, 
                          db: AsyncSession, 
                          resource_type_id: int, 
                          template_type: str) -> Optional[SmartTemplate]:
        """Get template from database with caching"""
        cache_key = f"template:{resource_type_id}:{template_type}"
        
        # Try cache first
        cached_template = await self.cache_service.get(cache_key)
        if cached_template:
            return cached_template
        
        # Query database
        result = await db.execute(
            select(SmartTemplate).where(
                SmartTemplate.resource_type_id == resource_type_id,
                SmartTemplate.template_type == template_type
            )
        )
        template = result.scalar_one_or_none()
        
        if template:
            await self.cache_service.set(cache_key, template, ttl=3600)
        
        return template
    
    async def generate_main_tf(self, 
                              db: AsyncSession,
                              resource_type: ResourceType,
                              variables: Dict[str, Any]) -> str:
        """Generate main.tf content"""
        template = await self.get_template(db, resource_type.id, "main")
        if not template:
            raise TemplateNotFoundError(f"Main template not found for {resource_type.resource_type}")
        
        return await self.render_template(template.template_content, variables)
    
    async def generate_variables_tf(self, 
                                   db: AsyncSession,
                                   resource_type: ResourceType,
                                   parameters: List[ResourceParameter]) -> str:
        """Generate variables.tf content"""
        template = await self.get_template(db, resource_type.id, "variables")
        if not template:
            # Generate default variables template
            return self._generate_default_variables(parameters)
        
        return await self.render_template(template.template_content, {"parameters": parameters})
    
    async def generate_outputs_tf(self, 
                                 db: AsyncSession,
                                 resource_type: ResourceType,
                                 outputs: List[Dict[str, Any]]) -> str:
        """Generate outputs.tf content"""
        template = await self.get_template(db, resource_type.id, "outputs")
        if not template:
            # Generate default outputs template
            return self._generate_default_outputs(outputs)
        
        return await self.render_template(template.template_content, {"outputs": outputs})
    
    def _generate_default_variables(self, parameters: List[ResourceParameter]) -> str:
        """Generate default variables.tf template"""
        variables = []
        for param in parameters:
            if param.is_required or param.default_value is not None:
                var_def = f'variable "{param.parameter_name}" {{\n'
                var_def += f'  description = "{param.description or param.parameter_name}"\n'
                var_def += f'  type        = {self._get_terraform_type(param.parameter_type)}\n'
                
                if param.default_value:
                    var_def += f'  default     = {param.default_value}\n'
                
                var_def += '}\n'
                variables.append(var_def)
        
        return '\n'.join(variables)
    
    def _generate_default_outputs(self, outputs: List[Dict[str, Any]]) -> str:
        """Generate default outputs.tf template"""
        output_defs = []
        for output in outputs:
            output_def = f'output "{output["name"]}" {{\n'
            output_def += f'  description = "{output.get("description", output["name"])}"\n'
            output_def += f'  value       = {output["value"]}\n'
            output_def += '}\n'
            output_defs.append(output_def)
        
        return '\n'.join(output_defs)
    
    def _get_terraform_type(self, param_type: str) -> str:
        """Convert parameter type to Terraform type"""
        type_mapping = {
            "string": "string",
            "number": "number",
            "boolean": "bool",
            "list": "list(string)",
            "map": "map(string)"
        }
        return type_mapping.get(param_type, "string")


class ContextAnalyzer:
    """Analyze generation context and requirements"""
    
    def __init__(self, cache_service: CacheService):
        self.cache_service = cache_service
    
    async def analyze(self, request: GenerationRequestSchema) -> Dict[str, Any]:
        """Analyze generation request context"""
        context = {
            "provider": request.provider,
            "resource_type": request.resource_type,
            "action": request.action,
            "environment": request.deployment_environment,
            "has_natural_language": bool(request.natural_language_request),
            "has_requirements": bool(request.requirements),
            "has_existing_infra": bool(request.existing_infrastructure),
            "has_team_standards": bool(request.team_standards),
            "complexity_score": self._calculate_complexity(request)
        }
        
        return context
    
    def _calculate_complexity(self, request: GenerationRequestSchema) -> int:
        """Calculate complexity score (1-5)"""
        score = 1
        
        if request.natural_language_request:
            score += 1
        
        if request.requirements:
            score += len(request.requirements) * 0.5
        
        if request.existing_infrastructure:
            score += 1
        
        if request.team_standards:
            score += 1
        
        return min(int(score), 5)


class IntelligentCodeGenerator:
    """Main intelligent code generation engine"""
    
    def __init__(self, 
                 ai_service: AIReasoningService,
                 template_engine: TemplateEngine,
                 context_analyzer: ContextAnalyzer,
                 cache_service: CacheService):
        self.ai_service = ai_service
        self.template_engine = template_engine
        self.context_analyzer = context_analyzer
        self.cache_service = cache_service
    
    async def generate_terraform_code(self, 
                                    db: AsyncSession,
                                    request: GenerationRequestSchema) -> GeneratedCode:
        """Generate Terraform code from request"""
        logger.info(f"Generating code for {request.provider}:{request.resource_type}")
        
        try:
            # 1. Analyze context
            context = await self.context_analyzer.analyze(request)
            
            # 2. Get resource type information
            resource_type = await self._get_resource_type(db, request.provider, request.resource_type)
            if not resource_type:
                raise CodeGenerationError(f"Resource type {request.resource_type} not found for {request.provider}")
            
            # 3. Get resource parameters
            parameters = await self._get_resource_parameters(db, resource_type.id)
            
            # 4. AI inference if natural language request
            intent = None
            if request.natural_language_request:
                intent = await self.ai_service.infer_intent(request, context)
            
            # 5. Analyze dependencies
            dependencies = await self._analyze_dependencies(db, resource_type, intent)
            
            # 6. Generate code structure
            variables = await self._prepare_variables(request, parameters, intent)
            
            # 7. Generate individual files
            generated_code = GeneratedCode()
            
            if "main" in request.output_format or not request.output_format:
                generated_code.main = await self.template_engine.generate_main_tf(
                    db, resource_type, variables
                )
            
            if "variables" in request.output_format:
                generated_code.variables = await self.template_engine.generate_variables_tf(
                    db, resource_type, parameters
                )
            
            if "outputs" in request.output_format:
                outputs = await self._generate_outputs(resource_type, variables)
                generated_code.outputs = await self.template_engine.generate_outputs_tf(
                    db, resource_type, outputs
                )
            
            # 8. Apply best practices
            generated_code = await self._apply_best_practices(generated_code, resource_type, context)
            
            # 9. Add metadata and recommendations
            generated_code.generation_metadata = {
                "generated_at": datetime.utcnow().isoformat(),
                "provider": request.provider,
                "resource_type": request.resource_type,
                "complexity_score": context["complexity_score"],
                "ai_enhanced": intent is not None
            }
            
            if intent:
                generated_code.recommendations = intent.recommendations
            
            logger.info(f"Successfully generated code for {request.provider}:{request.resource_type}")
            return generated_code
            
        except Exception as e:
            logger.error(f"Code generation failed: {str(e)}")
            raise CodeGenerationError(f"Code generation failed: {str(e)}")
    
    async def _get_resource_type(self, 
                                db: AsyncSession, 
                                provider: str, 
                                resource_type: str) -> Optional[ResourceType]:
        """Get resource type from database"""
        result = await db.execute(
            select(ResourceType)
            .join(ResourceType.provider)
            .where(
                ResourceType.resource_type == resource_type,
                ResourceType.provider.has(name=provider)
            )
        )
        return result.scalar_one_or_none()
    
    async def _get_resource_parameters(self, 
                                      db: AsyncSession, 
                                      resource_type_id: int) -> List[ResourceParameter]:
        """Get resource parameters from database"""
        result = await db.execute(
            select(ResourceParameter).where(
                ResourceParameter.resource_type_id == resource_type_id
            )
        )
        return result.scalars().all()
    
    async def _analyze_dependencies(self, 
                                   db: AsyncSession,
                                   resource_type: ResourceType,
                                   intent: Optional[InferredIntent]) -> List[str]:
        """Analyze resource dependencies"""
        dependencies = []
        
        # Basic dependency analysis based on resource type
        if "vpc" in resource_type.resource_type.lower():
            dependencies.append("aws_internet_gateway")
        elif "subnet" in resource_type.resource_type.lower():
            dependencies.append("aws_vpc")
        elif "instance" in resource_type.resource_type.lower():
            dependencies.extend(["aws_subnet", "aws_security_group"])
        
        # AI-enhanced dependency analysis
        if intent and intent.architecture:
            dependencies.extend(intent.architecture.get("dependencies", []))
        
        return dependencies
    
    async def _prepare_variables(self, 
                                request: GenerationRequestSchema,
                                parameters: List[ResourceParameter],
                                intent: Optional[InferredIntent]) -> Dict[str, Any]:
        """Prepare variables for template rendering"""
        variables = {
            "resource_name": request.parameters.get("name", "example"),
            "provider": request.provider,
            "environment": request.deployment_environment,
            "parameters": request.parameters
        }
        
        # Add team standards
        if request.team_standards:
            variables["naming_convention"] = request.team_standards.naming_convention
            variables["required_tags"] = request.team_standards.required_tags
        
        # Add AI-enhanced variables
        if intent:
            variables.update(intent.variables or {})
        
        return variables
    
    async def _generate_outputs(self, 
                               resource_type: ResourceType,
                               variables: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate standard outputs for resource type"""
        outputs = []
        
        # Standard outputs based on resource type
        if "instance" in resource_type.resource_type.lower():
            outputs.extend([
                {"name": "instance_id", "value": "aws_instance.example.id", "description": "Instance ID"},
                {"name": "public_ip", "value": "aws_instance.example.public_ip", "description": "Public IP address"},
                {"name": "private_ip", "value": "aws_instance.example.private_ip", "description": "Private IP address"}
            ])
        elif "vpc" in resource_type.resource_type.lower():
            outputs.extend([
                {"name": "vpc_id", "value": "aws_vpc.example.id", "description": "VPC ID"},
                {"name": "vpc_cidr", "value": "aws_vpc.example.cidr_block", "description": "VPC CIDR block"}
            ])
        
        return outputs
    
    async def _apply_best_practices(self, 
                                   generated_code: GeneratedCode,
                                   resource_type: ResourceType,
                                   context: Dict[str, Any]) -> GeneratedCode:
        """Apply best practices to generated code"""
        # Add security best practices
        if context.get("complexity_score", 1) >= 3:
            generated_code.warnings.append(
                "Consider implementing additional security measures for production environments"
            )
        
        # Add performance recommendations
        if "instance" in resource_type.resource_type.lower():
            generated_code.recommendations.append(
                "Consider using auto-scaling groups for better availability and performance"
            )
        
        return generated_code


class CodeGenerationService:
    """Service for managing code generation operations"""
    
    def __init__(self, generator: IntelligentCodeGenerator):
        self.generator = generator
    
    async def generate_code(self, 
                           db: AsyncSession,
                           request: GenerationRequestSchema) -> GeneratedCode:
        """Generate Terraform code and track request"""
        # Create generation request record
        generation_request = GenerationRequest(
            provider=request.provider,
            resource_type=request.resource_type,
            action=request.action,
            natural_language_request=request.natural_language_request,
            parameters=request.parameters,
            requirements=request.requirements,
            status="pending"
        )
        
        db.add(generation_request)
        await db.commit()
        
        start_time = datetime.utcnow()
        
        try:
            # Generate code
            generated_code = await self.generator.generate_terraform_code(db, request)
            
            # Update request record
            generation_request.status = "completed"
            generation_request.generated_code = {
                "main": generated_code.main,
                "variables": generated_code.variables,
                "outputs": generated_code.outputs,
                "module": generated_code.module
            }
            generation_request.processing_time_ms = int(
                (datetime.utcnow() - start_time).total_seconds() * 1000
            )
            generation_request.completed_at = datetime.utcnow()
            
            await db.commit()
            
            return generated_code
            
        except Exception as e:
            # Update request record with error
            generation_request.status = "error"
            generation_request.error_message = str(e)
            generation_request.completed_at = datetime.utcnow()
            
            await db.commit()
            raise
    
    async def validate_code(self, 
                           db: AsyncSession,
                           code: str, 
                           provider: str) -> ValidationResult:
        """Validate Terraform code"""
        # This would integrate with terraform validate or similar tool
        # For now, return a basic validation result
        return ValidationResult(
            is_valid=True,
            errors=[],
            warnings=[],
            suggestions=["Consider adding resource tags for better organization"]
        )
    
    async def get_suggestions(self, 
                             db: AsyncSession,
                             context: CodeContext) -> List[Suggestion]:
        """Get AI-powered suggestions for code improvement"""
        # This would integrate with AI service for intelligent suggestions
        suggestions = []
        
        if "resource" in context.current_code and "aws_instance" in context.current_code:
            suggestions.append(Suggestion(
                type="security",
                title="Add security group",
                description="Consider adding a security group to control network access",
                code_snippet='resource "aws_security_group" "example" { ... }',
                priority="high"
            ))
        
        return suggestions