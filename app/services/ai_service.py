"""
AI reasoning service for intelligent code generation
"""
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

import openai
from openai import AsyncOpenAI

from app.models.schemas import GenerationRequest, InferredIntent
from app.core.config import get_settings
from app.core.exceptions import AIServiceError

logger = logging.getLogger(__name__)
settings = get_settings()


class InferredIntent:
    """Inferred intent from natural language request"""
    
    def __init__(self, data: Dict[str, Any]):
        self.resources = data.get("resources", [])
        self.architecture = data.get("architecture", {})
        self.constraints = data.get("constraints", {})
        self.recommendations = data.get("recommendations", [])
        self.variables = data.get("variables", {})
        self.security_considerations = data.get("security_considerations", [])
        self.best_practices = data.get("best_practices", [])


class AIReasoningService:
    """AI service for intelligent code generation reasoning"""
    
    def __init__(self):
        if not settings.OPENAI_API_KEY:
            logger.warning("OpenAI API key not configured, AI features will be limited")
            self.client = None
        else:
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    
    async def infer_intent(self, 
                          request: GenerationRequest, 
                          context: Dict[str, Any]) -> InferredIntent:
        """Infer user intent from natural language request"""
        if not self.client:
            return self._fallback_intent(request, context)
        
        try:
            prompt = self._build_intent_prompt(request, context)
            
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content
            intent_data = json.loads(content)
            
            return InferredIntent(intent_data)
            
        except Exception as e:
            logger.error(f"AI intent inference failed: {str(e)}")
            return self._fallback_intent(request, context)
    
    def _build_intent_prompt(self, request: GenerationRequest, context: Dict[str, Any]) -> str:
        """Build prompt for intent inference"""
        prompt = f"""
        Analyze the following Terraform infrastructure request and provide structured analysis:

        Provider: {request.provider}
        Resource Type: {request.resource_type}
        Action: {request.action}
        Natural Language Request: {request.natural_language_request}
        Environment: {request.deployment_environment}
        
        Parameters: {json.dumps(request.parameters, indent=2)}
        
        Requirements:
        {json.dumps(request.requirements, indent=2)}
        
        Context:
        {json.dumps(context, indent=2)}
        
        Please provide a JSON response with the following structure:
        {{
            "resources": [
                {{
                    "type": "resource_type",
                    "name": "resource_name",
                    "properties": {{}}
                }}
            ],
            "architecture": {{
                "pattern": "architecture_pattern",
                "dependencies": ["dependency1", "dependency2"],
                "relationships": {{}}
            }},
            "constraints": {{
                "performance": {{}},
                "security": {{}},
                "cost": {{}}
            }},
            "recommendations": [
                "recommendation1",
                "recommendation2"
            ],
            "variables": {{
                "variable_name": "variable_value"
            }},
            "security_considerations": [
                "security_consideration1"
            ],
            "best_practices": [
                "best_practice1"
            ]
        }}
        
        Focus on:
        1. Understanding the user's intent and requirements
        2. Identifying necessary resources and their relationships
        3. Applying security best practices
        4. Considering performance and cost optimization
        5. Providing actionable recommendations
        """
        
        return prompt
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for AI model"""
        return """
        You are an expert Terraform and cloud infrastructure consultant with deep knowledge of:
        - AWS, Azure, and Google Cloud Platform services
        - Terraform best practices and patterns
        - Infrastructure security and compliance
        - Cost optimization strategies
        - Performance optimization techniques
        
        Your role is to analyze infrastructure requests and provide intelligent recommendations
        for Terraform code generation. Always consider:
        - Security first approach
        - Cost optimization
        - Scalability and maintainability
        - Industry best practices
        - Compliance requirements
        
        Provide responses in valid JSON format only.
        """
    
    def _fallback_intent(self, request: GenerationRequest, context: Dict[str, Any]) -> InferredIntent:
        """Fallback intent inference without AI"""
        fallback_data = {
            "resources": [
                {
                    "type": request.resource_type,
                    "name": request.parameters.get("name", "example"),
                    "properties": request.parameters
                }
            ],
            "architecture": {
                "pattern": "basic",
                "dependencies": [],
                "relationships": {}
            },
            "constraints": request.requirements,
            "recommendations": [
                "Consider adding resource tags for better organization",
                "Review security group configurations"
            ],
            "variables": request.parameters,
            "security_considerations": [
                "Review access permissions",
                "Enable encryption where applicable"
            ],
            "best_practices": [
                "Use consistent naming conventions",
                "Implement proper resource tagging"
            ]
        }
        
        return InferredIntent(fallback_data)
    
    async def analyze_code_quality(self, code: str, provider: str) -> Dict[str, Any]:
        """Analyze code quality and provide suggestions"""
        if not self.client:
            return self._fallback_code_analysis(code, provider)
        
        try:
            prompt = f"""
            Analyze the following Terraform code for {provider} and provide quality assessment:
            
            ```hcl
            {code}
            ```
            
            Provide analysis in JSON format:
            {{
                "quality_score": 0.0-1.0,
                "issues": [
                    {{
                        "type": "security|performance|style|best_practice",
                        "severity": "low|medium|high|critical",
                        "message": "Description of issue",
                        "line": 0,
                        "suggestion": "How to fix"
                    }}
                ],
                "recommendations": [
                    "Improvement recommendation"
                ],
                "best_practices": [
                    "Best practice to follow"
                ]
            }}
            """
            
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a Terraform expert. Analyze code quality and provide actionable feedback."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=1500
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"AI code analysis failed: {str(e)}")
            return self._fallback_code_analysis(code, provider)
    
    def _fallback_code_analysis(self, code: str, provider: str) -> Dict[str, Any]:
        """Fallback code analysis without AI"""
        issues = []
        
        # Basic static analysis
        if "resource" not in code:
            issues.append({
                "type": "syntax",
                "severity": "high",
                "message": "No resources defined in code",
                "line": 0,
                "suggestion": "Add at least one resource block"
            })
        
        if "tags" not in code:
            issues.append({
                "type": "best_practice",
                "severity": "medium",
                "message": "No resource tags defined",
                "line": 0,
                "suggestion": "Add tags for better resource organization"
            })
        
        return {
            "quality_score": 0.7,
            "issues": issues,
            "recommendations": [
                "Add resource tags for better organization",
                "Consider using variables for reusability"
            ],
            "best_practices": [
                "Use consistent naming conventions",
                "Implement proper resource tagging",
                "Add descriptions to variables"
            ]
        }
    
    async def generate_suggestions(self, 
                                  current_code: str, 
                                  cursor_position: int,
                                  provider: str) -> List[Dict[str, Any]]:
        """Generate context-aware suggestions"""
        if not self.client:
            return self._fallback_suggestions(current_code, provider)
        
        try:
            # Extract context around cursor
            lines = current_code.split('\n')
            current_line = 0
            char_count = 0
            
            for i, line in enumerate(lines):
                if char_count + len(line) >= cursor_position:
                    current_line = i
                    break
                char_count += len(line) + 1
            
            context_start = max(0, current_line - 3)
            context_end = min(len(lines), current_line + 3)
            context_lines = lines[context_start:context_end]
            
            prompt = f"""
            Provide intelligent code completion suggestions for Terraform {provider} code:
            
            Context around cursor:
            ```hcl
            {chr(10).join(context_lines)}
            ```
            
            Current line: {current_line + 1}
            
            Provide suggestions in JSON format:
            {{
                "suggestions": [
                    {{
                        "type": "resource|variable|output|data",
                        "label": "suggestion_label",
                        "description": "Description of suggestion",
                        "code": "code_to_insert",
                        "priority": "high|medium|low"
                    }}
                ]
            }}
            """
            
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a Terraform expert providing intelligent code completion."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content
            result = json.loads(content)
            return result.get("suggestions", [])
            
        except Exception as e:
            logger.error(f"AI suggestion generation failed: {str(e)}")
            return self._fallback_suggestions(current_code, provider)
    
    def _fallback_suggestions(self, code: str, provider: str) -> List[Dict[str, Any]]:
        """Fallback suggestions without AI"""
        suggestions = []
        
        # Basic suggestions based on provider
        if provider == "aws":
            suggestions.extend([
                {
                    "type": "resource",
                    "label": "aws_instance",
                    "description": "EC2 instance resource",
                    "code": 'resource "aws_instance" "example" {\n  ami           = "ami-12345678"\n  instance_type = "t3.micro"\n}',
                    "priority": "high"
                },
                {
                    "type": "resource",
                    "label": "aws_vpc",
                    "description": "VPC resource",
                    "code": 'resource "aws_vpc" "example" {\n  cidr_block = "10.0.0.0/16"\n}',
                    "priority": "medium"
                }
            ])
        
        return suggestions