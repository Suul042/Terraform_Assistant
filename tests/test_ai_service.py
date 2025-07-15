"""
Unit tests for AI reasoning service
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
import json

from app.services.ai_service import AIReasoningService, InferredIntent
from app.models.schemas import GenerationRequest, CloudProvider, TerraformAction
from app.core.exceptions import AIServiceError


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client"""
    client = Mock()
    client.chat = Mock()
    client.chat.completions = Mock()
    client.chat.completions.create = AsyncMock()
    return client


@pytest.fixture
def sample_generation_request():
    """Sample generation request"""
    return GenerationRequest(
        provider=CloudProvider.AWS,
        resource_type="aws_instance",
        action=TerraformAction.CREATE,
        natural_language_request="Create a secure web server for production",
        parameters={"instance_type": "t3.medium"},
        requirements={"security": {"encryption_at_rest": True}}
    )


@pytest.fixture
def sample_openai_response():
    """Sample OpenAI API response"""
    response = Mock()
    response.choices = [Mock()]
    response.choices[0].message = Mock()
    response.choices[0].message.content = json.dumps({
        "resources": [
            {
                "type": "aws_instance",
                "name": "web_server",
                "properties": {
                    "instance_type": "t3.medium",
                    "security_groups": ["web_sg"]
                }
            }
        ],
        "architecture": {
            "pattern": "single_instance",
            "dependencies": ["aws_security_group", "aws_subnet"],
            "relationships": {
                "instance_subnet": "private"
            }
        },
        "constraints": {
            "performance": {"max_cpu": 80},
            "security": {"encryption_required": True},
            "cost": {"max_monthly": 100}
        },
        "recommendations": [
            "Use Application Load Balancer for high availability",
            "Enable CloudWatch monitoring",
            "Configure automated backups"
        ],
        "variables": {
            "instance_type": "t3.medium",
            "subnet_id": "subnet-12345"
        },
        "security_considerations": [
            "Configure security groups to allow only necessary traffic",
            "Enable encryption at rest and in transit",
            "Use IAM roles instead of access keys"
        ],
        "best_practices": [
            "Tag all resources for cost allocation",
            "Use consistent naming conventions",
            "Implement proper monitoring and logging"
        ]
    })
    return response


