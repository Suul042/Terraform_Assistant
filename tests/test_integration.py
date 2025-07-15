"""
Integration tests for the complete code generation workflow
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient
import json

from app.main import app
from app.models.database import Base, CloudProviderModel, ResourceType, ResourceParameter, SmartTemplate
from app.models.schemas import GenerationRequest, CloudProvider, TerraformAction
from app.services.code_generation import CodeGenerationService
from app.services.ai_service import AIReasoningService
from app.services.cache_service import CacheService
from app.core.database import get_db


@pytest.fixture
async def test_db():
    """Create test database session"""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    
    # Use in-memory SQLite for testing
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    TestingSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    yield TestingSessionLocal
    await engine.dispose()


@pytest.fixture
async def test_client(test_db):
    """Create test client with database override"""
    async def override_get_db():
        async with test_db() as session:
            yield session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest.fixture
async def seed_test_data(test_db):
    """Seed test database with sample data"""
    async with test_db() as session:
        # Create provider
        provider = CloudProviderModel(
            name="aws",
            display_name="Amazon Web Services",
            sync_status="active"
        )
        session.add(provider)
        await session.flush()
        
        # Create resource type
        resource_type = ResourceType(
            provider_id=provider.id,
            resource_type="aws_instance",
            category="Compute",
            subcategory="EC2",
            description="Amazon EC2 instance"
        )
        session.add(resource_type)
        await session.flush()
        
        # Create parameters
        parameters = [
            ResourceParameter(
                resource_type_id=resource_type.id,
                parameter_name="instance_type",
                parameter_type="string",
                is_required=True,
                description="EC2 instance type"
            ),
            ResourceParameter(
                resource_type_id=resource_type.id,
                parameter_name="ami",
                parameter_type="string",
                is_required=True,
                description="AMI ID"
            ),
            ResourceParameter(
                resource_type_id=resource_type.id,
                parameter_name="tags",
                parameter_type="map",
                is_required=False,
                description="Resource tags"
            )
        ]
        
        for param in parameters:
            session.add(param)
        
        # Create template
        template = SmartTemplate(
            resource_type_id=resource_type.id,
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
        session.add(template)
        
        await session.commit()
        
        return {
            "provider": provider,
            "resource_type": resource_type,
            "parameters": parameters,
            "template": template
        }


class TestCodeGenerationIntegration:
    """Integration tests for code generation workflow"""
    
    @pytest.mark.asyncio
    async def test_complete_code_generation_workflow(self, test_client, seed_test_data):
        """Test complete code generation workflow via API"""
        # Prepare request
        request_data = {
            "provider": "aws",
            "resource_type": "aws_instance",
            "action": "create",
            "natural_language_request": "Create a web server instance",
            "parameters": {
                "instance_type": "t3.micro",
                "ami": "ami-12345678"
            },
            "requirements": {
                "security": {"encryption_at_rest": True}
            },
            "output_format": ["main", "variables"],
            "include_comments": True
        }
        
        # Mock AI service to avoid external API calls
        with patch('app.services.ai_service.AIReasoningService') as mock_ai_service:
            mock_ai_service.return_value.infer_intent = AsyncMock(return_value=Mock(
                resources=[{"type": "aws_instance", "name": "web"}],
                architecture={"pattern": "basic", "dependencies": []},
                constraints={},
                recommendations=["Add monitoring"],
                variables={"instance_type": "t3.micro"},
                security_considerations=["Configure security groups"],
                best_practices=["Tag resources"]
            ))
            
            # Make API request
            response = await test_client.post("/api/v1/generate", json=request_data)
            
            assert response.status_code == 200
            
            result = response.json()
            assert result["success"] is True
            assert "data" in result
            
            generated_code = result["data"]
            assert "main" in generated_code
            assert "variables" in generated_code
            assert "generation_metadata" in generated_code
            
            # Verify generated code structure
            assert 'resource "aws_instance"' in generated_code["main"]
            assert 'variable "instance_type"' in generated_code["variables"]
            assert 'variable "ami"' in generated_code["variables"]
            
            # Verify metadata
            metadata = generated_code["generation_metadata"]
            assert metadata["provider"] == "aws"
            assert metadata["resource_type"] == "aws_instance"
            assert "generated_at" in metadata
    
    @pytest.mark.asyncio
    async def test_code_generation_with_validation(self, test_client, seed_test_data):
        """Test code generation with validation"""
        # Generate code first
        request_data = {
            "provider": "aws",
            "resource_type": "aws_instance",
            "action": "create",
            "parameters": {
                "instance_type": "t3.micro",
                "ami": "ami-12345678"
            },
            "output_format": ["main"]
        }
        
        with patch('app.services.ai_service.AIReasoningService'):
            generation_response = await test_client.post("/api/v1/generate", json=request_data)
            assert generation_response.status_code == 200
            
            generated_code = generation_response.json()["data"]["main"]
            
            # Validate the generated code
            validation_request = {
                "code": generated_code,
                "provider": "aws"
            }
            
            validation_response = await test_client.post("/api/v1/validate", json=validation_request)
            assert validation_response.status_code == 200
            
            validation_result = validation_response.json()["data"]
            assert "is_valid" in validation_result
            assert "errors" in validation_result
            assert "warnings" in validation_result
            assert "suggestions" in validation_result
    
    @pytest.mark.asyncio
    async def test_get_suggestions_workflow(self, test_client, seed_test_data):
        """Test suggestions workflow"""
        request_data = {
            "current_code": 'resource "aws_instance" "web" {\n  instance_type = "t3.micro"\n}',
            "cursor_position": 50,
            "provider": "aws",
            "resource_type": "aws_instance"
        }
        
        with patch('app.services.ai_service.AIReasoningService') as mock_ai_service:
            mock_ai_service.return_value.generate_suggestions = AsyncMock(return_value=[
                {
                    "type": "resource",
                    "label": "aws_security_group",
                    "description": "Security group for EC2 instance",
                    "code": 'resource "aws_security_group" "web" {...}',
                    "priority": "high"
                }
            ])
            
            response = await test_client.post("/api/v1/suggestions", json=request_data)
            assert response.status_code == 200
            
            suggestions = response.json()["data"]
            assert len(suggestions) >= 1
            assert suggestions[0]["type"] == "resource"
            assert suggestions[0]["label"] == "aws_security_group"
    
    @pytest.mark.asyncio
    async def test_get_providers_workflow(self, test_client, seed_test_data):
        """Test providers endpoint"""
        response = await test_client.get("/api/v1/providers")
        assert response.status_code == 200
        
        providers = response.json()["data"]
        assert len(providers) >= 1
        assert providers[0]["name"] == "aws"
        assert providers[0]["display_name"] == "Amazon Web Services"
        assert providers[0]["sync_status"] == "active"
    
    @pytest.mark.asyncio
    async def test_get_resource_types_workflow(self, test_client, seed_test_data):
        """Test resource types endpoint"""
        response = await test_client.get("/api/v1/resource-types?provider=aws")
        assert response.status_code == 200
        
        resource_types = response.json()["data"]
        assert len(resource_types) >= 1
        assert resource_types[0]["resource_type"] == "aws_instance"
        assert resource_types[0]["category"] == "Compute"
        assert resource_types[0]["provider"]["name"] == "aws"
    
    @pytest.mark.asyncio
    async def test_get_resource_parameters_workflow(self, test_client, seed_test_data):
        """Test resource parameters endpoint"""
        # Get resource type ID first
        resource_types_response = await test_client.get("/api/v1/resource-types?provider=aws")
        resource_type_id = resource_types_response.json()["data"][0]["id"]
        
        response = await test_client.get(f"/api/v1/resource-types/{resource_type_id}/parameters")
        assert response.status_code == 200
        
        parameters = response.json()["data"]
        assert len(parameters) >= 2
        
        # Check required parameters
        required_params = [p for p in parameters if p["is_required"]]
        assert len(required_params) == 2
        
        param_names = [p["parameter_name"] for p in parameters]
        assert "instance_type" in param_names
        assert "ami" in param_names
        assert "tags" in param_names
    
    @pytest.mark.asyncio
    async def test_error_handling_workflow(self, test_client):
        """Test error handling in API"""
        # Test with non-existent resource type
        request_data = {
            "provider": "aws",
            "resource_type": "non_existent_resource",
            "action": "create",
            "parameters": {}
        }
        
        response = await test_client.post("/api/v1/generate", json=request_data)
        assert response.status_code == 400 or response.status_code == 404
        
        result = response.json()
        assert result["success"] is False
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_concurrent_generation_requests(self, test_client, seed_test_data):
        """Test handling concurrent generation requests"""
        import asyncio
        
        request_data = {
            "provider": "aws",
            "resource_type": "aws_instance",
            "action": "create",
            "parameters": {
                "instance_type": "t3.micro",
                "ami": "ami-12345678"
            },
            "output_format": ["main"]
        }
        
        with patch('app.services.ai_service.AIReasoningService'):
            # Send multiple concurrent requests
            tasks = []
            for i in range(5):
                task = test_client.post("/api/v1/generate", json=request_data)
                tasks.append(task)
            
            responses = await asyncio.gather(*tasks)
            
            # All requests should succeed
            for response in responses:
                assert response.status_code == 200
                result = response.json()
                assert result["success"] is True
                assert "data" in result
                assert "main" in result["data"]
    
    @pytest.mark.asyncio
    async def test_template_caching_workflow(self, test_client, seed_test_data):
        """Test template caching in generation workflow"""
        request_data = {
            "provider": "aws",
            "resource_type": "aws_instance",
            "action": "create",
            "parameters": {
                "instance_type": "t3.micro",
                "ami": "ami-12345678"
            },
            "output_format": ["main"]
        }
        
        with patch('app.services.ai_service.AIReasoningService'):
            # First request should populate cache
            response1 = await test_client.post("/api/v1/generate", json=request_data)
            assert response1.status_code == 200
            
            # Second request should use cache
            response2 = await test_client.post("/api/v1/generate", json=request_data)
            assert response2.status_code == 200
            
            # Both should return similar results
            result1 = response1.json()["data"]["main"]
            result2 = response2.json()["data"]["main"]
            
            # Should have same basic structure
            assert 'resource "aws_instance"' in result1
            assert 'resource "aws_instance"' in result2
    
    @pytest.mark.asyncio
    async def test_natural_language_processing_workflow(self, test_client, seed_test_data):
        """Test natural language processing in generation"""
        request_data = {
            "provider": "aws",
            "resource_type": "aws_instance",
            "action": "create",
            "natural_language_request": "Create a secure web server with monitoring and backup",
            "parameters": {
                "instance_type": "t3.medium"
            },
            "requirements": {
                "security": {"encryption_at_rest": True},
                "performance": {"max_response_time_ms": 500}
            },
            "output_format": ["main", "variables", "outputs"]
        }
        
        with patch('app.services.ai_service.AIReasoningService') as mock_ai_service:
            # Mock AI service to return enhanced intent
            mock_ai_service.return_value.infer_intent = AsyncMock(return_value=Mock(
                resources=[
                    {"type": "aws_instance", "name": "web_server"},
                    {"type": "aws_security_group", "name": "web_sg"}
                ],
                architecture={
                    "pattern": "secure_web_server",
                    "dependencies": ["aws_security_group", "aws_cloudwatch_log_group"]
                },
                constraints={
                    "security": {"encryption_required": True},
                    "performance": {"max_response_time": 500}
                },
                recommendations=[
                    "Enable CloudWatch monitoring",
                    "Configure automated backups",
                    "Use Application Load Balancer"
                ],
                variables={
                    "instance_type": "t3.medium",
                    "enable_monitoring": True
                },
                security_considerations=[
                    "Configure security groups properly",
                    "Enable encryption at rest"
                ],
                best_practices=[
                    "Tag all resources",
                    "Use IAM roles"
                ]
            ))
            
            response = await test_client.post("/api/v1/generate", json=request_data)
            assert response.status_code == 200
            
            result = response.json()["data"]
            assert "main" in result
            assert "variables" in result
            assert "outputs" in result
            assert "recommendations" in result
            
            # Verify AI enhancement
            assert len(result["recommendations"]) >= 3
            assert "generation_metadata" in result
            assert result["generation_metadata"]["ai_enhanced"] is True
    
    @pytest.mark.asyncio
    async def test_validation_with_errors(self, test_client):
        """Test validation with terraform code errors"""
        invalid_code = '''
        resource "aws_instance" "web" {
          instance_type = "invalid_type"
          ami = 
        }
        '''
        
        validation_request = {
            "code": invalid_code,
            "provider": "aws"
        }
        
        response = await test_client.post("/api/v1/validate", json=validation_request)
        assert response.status_code == 200
        
        result = response.json()["data"]
        # Basic validation should still work
        assert "is_valid" in result
        assert "suggestions" in result
    
    @pytest.mark.asyncio
    async def test_health_check_endpoint(self, test_client):
        """Test health check endpoint"""
        response = await test_client.get("/api/v1/health")
        assert response.status_code == 200
        
        health_data = response.json()["data"]
        assert "status" in health_data
        assert "timestamp" in health_data


class TestCacheIntegration:
    """Integration tests for caching"""
    
    @pytest.mark.asyncio
    async def test_cache_service_integration(self):
        """Test cache service integration"""
        cache_service = CacheService()
        await cache_service.init_redis()
        
        # Test basic cache operations
        test_key = "test:key"
        test_value = {"test": "data"}
        
        # Set value
        result = await cache_service.set(test_key, test_value, ttl=60)
        assert result is True
        
        # Get value
        cached_value = await cache_service.get(test_key)
        assert cached_value == test_value
        
        # Delete value
        result = await cache_service.delete(test_key)
        assert result is True
        
        # Verify deletion
        cached_value = await cache_service.get(test_key)
        assert cached_value is None
        
        await cache_service.close_redis()
    
    @pytest.mark.asyncio
    async def test_template_cache_integration(self):
        """Test template cache integration"""
        cache_service = CacheService()
        await cache_service.init_redis()
        
        from app.services.cache_service import TemplateCache
        template_cache = TemplateCache(cache_service)
        
        # Test template caching
        resource_type_id = 1
        template_type = "main"
        template_content = 'resource "aws_instance" "test" {}'
        
        # Set template
        result = await template_cache.set_template(resource_type_id, template_type, template_content)
        assert result is True
        
        # Get template
        cached_template = await template_cache.get_template(resource_type_id, template_type)
        assert cached_template == template_content
        
        # Invalidate templates
        count = await template_cache.invalidate_resource_templates(resource_type_id)
        assert count >= 1
        
        # Verify invalidation
        cached_template = await template_cache.get_template(resource_type_id, template_type)
        assert cached_template is None
        
        await cache_service.close_redis()


class TestErrorHandling:
    """Integration tests for error handling"""
    
    @pytest.mark.asyncio
    async def test_database_error_handling(self, test_client):
        """Test database error handling"""
        # Test with invalid database state
        request_data = {
            "provider": "nonexistent",
            "resource_type": "nonexistent_resource",
            "action": "create",
            "parameters": {}
        }
        
        response = await test_client.post("/api/v1/generate", json=request_data)
        
        # Should handle gracefully
        assert response.status_code in [400, 404, 500]
        
        result = response.json()
        assert result["success"] is False
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_validation_error_handling(self, test_client):
        """Test validation error handling"""
        # Test with invalid request data
        invalid_request = {
            "provider": "invalid_provider",
            "resource_type": "",  # Empty resource type
            "action": "invalid_action",
            "parameters": "invalid_parameters"  # Should be object
        }
        
        response = await test_client.post("/api/v1/generate", json=invalid_request)
        
        # Should return validation error
        assert response.status_code == 422
        
        result = response.json()
        assert "detail" in result  # FastAPI validation error format
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, test_client):
        """Test timeout handling"""
        # This would require mocking slow operations
        # For now, just test that the endpoint responds
        request_data = {
            "provider": "aws",
            "resource_type": "aws_instance",
            "action": "create",
            "parameters": {
                "instance_type": "t3.micro",
                "ami": "ami-12345678"
            }
        }
        
        # Test should complete within reasonable time
        import time
        start_time = time.time()
        
        with patch('app.services.ai_service.AIReasoningService'):
            response = await test_client.post("/api/v1/generate", json=request_data)
            
        end_time = time.time()
        
        # Should complete within 30 seconds
        assert end_time - start_time < 30
        assert response.status_code == 200