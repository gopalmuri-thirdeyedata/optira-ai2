"""
API endpoints for document transformation.
"""
import logging
import os
import uuid
import shutil
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.exceptions import (
    BaseAppException,
    UnsupportedFileTypeError,
    FileTooLargeError,
    PlaceholderNotFoundError,
    AIMapperError,
    RenderingError,
)
from app.services.parser import extract_content
from app.services.analyzer import analyze_template
from app.services.ai_mapper import map_content_to_placeholders
from app.services.renderer import render_document
from app.services.pdf_converter import convert_docx_to_pdf

router = APIRouter()
logger = logging.getLogger(__name__)


class ProcessResponse(BaseModel):
    """Response model for process endpoint."""
    success: bool
    message: str
    download_url: str | None = None
    job_id: str | None = None


class ErrorResponse(BaseModel):
    """Error response model."""
    success: bool = False
    error: str
    details: str | None = None


def get_temp_dir() -> Path:
    """Get or create temporary directory."""
    settings = get_settings()
    temp_dir = Path(settings.temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def validate_file(file: UploadFile, label: str) -> None:
    """
    Validate uploaded file.
    
    Args:
        file: The uploaded file
        label: Label for error messages (e.g., "normal_file")
        
    Raises:
        HTTPException: If validation fails
    """
    settings = get_settings()
    
    if not file.filename:
        raise HTTPException(status_code=400, detail=f"{label}: No filename provided")
    
    ext = Path(file.filename).suffix.lower()
    if ext not in settings.supported_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"{label}: Unsupported file type '{ext}'. Supported: {settings.supported_extensions}"
        )


async def save_upload(file: UploadFile, job_id: str, prefix: str) -> Path:
    """Save uploaded file to temp directory."""
    temp_dir = get_temp_dir()
    job_dir = temp_dir / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    
    ext = Path(file.filename).suffix.lower()
    file_path = job_dir / f"{prefix}{ext}"
    
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    return file_path


def cleanup_job(job_id: str) -> None:
    """Clean up temporary files for a job."""
    temp_dir = get_temp_dir()
    job_dir = temp_dir / job_id
    if job_dir.exists():
        shutil.rmtree(job_dir)


@router.post(
    "/process",
    response_model=ProcessResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    summary="Process and transform documents",
    description="Upload a source document and a template. The content from the source will be mapped to placeholders in the template."
)
async def process_documents(
    background_tasks: BackgroundTasks,
    normal_file: Annotated[UploadFile, File(description="Source document (DOCX, PDF, or PPTX)")],
    target_file: Annotated[UploadFile, File(description="Template document with {{PLACEHOLDERS}} (DOCX or PPTX)")],
    output_format: Annotated[Literal["docx", "pdf"], Form(description="Output format: 'docx' for Word document, 'pdf' for PDF")] = "docx",
):
    """
    Process documents by extracting content from normal_file and
    replacing placeholders in target_file.
    
    The target_file acts as a template and MUST contain placeholders
    in the format {{KEY_NAME}}.
    
    Returns a download URL for the processed document.
    """
    job_id = str(uuid.uuid4())
    
    try:
        # Validate files
        validate_file(normal_file, "normal_file")
        validate_file(target_file, "target_file")
        
        # Save uploaded files
        source_path = await save_upload(normal_file, job_id, "source")
        template_path = await save_upload(target_file, job_id, "template")
        
        # Step 1: Extract content from source document
        extracted_content = extract_content(source_path)
        
        if not extracted_content.blocks:
            raise HTTPException(
                status_code=400,
                detail="No content could be extracted from the source document"
            )
        
        # Step 2: Analyze template for sections (heading + body pairs)
        template_analysis = analyze_template(template_path)
        
        # Step 3: Map content to sections using AI
        content_mapping = await map_content_to_placeholders(
            extracted_content,
            template_analysis
        )
        
        # Step 4: Render the final document with style-preserving injection
        output_filename = f"output_{Path(target_file.filename).stem}{template_path.suffix}"
        output_path = get_temp_dir() / job_id / output_filename
        
        render_document(
            template_path, 
            output_path, 
            content_mapping,
            template_analysis
        )
        
        # Step 5: Convert to PDF if requested
        final_path = output_path
        final_filename = output_filename
        
        if output_format == "pdf":
            logger.info("PDF output format requested, converting DOCX to PDF")
            pdf_filename = f"output_{Path(target_file.filename).stem}.pdf"
            pdf_path = get_temp_dir() / job_id / pdf_filename
            
            try:
                await convert_docx_to_pdf(output_path, pdf_path)
                final_path = pdf_path
                final_filename = pdf_filename
                logger.info(f"PDF conversion successful: {pdf_filename}")
            except Exception as e:
                logger.error(f"PDF conversion failed: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"PDF conversion failed: {str(e)}"
                )
        
        return ProcessResponse(
            success=True,
            message="Document processed successfully",
            download_url=f"/api/download/{job_id}/{final_filename}",
            job_id=job_id
        )
        
    except PlaceholderNotFoundError as e:
        cleanup_job(job_id)
        raise HTTPException(status_code=400, detail=str(e.message))
    except UnsupportedFileTypeError as e:
        cleanup_job(job_id)
        raise HTTPException(status_code=400, detail=str(e.message))
    except AIMapperError as e:
        cleanup_job(job_id)
        raise HTTPException(status_code=500, detail=f"AI mapping failed: {e.message}")
    except RenderingError as e:
        cleanup_job(job_id)
        raise HTTPException(status_code=500, detail=f"Rendering failed: {e.message}")
    except BaseAppException as e:
        cleanup_job(job_id)
        raise HTTPException(status_code=500, detail=str(e.message))
    except HTTPException:
        cleanup_job(job_id)
        raise
    except Exception as e:
        cleanup_job(job_id)
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.get(
    "/download/{job_id}/{filename}",
    summary="Download processed document",
    description="Download the processed document by job ID and filename."
)
async def download_document(
    job_id: str,
    filename: str,
    background_tasks: BackgroundTasks
):
    """Download a processed document."""
    temp_dir = get_temp_dir()
    file_path = temp_dir / job_id / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found or expired")
    
    # Schedule cleanup after download
    background_tasks.add_task(cleanup_job, job_id)
    
    # Determine media type
    ext = file_path.suffix.lower()
    media_types = {
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".pdf": "application/pdf",
    }
    media_type = media_types.get(ext, "application/octet-stream")
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type=media_type
    )


@router.get(
    "/health",
    summary="Health check",
    description="Check if the API is running."
)
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "Optira Document Transformer"}