class TestAIReasoningService:
    """Test AI reasoning service functionality"""
    
    def test_init_with_api_key(self):
        """Test initialization with API key"""
        with patch('app.services.ai_service.settings') as mock_settings:
            mock_settings.OPENAI_API_KEY = "test-key"
            with patch('app.services.ai_service.AsyncOpenAI') as mock_openai:
                service = AIReasoningService()
                assert service.client is not None
                mock_openai.assert_called_once_with(api_key="test-key")
    
    def test_init_without_api_key(self):
        """Test initialization without API key"""
        with patch('app.services.ai_service.settings') as mock_settings:
            mock_settings.OPENAI_API_KEY = None
            service = AIReasoningService()
            assert service.client is None
    
    @pytest.mark.asyncio
    async def test_infer_intent_success(self, sample_generation_request, sample_openai_response):
        """Test successful intent inference"""
        with patch('app.services.ai_service.settings') as mock_settings:
            mock_settings.OPENAI_API_KEY = "test-key"
            mock_settings.OPENAI_MODEL = "gpt-4"
            
            service = AIReasoningService()
            service.client = Mock()
            service.client.chat.completions.create = AsyncMock(return_value=sample_openai_response)
            
            context = {"complexity_score": 3}
            result = await service.infer_intent(sample_generation_request, context)
            
            assert isinstance(result, InferredIntent)
            assert len(result.resources) == 1
            assert result.resources[0]["type"] == "aws_instance"
            assert result.architecture["pattern"] == "single_instance"
            assert "aws_security_group" in result.architecture["dependencies"]
            assert len(result.recommendations) == 3
            assert len(result.security_considerations) == 3
            assert len(result.best_practices) == 3
    
    @pytest.mark.asyncio
    async def test_infer_intent_without_client(self, sample_generation_request):
        """Test intent inference without OpenAI client"""
        service = AIReasoningService()
        service.client = None
        
        context = {"complexity_score": 2}
        result = await service.infer_intent(sample_generation_request, context)
        
        assert isinstance(result, InferredIntent)
        assert len(result.resources) == 1
        assert result.resources[0]["type"] == "aws_instance"
        assert result.architecture["pattern"] == "basic"
        assert len(result.recommendations) == 2
    
    @pytest.mark.asyncio
    async def test_infer_intent_api_error(self, sample_generation_request):
        """Test intent inference with API error"""
        with patch('app.services.ai_service.settings') as mock_settings:
            mock_settings.OPENAI_API_KEY = "test-key"
            mock_settings.OPENAI_MODEL = "gpt-4"
            
            service = AIReasoningService()
            service.client = Mock()
            service.client.chat.completions.create = AsyncMock(side_effect=Exception("API Error"))
            
            context = {"complexity_score": 3}
            result = await service.infer_intent(sample_generation_request, context)
            
            # Should fallback to basic intent
            assert isinstance(result, InferredIntent)
            assert len(result.resources) == 1
            assert result.architecture["pattern"] == "basic"
    
    @pytest.mark.asyncio
    async def test_infer_intent_invalid_json(self, sample_generation_request):
        """Test intent inference with invalid JSON response"""
        with patch('app.services.ai_service.settings') as mock_settings:
            mock_settings.OPENAI_API_KEY = "test-key"
            mock_settings.OPENAI_MODEL = "gpt-4"
            
            service = AIReasoningService()
            service.client = Mock()
            
            # Mock response with invalid JSON
            response = Mock()
            response.choices = [Mock()]
            response.choices[0].message = Mock()
            response.choices[0].message.content = "invalid json"
            
            service.client.chat.completions.create = AsyncMock(return_value=response)
            
            context = {"complexity_score": 3}
            result = await service.infer_intent(sample_generation_request, context)
            
            # Should fallback to basic intent
            assert isinstance(result, InferredIntent)
            assert result.architecture["pattern"] == "basic"
    
    def test_build_intent_prompt(self, sample_generation_request):
        """Test intent prompt building"""
        service = AIReasoningService()
        context = {"complexity_score": 3, "has_natural_language": True}
        
        prompt = service._build_intent_prompt(sample_generation_request, context)
        
        assert "Provider: aws" in prompt
        assert "Resource Type: aws_instance" in prompt
        assert "Action: create" in prompt
        assert "Natural Language Request: Create a secure web server for production" in prompt
        assert "Environment: dev" in prompt
        assert "complexity_score" in prompt
        assert "JSON response" in prompt
    
    def test_get_system_prompt(self):
        """Test system prompt generation"""
        service = AIReasoningService()
        prompt = service._get_system_prompt()
        
        assert "Terraform" in prompt
        assert "cloud infrastructure consultant" in prompt
        assert "AWS, Azure, and Google Cloud Platform" in prompt
        assert "Security first approach" in prompt
        assert "JSON format" in prompt
    
    def test_fallback_intent(self, sample_generation_request):
        """Test fallback intent generation"""
        service = AIReasoningService()
        context = {"complexity_score": 2}
        
        result = service._fallback_intent(sample_generation_request, context)
        
        assert isinstance(result, InferredIntent)
        assert len(result.resources) == 1
        assert result.resources[0]["type"] == "aws_instance"
        assert result.architecture["pattern"] == "basic"
        assert len(result.recommendations) >= 2
        assert len(result.security_considerations) >= 2
        assert len(result.best_practices) >= 2
    
    @pytest.mark.asyncio
    async def test_analyze_code_quality_success(self):
        """Test successful code quality analysis"""
        with patch('app.services.ai_service.settings') as mock_settings:
            mock_settings.OPENAI_API_KEY = "test-key"
            mock_settings.OPENAI_MODEL = "gpt-4"
            
            service = AIReasoningService()
            service.client = Mock()
            
            # Mock response
            response = Mock()
            response.choices = [Mock()]
            response.choices[0].message = Mock()
            response.choices[0].message.content = json.dumps({
                "quality_score": 0.8,
                "issues": [
                    {
                        "type": "best_practice",
                        "severity": "medium",
                        "message": "Missing resource tags",
                        "line": 5,
                        "suggestion": "Add tags for better organization"
                    }
                ],
                "recommendations": [
                    "Add resource tags for better organization",
                    "Use variables for repeated values"
                ],
                "best_practices": [
                    "Use consistent naming conventions",
                    "Add descriptions to variables"
                ]
            })
            
            service.client.chat.completions.create = AsyncMock(return_value=response)
            
            code = 'resource "aws_instance" "web" {\n  instance_type = "t3.micro"\n}'
            result = await service.analyze_code_quality(code, "aws")
            
            assert result["quality_score"] == 0.8
            assert len(result["issues"]) == 1
            assert result["issues"][0]["type"] == "best_practice"
            assert len(result["recommendations"]) == 2
            assert len(result["best_practices"]) == 2
    
    @pytest.mark.asyncio
    async def test_analyze_code_quality_without_client(self):
        """Test code quality analysis without OpenAI client"""
        service = AIReasoningService()
        service.client = None
        
        code = 'resource "aws_instance" "web" {\n  instance_type = "t3.micro"\n}'
        result = await service.analyze_code_quality(code, "aws")
        
        assert result["quality_score"] == 0.7
        assert len(result["recommendations"]) >= 2
        assert len(result["best_practices"]) >= 3
    
    @pytest.mark.asyncio
    async def test_analyze_code_quality_api_error(self):
        """Test code quality analysis with API error"""
        with patch('app.services.ai_service.settings') as mock_settings:
            mock_settings.OPENAI_API_KEY = "test-key"
            mock_settings.OPENAI_MODEL = "gpt-4"
            
            service = AIReasoningService()
            service.client = Mock()
            service.client.chat.completions.create = AsyncMock(side_effect=Exception("API Error"))
            
            code = 'resource "aws_instance" "web" {\n  instance_type = "t3.micro"\n}'
            result = await service.analyze_code_quality(code, "aws")
            
            # Should fallback to basic analysis
            assert result["quality_score"] == 0.7
            assert len(result["recommendations"]) >= 2
    
    def test_fallback_code_analysis(self):
        """Test fallback code analysis"""
        service = AIReasoningService()
        
        # Code without resources
        code = 'variable "instance_type" { type = string }'
        result = service._fallback_code_analysis(code, "aws")
        
        assert result["quality_score"] == 0.7
        assert any(issue["type"] == "syntax" for issue in result["issues"])
        assert any(issue["message"] == "No resources defined in code" for issue in result["issues"])
        
        # Code without tags
        code = 'resource "aws_instance" "web" { instance_type = "t3.micro" }'
        result = service._fallback_code_analysis(code, "aws")
        
        assert any(issue["type"] == "best_practice" for issue in result["issues"])
        assert any(issue["message"] == "No resource tags defined" for issue in result["issues"])
    
    @pytest.mark.asyncio
    async def test_generate_suggestions_success(self):
        """Test successful suggestion generation"""
        with patch('app.services.ai_service.settings') as mock_settings:
            mock_settings.OPENAI_API_KEY = "test-key"
            mock_settings.OPENAI_MODEL = "gpt-4"
            
            service = AIReasoningService()
            service.client = Mock()
            
            # Mock response
            response = Mock()
            response.choices = [Mock()]
            response.choices[0].message = Mock()
            response.choices[0].message.content = json.dumps({
                "suggestions": [
                    {
                        "type": "resource",
                        "label": "aws_security_group",
                        "description": "Security group for EC2 instance",
                        "code": 'resource "aws_security_group" "web" {...}',
                        "priority": "high"
                    }
                ]
            })
            
            service.client.chat.completions.create = AsyncMock(return_value=response)
            
            code = 'resource "aws_instance" "web" {\n  instance_type = "t3.micro"\n}'
            result = await service.generate_suggestions(code, 50, "aws")
            
            assert len(result) == 1
            assert result[0]["type"] == "resource"
            assert result[0]["label"] == "aws_security_group"
            assert result[0]["priority"] == "high"
    
    @pytest.mark.asyncio
    async def test_generate_suggestions_without_client(self):
        """Test suggestion generation without OpenAI client"""
        service = AIReasoningService()
        service.client = None
        
        code = 'resource "aws_instance" "web" {\n  instance_type = "t3.micro"\n}'
        result = await service.generate_suggestions(code, 50, "aws")
        
        assert len(result) >= 2
        assert any(suggestion["label"] == "aws_instance" for suggestion in result)
        assert any(suggestion["label"] == "aws_vpc" for suggestion in result)
    
    def test_fallback_suggestions(self):
        """Test fallback suggestion generation"""
        service = AIReasoningService()
        
        # Test AWS suggestions
        code = 'resource "aws_instance" "web" {}'
        result = service._fallback_suggestions(code, "aws")
        
        assert len(result) >= 2
        assert any(suggestion["label"] == "aws_instance" for suggestion in result)
        assert any(suggestion["label"] == "aws_vpc" for suggestion in result)
        assert any(suggestion["type"] == "resource" for suggestion in result)
        
        # Test empty code
        result = service._fallback_suggestions("", "aws")
        assert len(result) >= 2


