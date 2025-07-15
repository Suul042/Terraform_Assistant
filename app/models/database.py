"""
Database models for Terraform Assistant
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
import uuid

Base = declarative_base()


class CloudProvider(str, Enum):
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"


class SyncStatus(str, Enum):
    ACTIVE = "active"
    SYNCING = "syncing"
    ERROR = "error"
    DISABLED = "disabled"


class TemplateType(str, Enum):
    MAIN = "main"
    VARIABLES = "variables"
    OUTPUTS = "outputs"
    MODULE = "module"


class TerraformAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    IMPORT = "import"


class CloudProviderModel(Base):
    """Cloud provider information"""
    __tablename__ = "cloud_providers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    api_endpoint = Column(String(200))
    documentation_base_url = Column(String(200))
    icon_url = Column(String(200))
    last_sync_at = Column(DateTime(timezone=True))
    sync_status = Column(String(20), default=SyncStatus.ACTIVE.value)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    resource_types = relationship("ResourceType", back_populates="provider")
    
    def __repr__(self):
        return f"<CloudProvider(name='{self.name}', status='{self.sync_status}')>"


class ResourceType(Base):
    """Terraform resource types for each provider"""
    __tablename__ = "resource_types"
    
    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("cloud_providers.id"), nullable=False)
    resource_type = Column(String(100), nullable=False)
    category = Column(String(50))
    subcategory = Column(String(50))
    description = Column(Text)
    documentation_url = Column(String(500))
    api_version = Column(String(20))
    deprecation_status = Column(String(20))
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Version control
    version_hash = Column(String(64))
    
    # Relationships
    provider = relationship("CloudProviderModel", back_populates="resource_types")
    parameters = relationship("ResourceParameter", back_populates="resource_type")
    templates = relationship("SmartTemplate", back_populates="resource_type")
    
    # Constraints
    __table_args__ = (
        Index('idx_provider_resource_version', 'provider_id', 'resource_type', 'api_version'),
        Index('idx_resource_category', 'category', 'subcategory'),
    )
    
    def __repr__(self):
        return f"<ResourceType(type='{self.resource_type}', provider='{self.provider.name}')>"


class ResourceParameter(Base):
    """Parameters for Terraform resources"""
    __tablename__ = "resource_parameters"
    
    id = Column(Integer, primary_key=True, index=True)
    resource_type_id = Column(Integer, ForeignKey("resource_types.id"), nullable=False)
    parameter_name = Column(String(100), nullable=False)
    parameter_type = Column(String(50))  # string, number, boolean, list, map
    is_required = Column(Boolean, default=False)
    is_computed = Column(Boolean, default=False)
    default_value = Column(Text)
    description = Column(Text)
    example_value = Column(Text)
    
    # Validation rules
    validation_rules = Column(JSONB)
    
    # Relationships
    resource_type = relationship("ResourceType", back_populates="parameters")
    
    # Constraints
    __table_args__ = (
        Index('idx_resource_parameter', 'resource_type_id', 'parameter_name'),
    )
    
    def __repr__(self):
        return f"<ResourceParameter(name='{self.parameter_name}', type='{self.parameter_type}')>"


class SmartTemplate(Base):
    """Smart templates for code generation"""
    __tablename__ = "smart_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    resource_type_id = Column(Integer, ForeignKey("resource_types.id"), nullable=False)
    template_name = Column(String(100), nullable=False)
    template_type = Column(String(20), nullable=False)  # main, variables, outputs, module
    template_content = Column(Text, nullable=False)
    
    # AI enhancement fields
    use_cases = Column(JSONB)
    complexity_score = Column(Integer, default=1)  # 1-5
    best_practices = Column(JSONB)
    security_considerations = Column(JSONB)
    
    # Template metadata
    variables = Column(JSONB)
    conditions = Column(JSONB)
    
    # Performance optimization
    template_hash = Column(String(64))
    compiled_template = Column(Text)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    resource_type = relationship("ResourceType", back_populates="templates")
    
    # Constraints
    __table_args__ = (
        Index('idx_template_type', 'resource_type_id', 'template_type'),
        Index('idx_template_hash', 'template_hash'),
    )
    
    def __repr__(self):
        return f"<SmartTemplate(name='{self.template_name}', type='{self.template_type}')>"


class GenerationRequest(Base):
    """Code generation request history"""
    __tablename__ = "generation_requests"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(100))  # User identifier
    provider = Column(String(20), nullable=False)
    resource_type = Column(String(100), nullable=False)
    action = Column(String(20), nullable=False)
    
    # Request data
    natural_language_request = Column(Text)
    parameters = Column(JSONB)
    requirements = Column(JSONB)
    context = Column(JSONB)
    
    # Response data
    generated_code = Column(JSONB)
    processing_time_ms = Column(Integer)
    tokens_used = Column(Integer)
    
    # Status
    status = Column(String(20), default="pending")  # pending, completed, error
    error_message = Column(Text)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    
    # Constraints
    __table_args__ = (
        Index('idx_user_requests', 'user_id', 'created_at'),
        Index('idx_provider_resource', 'provider', 'resource_type'),
    )
    
    def __repr__(self):
        return f"<GenerationRequest(id='{self.id}', provider='{self.provider}', resource='{self.resource_type}')>"


class UserProject(Base):
    """User projects for code organization"""
    __tablename__ = "user_projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(100), nullable=False)
    project_name = Column(String(100), nullable=False)
    description = Column(Text)
    
    # Project configuration
    default_provider = Column(String(20))
    default_region = Column(String(50))
    project_config = Column(JSONB)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Constraints
    __table_args__ = (
        Index('idx_user_projects', 'user_id', 'project_name'),
    )
    
    def __repr__(self):
        return f"<UserProject(name='{self.project_name}', user='{self.user_id}')>"


class DocumentationSync(Base):
    """Documentation synchronization tracking"""
    __tablename__ = "documentation_syncs"
    
    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("cloud_providers.id"), nullable=False)
    sync_type = Column(String(50), nullable=False)  # full, incremental
    
    # Sync statistics
    resources_processed = Column(Integer, default=0)
    resources_created = Column(Integer, default=0)
    resources_updated = Column(Integer, default=0)
    resources_deleted = Column(Integer, default=0)
    
    # Status
    status = Column(String(20), default="running")  # running, completed, failed
    error_message = Column(Text)
    
    # Timing
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    duration_seconds = Column(Integer)
    
    # Relationships
    provider = relationship("CloudProviderModel")
    
    def __repr__(self):
        return f"<DocumentationSync(provider='{self.provider.name}', status='{self.status}')>"