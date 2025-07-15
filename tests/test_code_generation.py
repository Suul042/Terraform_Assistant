"""
Unit tests for the code generation service
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.code_generation import (
    TemplateEngine, 
    ContextAnalyzer, 
    IntelligentCodeGenerator,
    CodeGenerationService
)
from app.services.ai_service import AIReasoningService, InferredIntent
from app.services.cache_service import CacheService
from app.models.database import ResourceType, ResourceParameter, SmartTemplate, CloudProviderModel
from app.models.schemas import GenerationRequest, GeneratedCode, CloudProvider, TerraformAction
from app.core.exceptions import CodeGenerationError, TemplateNotFoundError


@pytest.fixture
def mock_cache_service():
    """Mock cache service"""
    cache_service = Mock(spec=CacheService)
    cache_service.get = AsyncMock(return_value=None)
    cache_service.set = AsyncMock(return_value=True)
    return cache_service


@pytest.fixture
def mock_ai_service():
    """Mock AI service"""
    ai_service = Mock(spec=AIReasoningService)
    ai_service.infer_intent = AsyncMock(return_value=InferredIntent({
        "resources": [{"type": "aws_instance", "name": "example"}],
        "architecture": {"pattern": "basic", "dependencies": []},
        "constraints": {},
        "recommendations": ["Add tags for better organization"],
        "variables": {"instance_type": "t3.micro"},
        "security_considerations": ["Review security groups"],
        "best_practices": ["Use consistent naming"]
    }))
    return ai_service


@pytest.fixture
def mock_db_session():
    """Mock database session"""
    session = Mock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.scalar_one_or_none = AsyncMock()
    session.scalars = AsyncMock()
    session.add = Mock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def sample_provider():
    """Sample cloud provider"""
    return CloudProviderModel(
        id=1,
        name="aws",
        display_name="Amazon Web Services",
        sync_status="active"
    )


@pytest.fixture
def sample_resource_type():
    """Sample resource type"""
    return ResourceType(
        id=1,
        provider_id=1,
        resource_type="aws_instance",
        category="Compute",
        subcategory="EC2",
        description="EC2 instance resource",
        documentation_url="https://docs.aws.amazon.com/ec2/"
    )


@pytest.fixture
def sample_parameters():
    """Sample resource parameters"""
    return [
        ResourceParameter(
            id=1,
            resource_type_id=1,
            parameter_name="instance_type",
            parameter_type="string",
            is_required=True,
            description="EC2 instance type"
        ),
        ResourceParameter(
            id=2,
            resource_type_id=1,
            parameter_name="ami",
            parameter_type="string",
            is_required=True,
            description="AMI ID"
        ),
        ResourceParameter(
            id=3,
            resource_type_id=1,
            parameter_name="tags",
            parameter_type="map",
            is_required=False,
            description="Resource tags"
        )
    ]


@pytest.fixture
def sample_template():
    """Sample template"""
    return SmartTemplate(
        id=1,
        resource_type_id=1,
        template_name="Basic",
        template_type="main",
        template_content='''resource "aws_instance" "{{ resource_name }}" {
  ami           = var.ami
  instance_type = var.instance_type
  
  {% if required_tags %}
  tags = {
    {% for key, value in required_tags.items() %}
    "{{ key }}" = "{{ value }}"
    {% endfor %}
  }
  {% endif %}
}''',
        complexity_score=1
    )


@pytest.fixture
def sample_generation_request():
    """Sample generation request"""
    return GenerationRequest(
        provider=CloudProvider.AWS,
        resource_type="aws_instance",
        action=TerraformAction.CREATE,
        natural_language_request="Create a web server instance",
        parameters={"instance_type": "t3.micro", "ami": "ami-12345678"},
        requirements={"performance": {"max_response_time_ms": 1000}},
        output_format=["main", "variables"]
    )


class TestTemplateEngine:
    """Test template engine functionality"""
    
    def test_init(self, mock_cache_service):
        """Test template engine initialization"""
        engine = TemplateEngine(mock_cache_service)
        assert engine.cache_service == mock_cache_service
        assert engine.jinja_env is not None
    
    @pytest.mark.asyncio
    async def test_render_template_success(self, mock_cache_service):
        """Test successful template rendering"""
        engine = TemplateEngine(mock_cache_service)
        template_content = 'resource "aws_instance" "{{ name }}" {\n  instance_type = "{{ instance_type }}"\n}'
        variables = {"name": "web", "instance_type": "t3.micro"}
        
        result = await engine.render_template(template_content, variables)
        
        assert 'resource "aws_instance" "web"' in result
        assert 'instance_type = "t3.micro"' in result
    
    @pytest.mark.asyncio
    async def test_render_template_error(self, mock_cache_service):
        """Test template rendering with error"""
        engine = TemplateEngine(mock_cache_service)
        template_content = 'resource "aws_instance" "{{ name }}" {\n  instance_type = "{{ undefined_var }}"\n}'
        variables = {"name": "web"}
        
        with pytest.raises(CodeGenerationError):
            await engine.render_template(template_content, variables)
    
    @pytest.mark.asyncio
    async def test_get_template_from_cache(self, mock_cache_service, sample_template):
        """Test getting template from cache"""
        mock_cache_service.get.return_value = sample_template
        
        engine = TemplateEngine(mock_cache_service)
        result = await engine.get_template(Mock(), 1, "main")
        
        assert result == sample_template
        mock_cache_service.get.assert_called_once_with("template:1:main")
    
    @pytest.mark.asyncio
    async def test_get_template_from_db(self, mock_cache_service, mock_db_session, sample_template):
        """Test getting template from database"""
        mock_cache_service.get.return_value = None
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_template
        mock_db_session.execute.return_value = mock_result
        
        engine = TemplateEngine(mock_cache_service)
        result = await engine.get_template(mock_db_session, 1, "main")
        
        assert result == sample_template
        mock_cache_service.set.assert_called_once_with("template:1:main", sample_template, ttl=3600)
    
    @pytest.mark.asyncio
    async def test_generate_main_tf_success(self, mock_cache_service, mock_db_session, sample_resource_type, sample_template):
        """Test successful main.tf generation"""
        mock_cache_service.get.return_value = sample_template
        
        engine = TemplateEngine(mock_cache_service)
        variables = {"resource_name": "web", "required_tags": {"Environment": "dev"}}
        
        result = await engine.generate_main_tf(mock_db_session, sample_resource_type, variables)
        
        assert 'resource "aws_instance" "web"' in result
        assert 'Environment' in result
    
    @pytest.mark.asyncio
    async def test_generate_main_tf_template_not_found(self, mock_cache_service, mock_db_session, sample_resource_type):
        """Test main.tf generation when template not found"""
        mock_cache_service.get.return_value = None
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result
        
        engine = TemplateEngine(mock_cache_service)
        variables = {"resource_name": "web"}
        
        with pytest.raises(TemplateNotFoundError):
            await engine.generate_main_tf(mock_db_session, sample_resource_type, variables)
    
    @pytest.mark.asyncio
    async def test_generate_variables_tf_with_template(self, mock_cache_service, mock_db_session, sample_resource_type, sample_parameters):
        """Test variables.tf generation with template"""
        variables_template = SmartTemplate(
            id=2,
            resource_type_id=1,
            template_name="Variables",
            template_type="variables",
            template_content='''{% for param in parameters %}
variable "{{ param.parameter_name }}" {
  description = "{{ param.description }}"
  type        = {{ param.parameter_type }}
}
{% endfor %}''',
            complexity_score=1
        )
        mock_cache_service.get.return_value = variables_template
        
        engine = TemplateEngine(mock_cache_service)
        result = await engine.generate_variables_tf(mock_db_session, sample_resource_type, sample_parameters)
        
        assert 'variable "instance_type"' in result
        assert 'variable "ami"' in result
        assert 'variable "tags"' in result
    
    @pytest.mark.asyncio
    async def test_generate_variables_tf_default(self, mock_cache_service, mock_db_session, sample_resource_type, sample_parameters):
        """Test variables.tf generation with default template"""
        mock_cache_service.get.return_value = None
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result
        
        engine = TemplateEngine(mock_cache_service)
        result = await engine.generate_variables_tf(mock_db_session, sample_resource_type, sample_parameters)
        
        assert 'variable "instance_type"' in result
        assert 'variable "ami"' in result
        assert 'type        = string' in result
    
    def test_get_terraform_type(self, mock_cache_service):
        """Test Terraform type conversion"""
        engine = TemplateEngine(mock_cache_service)
        
        assert engine._get_terraform_type("string") == "string"
        assert engine._get_terraform_type("number") == "number"
        assert engine._get_terraform_type("boolean") == "bool"
        assert engine._get_terraform_type("list") == "list(string)"
        assert engine._get_terraform_type("map") == "map(string)"
        assert engine._get_terraform_type("unknown") == "string"


class TestContextAnalyzer:
    """Test context analyzer functionality"""
    
    def test_init(self, mock_cache_service):
        """Test context analyzer initialization"""
        analyzer = ContextAnalyzer(mock_cache_service)
        assert analyzer.cache_service == mock_cache_service
    
    @pytest.mark.asyncio
    async def test_analyze_basic_request(self, mock_cache_service, sample_generation_request):
        """Test basic request analysis"""
        analyzer = ContextAnalyzer(mock_cache_service)
        
        result = await analyzer.analyze(sample_generation_request)
        
        assert result["provider"] == "aws"
        assert result["resource_type"] == "aws_instance"
        assert result["action"] == "create"
        assert result["has_natural_language"] is True
        assert result["has_requirements"] is True
        assert result["complexity_score"] >= 1
    
    @pytest.mark.asyncio
    async def test_analyze_minimal_request(self, mock_cache_service):
        """Test minimal request analysis"""
        request = GenerationRequest(
            provider=CloudProvider.AWS,
            resource_type="aws_instance",
            action=TerraformAction.CREATE,
            parameters={"instance_type": "t3.micro"}
        )
        
        analyzer = ContextAnalyzer(mock_cache_service)
        result = await analyzer.analyze(request)
        
        assert result["provider"] == "aws"
        assert result["has_natural_language"] is False
        assert result["has_requirements"] is False
        assert result["complexity_score"] == 1
    
    def test_calculate_complexity(self, mock_cache_service):
        """Test complexity calculation"""
        analyzer = ContextAnalyzer(mock_cache_service)
        
        # Minimal request
        request = GenerationRequest(
            provider=CloudProvider.AWS,
            resource_type="aws_instance",
            action=TerraformAction.CREATE,
            parameters={}
        )
        score = analyzer._calculate_complexity(request)
        assert score == 1
        
        # Complex request
        request = GenerationRequest(
            provider=CloudProvider.AWS,
            resource_type="aws_instance",
            action=TerraformAction.CREATE,
            natural_language_request="Create a secure web server",
            parameters={"instance_type": "t3.micro"},
            requirements={"performance": {}, "security": {}},
            existing_infrastructure={"vpc_id": "vpc-123"},
            team_standards={"naming_convention": "env-app-resource"}
        )
        score = analyzer._calculate_complexity(request)
        assert score == 5  # Maximum complexity


class TestIntelligentCodeGenerator:
    """Test intelligent code generator"""
    
    def test_init(self, mock_ai_service, mock_cache_service):
        """Test generator initialization"""
        template_engine = TemplateEngine(mock_cache_service)
        context_analyzer = ContextAnalyzer(mock_cache_service)
        
        generator = IntelligentCodeGenerator(
            mock_ai_service,
            template_engine,
            context_analyzer,
            mock_cache_service
        )
        
        assert generator.ai_service == mock_ai_service
        assert generator.template_engine == template_engine
        assert generator.context_analyzer == context_analyzer
        assert generator.cache_service == mock_cache_service
    
    @pytest.mark.asyncio
    async def test_generate_terraform_code_success(self, mock_ai_service, mock_cache_service, mock_db_session, sample_generation_request, sample_resource_type, sample_parameters, sample_template):
        """Test successful code generation"""
        template_engine = TemplateEngine(mock_cache_service)
        context_analyzer = ContextAnalyzer(mock_cache_service)
        
        generator = IntelligentCodeGenerator(
            mock_ai_service,
            template_engine,
            context_analyzer,
            mock_cache_service
        )
        
        # Mock database queries
        mock_resource_result = Mock()
        mock_resource_result.scalar_one_or_none.return_value = sample_resource_type
        mock_params_result = Mock()
        mock_params_result.scalars.return_value.all.return_value = sample_parameters
        mock_db_session.execute.side_effect = [mock_resource_result, mock_params_result]
        
        # Mock template
        mock_cache_service.get.return_value = sample_template
        
        result = await generator.generate_terraform_code(mock_db_session, sample_generation_request)
        
        assert isinstance(result, GeneratedCode)
        assert result.main is not None
        assert result.generation_metadata is not None
        assert result.generation_metadata["provider"] == "aws"
        assert result.generation_metadata["resource_type"] == "aws_instance"
        assert len(result.recommendations) > 0
    
    @pytest.mark.asyncio
    async def test_generate_terraform_code_resource_not_found(self, mock_ai_service, mock_cache_service, mock_db_session, sample_generation_request):
        """Test code generation when resource type not found"""
        template_engine = TemplateEngine(mock_cache_service)
        context_analyzer = ContextAnalyzer(mock_cache_service)
        
        generator = IntelligentCodeGenerator(
            mock_ai_service,
            template_engine,
            context_analyzer,
            mock_cache_service
        )
        
        # Mock database query to return None
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result
        
        with pytest.raises(CodeGenerationError, match="Resource type aws_instance not found"):
            await generator.generate_terraform_code(mock_db_session, sample_generation_request)
    
    @pytest.mark.asyncio
    async def test_analyze_dependencies(self, mock_ai_service, mock_cache_service, sample_resource_type):
        """Test dependency analysis"""
        template_engine = TemplateEngine(mock_cache_service)
        context_analyzer = ContextAnalyzer(mock_cache_service)
        
        generator = IntelligentCodeGenerator(
            mock_ai_service,
            template_engine,
            context_analyzer,
            mock_cache_service
        )
        
        # Test VPC resource
        vpc_resource = ResourceType(
            id=2,
            provider_id=1,
            resource_type="aws_vpc",
            category="Network"
        )
        
        dependencies = await generator._analyze_dependencies(Mock(), vpc_resource, None)
        assert "aws_internet_gateway" in dependencies
        
        # Test instance resource
        dependencies = await generator._analyze_dependencies(Mock(), sample_resource_type, None)
        assert "aws_subnet" in dependencies
        assert "aws_security_group" in dependencies
    
    @pytest.mark.asyncio
    async def test_generate_outputs(self, mock_ai_service, mock_cache_service, sample_resource_type):
        """Test output generation"""
        template_engine = TemplateEngine(mock_cache_service)
        context_analyzer = ContextAnalyzer(mock_cache_service)
        
        generator = IntelligentCodeGenerator(
            mock_ai_service,
            template_engine,
            context_analyzer,
            mock_cache_service
        )
        
        variables = {"resource_name": "web"}
        outputs = await generator._generate_outputs(sample_resource_type, variables)
        
        assert len(outputs) > 0
        assert any(output["name"] == "instance_id" for output in outputs)
        assert any(output["name"] == "public_ip" for output in outputs)
        assert any(output["name"] == "private_ip" for output in outputs)


class TestCodeGenerationService:
    """Test code generation service"""
    
    @pytest.mark.asyncio
    async def test_generate_code_success(self, mock_ai_service, mock_cache_service, mock_db_session, sample_generation_request):
        """Test successful code generation with request tracking"""
        template_engine = TemplateEngine(mock_cache_service)
        context_analyzer = ContextAnalyzer(mock_cache_service)
        
        generator = IntelligentCodeGenerator(
            mock_ai_service,
            template_engine,
            context_analyzer,
            mock_cache_service
        )
        
        service = CodeGenerationService(generator)
        
        # Mock generator to return successful result
        expected_code = GeneratedCode(
            main='resource "aws_instance" "web" {\n  instance_type = "t3.micro"\n}',
            generation_metadata={"provider": "aws", "resource_type": "aws_instance"}
        )
        
        with patch.object(generator, 'generate_terraform_code', return_value=expected_code) as mock_generate:
            result = await service.generate_code(mock_db_session, sample_generation_request)
            
            assert result == expected_code
            mock_generate.assert_called_once_with(mock_db_session, sample_generation_request)
            # Verify database operations
            mock_db_session.add.assert_called()
            assert mock_db_session.commit.call_count == 2  # Once for creation, once for completion
    
    @pytest.mark.asyncio
    async def test_generate_code_with_error(self, mock_ai_service, mock_cache_service, mock_db_session, sample_generation_request):
        """Test code generation with error handling"""
        template_engine = TemplateEngine(mock_cache_service)
        context_analyzer = ContextAnalyzer(mock_cache_service)
        
        generator = IntelligentCodeGenerator(
            mock_ai_service,
            template_engine,
            context_analyzer,
            mock_cache_service
        )
        
        service = CodeGenerationService(generator)
        
        # Mock generator to raise error
        with patch.object(generator, 'generate_terraform_code', side_effect=CodeGenerationError("Test error")) as mock_generate:
            with pytest.raises(CodeGenerationError, match="Test error"):
                await service.generate_code(mock_db_session, sample_generation_request)
            
            mock_generate.assert_called_once_with(mock_db_session, sample_generation_request)
            # Verify error is recorded in database
            mock_db_session.add.assert_called()
            assert mock_db_session.commit.call_count == 2  # Once for creation, once for error update