class TestInferredIntent:
    """Test InferredIntent class"""
    
    def test_init_with_full_data(self):
        """Test initialization with complete data"""
        data = {
            "resources": [{"type": "aws_instance", "name": "web"}],
            "architecture": {"pattern": "single_instance"},
            "constraints": {"performance": {"max_cpu": 80}},
            "recommendations": ["Use load balancer"],
            "variables": {"instance_type": "t3.medium"},
            "security_considerations": ["Configure security groups"],
            "best_practices": ["Tag all resources"]
        }
        
        intent = InferredIntent(data)
        
        assert len(intent.resources) == 1
        assert intent.resources[0]["type"] == "aws_instance"
        assert intent.architecture["pattern"] == "single_instance"
        assert intent.constraints["performance"]["max_cpu"] == 80
        assert len(intent.recommendations) == 1
        assert intent.variables["instance_type"] == "t3.medium"
        assert len(intent.security_considerations) == 1
        assert len(intent.best_practices) == 1
    
    def test_init_with_minimal_data(self):
        """Test initialization with minimal data"""
        data = {}
        
        intent = InferredIntent(data)
        
        assert intent.resources == []
        assert intent.architecture == {}
        assert intent.constraints == {}
        assert intent.recommendations == []
        assert intent.variables == {}
        assert intent.security_considerations == []
        assert intent.best_practices == []
    
    def test_init_with_partial_data(self):
        """Test initialization with partial data"""
        data = {
            "resources": [{"type": "aws_instance"}],
            "recommendations": ["Use monitoring"]
        }
        
        intent = InferredIntent(data)
        
        assert len(intent.resources) == 1
        assert intent.resources[0]["type"] == "aws_instance"
        assert intent.architecture == {}
        assert len(intent.recommendations) == 1
        assert intent.recommendations[0] == "Use monitoring"
        assert intent.variables == {}
        assert intent.security_considerations == []
        assert intent.best_practices == []