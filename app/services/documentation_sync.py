"""
Documentation synchronization and parsing service
"""
import asyncio
import hashlib
import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
import re

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from app.models.database import (
    CloudProviderModel, ResourceType, ResourceParameter, 
    SmartTemplate, DocumentationSync
)
from app.services.cache_service import DocumentationCache
from app.core.config import get_settings
from app.core.exceptions import DocumentationSyncError

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class DocumentChange:
    """Represents a documentation change"""
    type: str  # CREATE, UPDATE, DELETE
    resource_type: str
    resource_data: Optional[Dict[str, Any]] = None
    resource_id: Optional[int] = None


@dataclass
class ResourceDetails:
    """Detailed resource information"""
    resource_type: str
    category: str
    subcategory: str
    description: str
    documentation_url: str
    parameters: List[Dict[str, Any]]
    examples: List[Dict[str, Any]]
    version_hash: str


class ProviderAdapter:
    """Base class for provider-specific documentation adapters"""
    
    def __init__(self, provider_name: str, base_url: str, cache: DocumentationCache):
        self.provider_name = provider_name
        self.base_url = base_url
        self.cache = cache
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def detect_changes(self) -> List[DocumentChange]:
        """Detect changes in provider documentation"""
        raise NotImplementedError
    
    async def fetch_resource_details(self, resource_type: str) -> ResourceDetails:
        """Fetch detailed resource information"""
        raise NotImplementedError
    
    async def validate_documentation(self, resource: ResourceDetails) -> bool:
        """Validate documentation completeness"""
        return all([
            resource.resource_type,
            resource.description,
            resource.documentation_url,
            resource.parameters
        ])
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


