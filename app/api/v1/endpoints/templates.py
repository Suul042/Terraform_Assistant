"""
Template Management Endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
import logging

from app.core.config import get_settings
from app.models.schemas import (
    TemplateResponse,
    TemplateListResponse,
    TemplateCreateRequest
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=TemplateListResponse)
async def list_templates(
    provider: Optional[str] = None,
    category: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    settings=Depends(get_settings)
):
    """
    List available Terraform templates

    Args:
        provider: Filter by cloud provider (aws, azure, gcp)
        category: Filter by category (compute, network, storage, etc.)
        page: Page number
        page_size: Items per page

    Returns:
        List of templates with pagination
    """
    try:
        # TODO: Implement actual database query
        # For now, return sample templates
        sample_templates = [
            {
                "id": "aws-ec2-basic",
                "name": "Basic EC2 Instance",
                "description": "Simple EC2 instance with security group",
                "provider": "aws",
                "category": "compute",
                "tags": ["ec2", "compute", "basic"]
            },
            {
                "id": "aws-vpc-standard",
                "name": "Standard VPC",
                "description": "VPC with public and private subnets",
                "provider": "aws",
                "category": "network",
                "tags": ["vpc", "network", "subnets"]
            },
            {
                "id": "azure-vm-basic",
                "name": "Basic Azure VM",
                "description": "Azure virtual machine with network interface",
                "provider": "azure",
                "category": "compute",
                "tags": ["vm", "compute", "azure"]
            },
            {
                "id": "gcp-compute-basic",
                "name": "Basic GCP Compute Instance",
                "description": "Google Cloud compute instance",
                "provider": "gcp",
                "category": "compute",
                "tags": ["compute", "gcp", "vm"]
            }
        ]

        # Filter templates
        filtered_templates = sample_templates
        if provider:
            filtered_templates = [
                t for t in filtered_templates if t["provider"] == provider
            ]
        if category:
            filtered_templates = [
                t for t in filtered_templates if t["category"] == category
            ]

        # Pagination
        start = (page - 1) * page_size
        end = start + page_size
        paginated_templates = filtered_templates[start:end]

        return TemplateListResponse(
            templates=paginated_templates,
            total=len(filtered_templates),
            page=page,
            page_size=page_size
        )

    except Exception as e:
        logger.error(f"Failed to list templates: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list templates: {str(e)}"
        )


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(template_id: str):
    """
    Get a specific template by ID

    Args:
        template_id: Template identifier

    Returns:
        Template details with code
    """
    try:
        # TODO: Implement actual database query
        # For now, return a sample template
        if template_id == "aws-ec2-basic":
            return TemplateResponse(
                id=template_id,
                name="Basic EC2 Instance",
                description="Simple EC2 instance with security group",
                provider="aws",
                category="compute",
                code='''resource "aws_instance" "example" {
  ami           = var.ami_id
  instance_type = var.instance_type

  tags = {
    Name = var.instance_name
  }
}

resource "aws_security_group" "example" {
  name        = "${var.instance_name}-sg"
  description = "Security group for ${var.instance_name}"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}''',
                variables={
                    "ami_id": {
                        "type": "string",
                        "description": "AMI ID for the EC2 instance"
                    },
                    "instance_type": {
                        "type": "string",
                        "default": "t3.micro",
                        "description": "EC2 instance type"
                    },
                    "instance_name": {
                        "type": "string",
                        "description": "Name tag for the instance"
                    }
                },
                tags=["ec2", "compute", "basic"]
            )

        raise HTTPException(status_code=404, detail="Template not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get template: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get template: {str(e)}"
        )


@router.post("/", response_model=TemplateResponse, status_code=201)
async def create_template(request: TemplateCreateRequest):
    """
    Create a new template

    Args:
        request: Template creation request

    Returns:
        Created template
    """
    try:
        # TODO: Implement actual database insertion
        logger.info(f"Creating template: {request.name}")

        # For now, return the request as a response
        return TemplateResponse(
            id=f"custom-{request.name.lower().replace(' ', '-')}",
            name=request.name,
            description=request.description,
            provider=request.provider,
            category=request.category,
            code=request.code,
            variables=request.variables or {},
            tags=request.tags or []
        )

    except Exception as e:
        logger.error(f"Failed to create template: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create template: {str(e)}"
        )
