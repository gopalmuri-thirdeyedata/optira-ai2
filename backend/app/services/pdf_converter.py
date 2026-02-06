"""
PDF conversion service using ConvertAPI.
Converts DOCX files to PDF format using cloud API.
"""
import logging
from pathlib import Path
import httpx

from app.core.config import get_settings
from app.core.exceptions import RenderingError

logger = logging.getLogger(__name__)


class PDFConversionError(RenderingError):
    """Exception raised when PDF conversion fails."""
    pass


async def convert_docx_to_pdf(docx_path: Path, pdf_path: Path) -> Path:
    """
    Convert a DOCX file to PDF using ConvertAPI.
    
    ConvertAPI provides a simple REST API:
    POST https://v2.convertapi.com/convert/docx/to/pdf?Secret=YOUR_SECRET
    
    Args:
        docx_path: Path to source DOCX file
        pdf_path: Path where PDF should be saved
        
    Returns:
        Path to the generated PDF file
        
    Raises:
        PDFConversionError: If conversion fails
    """
    settings = get_settings()
    
    if not settings.convertapi_secret:
        raise PDFConversionError(
            "CONVERTAPI_SECRET not configured. Please add it to your .env file."
        )
    
    logger.info(f"Converting {docx_path.name} to PDF using ConvertAPI")
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            # ConvertAPI endpoint and authentication
            api_url = "https://v2.convertapi.com/convert/docx/to/pdf"
            headers = {
                "Authorization": f"Bearer {settings.convertapi_secret}"
            }
            
            # Upload file
            logger.info("Uploading DOCX and requesting conversion")
            with open(docx_path, "rb") as f:
                files = {
                    "File": (docx_path.name, f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
                }
                data = {
                    "StoreFile": "true"
                }
                
                response = await client.post(api_url, headers=headers, files=files, data=data)
                response.raise_for_status()
            
            result = response.json()
            
            # ConvertAPI response structure: {"Files": [{"FileName": "...", "FileSize": ..., "Url": "..."}]}
            # Get download URL from response
            if "Files" not in result or len(result["Files"]) == 0:
                logger.error(f"Unexpected response structure: {result}")
                raise PDFConversionError("No files in conversion response")
            
            file_info = result["Files"][0]
            download_url = file_info.get("Url") or file_info.get("url") or file_info.get("FileData")
            
            if not download_url:
                logger.error(f"No download URL found in file info: {file_info}")
                raise PDFConversionError(f"No download URL in response. Available keys: {list(file_info.keys())}")
            
            logger.info(f"Conversion successful, downloading from: {download_url}")
            
            # Download PDF
            pdf_response = await client.get(download_url)
            pdf_response.raise_for_status()
            
            # Save PDF file
            pdf_path.parent.mkdir(parents=True, exist_ok=True)
            with open(pdf_path, "wb") as f:
                f.write(pdf_response.content)
            
            logger.info(f"PDF saved successfully to: {pdf_path}")
            return pdf_path
            
    except httpx.HTTPStatusError as e:
        error_detail = f"HTTP {e.response.status_code}"
        try:
            error_json = e.response.json()
            error_detail = f"{error_detail}: {error_json}"
        except Exception:
            error_detail = f"{error_detail}: {e.response.text}"
        
        raise PDFConversionError(
            f"API request failed: {error_detail}",
            details=str(e)
        )
    except Exception as e:
        raise PDFConversionError(
            f"PDF conversion failed: {str(e)}",
            details=str(e)
        )