class AWSProviderAdapter(ProviderAdapter):
    """AWS Terraform provider documentation adapter"""
    
    def __init__(self, cache: DocumentationCache):
        super().__init__("aws", settings.AWS_DOCS_BASE_URL, cache)
        self.resource_index_url = f"{self.base_url}/resources"
        self.data_source_index_url = f"{self.base_url}/data-sources"
    
    async def detect_changes(self) -> List[DocumentChange]:
        """Detect changes in AWS provider documentation"""
        changes = []
        
        try:
            # Fetch resource index page
            response = await self.client.get(self.resource_index_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract resource links
            resource_links = soup.find_all('a', href=re.compile(r'/resources/'))
            
            for link in resource_links:
                resource_type = self._extract_resource_type(link.get('href'))
                if resource_type:
                    # Check if resource is new or updated
                    cached_resource = await self.cache.get_resource_docs("aws", resource_type)
                    
                    if not cached_resource:
                        changes.append(DocumentChange(
                            type="CREATE",
                            resource_type=resource_type,
                            resource_data={"url": urljoin(self.base_url, link.get('href'))}
                        ))
                    else:
                        # Check for updates by comparing last modified
                        resource_details = await self.fetch_resource_details(resource_type)
                        if resource_details.version_hash != cached_resource.get("version_hash"):
                            changes.append(DocumentChange(
                                type="UPDATE",
                                resource_type=resource_type,
                                resource_data={"url": urljoin(self.base_url, link.get('href'))}
                            ))
            
            return changes
            
        except Exception as e:
            logger.error(f"Error detecting AWS changes: {str(e)}")
            raise DocumentationSyncError(f"Failed to detect AWS changes: {str(e)}")
    
    async def fetch_resource_details(self, resource_type: str) -> ResourceDetails:
        """Fetch AWS resource details"""
        resource_url = f"{self.base_url}/resources/{resource_type}"
        
        try:
            response = await self.client.get(resource_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract resource information
            description = self._extract_description(soup)
            parameters = self._extract_parameters(soup)
            examples = self._extract_examples(soup)
            category = self._determine_category(resource_type)
            
            # Generate version hash
            content_hash = hashlib.md5(response.content).hexdigest()
            
            return ResourceDetails(
                resource_type=resource_type,
                category=category,
                subcategory=self._determine_subcategory(resource_type, category),
                description=description,
                documentation_url=resource_url,
                parameters=parameters,
                examples=examples,
                version_hash=content_hash
            )
            
        except Exception as e:
            logger.error(f"Error fetching AWS resource {resource_type}: {str(e)}")
            raise DocumentationSyncError(f"Failed to fetch AWS resource details: {str(e)}")
    
    def _extract_resource_type(self, href: str) -> Optional[str]:
        """Extract resource type from href"""
        match = re.search(r'/resources/([^/]+)', href)
        return match.group(1) if match else None
    
    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract resource description"""
        # Look for description in various common locations
        description_selectors = [
            'p.description',
            '.description p',
            'div.description',
            'main p:first-of-type',
            'article p:first-of-type'
        ]
        
        for selector in description_selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        
        return "No description available"
    
    def _extract_parameters(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract resource parameters"""
        parameters = []
        
        # Look for argument reference table
        tables = soup.find_all('table')
        for table in tables:
            headers = table.find_all('th')
            if any('argument' in th.get_text().lower() for th in headers):
                rows = table.find_all('tr')[1:]  # Skip header row
                
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        param_name = cells[0].get_text(strip=True).rstrip('*')
                        param_description = cells[1].get_text(strip=True)
                        
                        # Determine if required (often marked with *)
                        is_required = '*' in cells[0].get_text()
                        
                        # Try to extract type information
                        param_type = self._extract_parameter_type(param_description)
                        
                        parameters.append({
                            'parameter_name': param_name,
                            'parameter_type': param_type,
                            'is_required': is_required,
                            'description': param_description,
                            'validation_rules': {}
                        })
        
        return parameters
    
    def _extract_examples(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract code examples"""
        examples = []
        
        # Look for code blocks
        code_blocks = soup.find_all('pre')
        for i, block in enumerate(code_blocks):
            code_text = block.get_text(strip=True)
            if 'resource "' in code_text:
                examples.append({
                    'title': f'Example {i + 1}',
                    'code': code_text,
                    'description': 'Terraform configuration example'
                })
        
        return examples
    
    def _extract_parameter_type(self, description: str) -> str:
        """Extract parameter type from description"""
        description_lower = description.lower()
        
        if 'boolean' in description_lower or 'true/false' in description_lower:
            return 'boolean'
        elif 'number' in description_lower or 'integer' in description_lower:
            return 'number'
        elif 'list' in description_lower or 'array' in description_lower:
            return 'list'
        elif 'map' in description_lower or 'object' in description_lower:
            return 'map'
        else:
            return 'string'
    
    def _determine_category(self, resource_type: str) -> str:
        """Determine resource category"""
        category_mapping = {
            'ec2': 'Compute',
            'rds': 'Database',
            'vpc': 'Network',
            's3': 'Storage',
            'iam': 'Security',
            'lambda': 'Compute',
            'cloudfront': 'CDN',
            'route53': 'DNS',
            'elb': 'Load Balancer',
            'autoscaling': 'Scaling'
        }
        
        for key, category in category_mapping.items():
            if key in resource_type.lower():
                return category
        
        return 'Other'
    
    def _determine_subcategory(self, resource_type: str, category: str) -> str:
        """Determine resource subcategory"""
        if category == 'Compute':
            if 'instance' in resource_type:
                return 'EC2 Instance'
            elif 'lambda' in resource_type:
                return 'Lambda Function'
        elif category == 'Network':
            if 'vpc' in resource_type:
                return 'VPC'
            elif 'subnet' in resource_type:
                return 'Subnet'
        
        return category


class AzureProviderAdapter(ProviderAdapter):
    """Azure Terraform provider documentation adapter"""
    
    def __init__(self, cache: DocumentationCache):
        super().__init__("azure", settings.AZURE_DOCS_BASE_URL, cache)
    
    async def detect_changes(self) -> List[DocumentChange]:
        """Detect changes in Azure provider documentation"""
        # Implementation similar to AWS but for Azure
        return []
    
    async def fetch_resource_details(self, resource_type: str) -> ResourceDetails:
        """Fetch Azure resource details"""
        # Implementation similar to AWS but for Azure
        return ResourceDetails(
            resource_type=resource_type,
            category="Azure",
            subcategory="Resource",
            description="Azure resource",
            documentation_url=f"{self.base_url}/resources/{resource_type}",
            parameters=[],
            examples=[],
            version_hash=""
        )


class GCPProviderAdapter(ProviderAdapter):
    """Google Cloud Terraform provider documentation adapter"""
    
    def __init__(self, cache: DocumentationCache):
        super().__init__("gcp", settings.GCP_DOCS_BASE_URL, cache)
    
    async def detect_changes(self) -> List[DocumentChange]:
        """Detect changes in GCP provider documentation"""
        # Implementation similar to AWS but for GCP
        return []
    
    async def fetch_resource_details(self, resource_type: str) -> ResourceDetails:
        """Fetch GCP resource details"""
        # Implementation similar to AWS but for GCP
        return ResourceDetails(
            resource_type=resource_type,
            category="GCP",
            subcategory="Resource",
            description="GCP resource",
            documentation_url=f"{self.base_url}/resources/{resource_type}",
            parameters=[],
            examples=[],
            version_hash=""
        )


class DocumentSyncEngine:
    """Main documentation synchronization engine"""
    
    def __init__(self, cache: DocumentationCache):
        self.cache = cache
        self.providers = {
            "aws": AWSProviderAdapter(cache),
            "azure": AzureProviderAdapter(cache),
            "gcp": GCPProviderAdapter(cache)
        }
    
    async def sync_all_providers(self, db: AsyncSession) -> Dict[str, Any]:
        """Sync all providers"""
        results = {}
        
        for provider_name, adapter in self.providers.items():
            try:
                result = await self.sync_provider(db, provider_name, adapter)
                results[provider_name] = result
            except Exception as e:
                logger.error(f"Failed to sync {provider_name}: {str(e)}")
                results[provider_name] = {"status": "error", "error": str(e)}
        
        return results
    
    async def sync_provider(self, 
                           db: AsyncSession, 
                           provider_name: str, 
                           adapter: ProviderAdapter) -> Dict[str, Any]:
        """Sync a specific provider"""
        # Get provider from database
        result = await db.execute(
            select(CloudProviderModel).where(CloudProviderModel.name == provider_name)
        )
        provider = result.scalar_one_or_none()
        
        if not provider:
            raise DocumentationSyncError(f"Provider {provider_name} not found")
        
        # Create sync record
        sync_record = DocumentationSync(
            provider_id=provider.id,
            sync_type="incremental",
            status="running"
        )
        db.add(sync_record)
        await db.commit()
        
        try:
            # Detect changes
            changes = await adapter.detect_changes()
            
            # Process changes
            stats = {
                "resources_processed": 0,
                "resources_created": 0,
                "resources_updated": 0,
                "resources_deleted": 0
            }
            
            for change in changes:
                try:
                    if change.type == "CREATE":
                        await self._create_resource(db, provider, adapter, change)
                        stats["resources_created"] += 1
                    elif change.type == "UPDATE":
                        await self._update_resource(db, provider, adapter, change)
                        stats["resources_updated"] += 1
                    elif change.type == "DELETE":
                        await self._delete_resource(db, provider, change)
                        stats["resources_deleted"] += 1
                    
                    stats["resources_processed"] += 1
                    
                except Exception as e:
                    logger.error(f"Error processing change {change.type}:{change.resource_type}: {str(e)}")
            
            # Update sync record
            sync_record.status = "completed"
            sync_record.resources_processed = stats["resources_processed"]
            sync_record.resources_created = stats["resources_created"]
            sync_record.resources_updated = stats["resources_updated"]
            sync_record.resources_deleted = stats["resources_deleted"]
            sync_record.completed_at = datetime.utcnow()
            
            await db.commit()
            
            # Update provider last sync
            provider.last_sync_at = datetime.utcnow()
            provider.sync_status = "active"
            await db.commit()
            
            return {
                "status": "success",
                "stats": stats
            }
            
        except Exception as e:
            # Update sync record with error
            sync_record.status = "failed"
            sync_record.error_message = str(e)
            sync_record.completed_at = datetime.utcnow()
            
            await db.commit()
            
            # Update provider status
            provider.sync_status = "error"
            await db.commit()
            
            raise DocumentationSyncError(f"Sync failed for {provider_name}: {str(e)}")
    
    async def _create_resource(self, 
                              db: AsyncSession,
                              provider: CloudProviderModel,
                              adapter: ProviderAdapter,
                              change: DocumentChange):
        """Create new resource"""
        resource_details = await adapter.fetch_resource_details(change.resource_type)
        
        # Create resource type
        resource_type = ResourceType(
            provider_id=provider.id,
            resource_type=resource_details.resource_type,
            category=resource_details.category,
            subcategory=resource_details.subcategory,
            description=resource_details.description,
            documentation_url=resource_details.documentation_url,
            version_hash=resource_details.version_hash
        )
        
        db.add(resource_type)
        await db.flush()
        
        # Create parameters
        for param_data in resource_details.parameters:
            parameter = ResourceParameter(
                resource_type_id=resource_type.id,
                parameter_name=param_data['parameter_name'],
                parameter_type=param_data['parameter_type'],
                is_required=param_data['is_required'],
                description=param_data['description'],
                validation_rules=param_data.get('validation_rules', {})
            )
            db.add(parameter)
        
        # Create basic templates
        await self._create_basic_templates(db, resource_type, resource_details)
        
        # Cache resource documentation
        await self.cache.set_resource_docs(
            provider.name, 
            resource_details.resource_type, 
            {
                "resource_type": resource_details.resource_type,
                "description": resource_details.description,
                "parameters": resource_details.parameters,
                "examples": resource_details.examples,
                "version_hash": resource_details.version_hash
            }
        )
    
    async def _update_resource(self, 
                              db: AsyncSession,
                              provider: CloudProviderModel,
                              adapter: ProviderAdapter,
                              change: DocumentChange):
        """Update existing resource"""
        resource_details = await adapter.fetch_resource_details(change.resource_type)
        
        # Find existing resource
        result = await db.execute(
            select(ResourceType).where(
                ResourceType.provider_id == provider.id,
                ResourceType.resource_type == change.resource_type
            )
        )
        resource_type = result.scalar_one_or_none()
        
        if resource_type:
            # Update resource type
            resource_type.description = resource_details.description
            resource_type.documentation_url = resource_details.documentation_url
            resource_type.version_hash = resource_details.version_hash
            resource_type.updated_at = datetime.utcnow()
            
            # Update parameters (remove old, add new)
            await db.execute(
                delete(ResourceParameter).where(
                    ResourceParameter.resource_type_id == resource_type.id
                )
            )
            
            for param_data in resource_details.parameters:
                parameter = ResourceParameter(
                    resource_type_id=resource_type.id,
                    parameter_name=param_data['parameter_name'],
                    parameter_type=param_data['parameter_type'],
                    is_required=param_data['is_required'],
                    description=param_data['description'],
                    validation_rules=param_data.get('validation_rules', {})
                )
                db.add(parameter)
            
            # Update cache
            await self.cache.set_resource_docs(
                provider.name,
                resource_details.resource_type,
                {
                    "resource_type": resource_details.resource_type,
                    "description": resource_details.description,
                    "parameters": resource_details.parameters,
                    "examples": resource_details.examples,
                    "version_hash": resource_details.version_hash
                }
            )
    
    async def _delete_resource(self, 
                              db: AsyncSession,
                              provider: CloudProviderModel,
                              change: DocumentChange):
        """Delete resource"""
        # Find and delete resource
        result = await db.execute(
            select(ResourceType).where(
                ResourceType.provider_id == provider.id,
                ResourceType.resource_type == change.resource_type
            )
        )
        resource_type = result.scalar_one_or_none()
        
        if resource_type:
            # Delete related records (parameters, templates)
            await db.execute(
                delete(ResourceParameter).where(
                    ResourceParameter.resource_type_id == resource_type.id
                )
            )
            
            await db.execute(
                delete(SmartTemplate).where(
                    SmartTemplate.resource_type_id == resource_type.id
                )
            )
            
            # Delete resource type
            await db.delete(resource_type)
            
            # Remove from cache
            await self.cache.invalidate_provider_docs(provider.name)
    
    async def _create_basic_templates(self, 
                                     db: AsyncSession,
                                     resource_type: ResourceType,
                                     resource_details: ResourceDetails):
        """Create basic templates for resource"""
        # Create main template
        main_template = SmartTemplate(
            resource_type_id=resource_type.id,
            template_name="Basic",
            template_type="main",
            template_content=self._generate_basic_main_template(resource_details),
            complexity_score=1,
            use_cases={"basic": "Basic resource configuration"}
        )
        db.add(main_template)
        
        # Create variables template
        variables_template = SmartTemplate(
            resource_type_id=resource_type.id,
            template_name="Basic Variables",
            template_type="variables",
            template_content=self._generate_basic_variables_template(resource_details),
            complexity_score=1,
            use_cases={"basic": "Basic variable definitions"}
        )
        db.add(variables_template)
    
    def _generate_basic_main_template(self, resource_details: ResourceDetails) -> str:
        """Generate basic main template"""
        template = f'''resource "{resource_details.resource_type}" "{{{{ resource_name }}}}" {{
'''
        
        # Add required parameters
        for param in resource_details.parameters:
            if param.get('is_required', False):
                template += f'  {param["parameter_name"]} = var.{param["parameter_name"]}\n'
        
        template += '''
  {% if required_tags %}
  tags = {
    {% for key, value in required_tags.items() %}
    "{{ key }}" = "{{ value }}"
    {% endfor %}
  }
  {% endif %}
}'''
        
        return template
    
    def _generate_basic_variables_template(self, resource_details: ResourceDetails) -> str:
        """Generate basic variables template"""
        template = ""
        
        for param in resource_details.parameters:
            if param.get('is_required', False):
                template += f'''variable "{param["parameter_name"]}" {{
  description = "{param.get('description', param['parameter_name'])}"
  type        = {self._get_terraform_type(param.get('parameter_type', 'string'))}
}}

'''
        
        return template
    
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
    
    async def close(self):
        """Close all provider adapters"""
        for adapter in self.providers.values():
            await adapter.close()