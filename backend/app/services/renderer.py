"""
Content replacement engine for template documents.
Performs style-preserving section injection: replaces section body content while
preserving the template's heading styles, fonts, header/footer, images, and layout.
"""
import logging
import re
from pathlib import Path
from typing import Any, Optional

from app.core.exceptions import RenderingError, UnsupportedFileTypeError
from app.services.ai_mapper import SectionMapping
from app.services.analyzer import TemplateAnalysis

logger = logging.getLogger(__name__)


def render_document(
    template_path: Path,
    output_path: Path,
    mapping: SectionMapping,
    analysis: TemplateAnalysis
) -> Path:
    """
    Replace section body content in template with mapped content.
    Preserves all template formatting, headers, footers, images.
    
    Args:
        template_path: Path to the template document
        output_path: Path where the rendered document will be saved
        mapping: Section-to-content mapping from AI
        analysis: Template analysis with section info
        
    Returns:
        Path to the rendered document
    """
    suffix = template_path.suffix.lower()
    
    if suffix == ".docx":
        return _render_docx_sections(template_path, output_path, mapping, analysis)
    elif suffix == ".pptx":
        return _render_pptx_sections(template_path, output_path, mapping, analysis)
    elif suffix == ".pdf":
        raise UnsupportedFileTypeError(
            "PDF template replacement is not directly supported. "
            "Consider using a DOCX template and converting to PDF."
        )
    else:
        raise UnsupportedFileTypeError(f"Unsupported template type: {suffix}")


def _render_docx_sections(
    template_path: Path,
    output_path: Path,
    mapping: SectionMapping,
    analysis: TemplateAnalysis
) -> Path:
    """
    Render DOCX template with section-based content replacement.
    """
    try:
        from docx import Document
        from docx.shared import Pt
        
        doc = Document(str(template_path))
        paragraphs = doc.paragraphs
        mappings = mapping.mappings
        
        logger.info(f"Rendering DOCX: {len(paragraphs)} paragraphs, {len(analysis.sections)} sections")
        logger.info(f"Mappings received: {list(mappings.keys())}")
        
        # Process sections in reverse order to avoid index shifting
        for section in reversed(analysis.sections):
            section_id = section.section_id
            new_content = mappings.get(section_id, "")
            
            logger.info(f"Processing section '{section_id}': heading='{section.heading_text[:30]}', body=[{section.body_start_idx}, {section.body_end_idx})")
            logger.info(f"  New content ({len(new_content)} chars): '{new_content[:80]}...'")
            
            if not new_content:
                logger.warning(f"  Skipping section '{section_id}' - no content to insert")
                continue
            
            body_start = section.body_start_idx
            body_end = section.body_end_idx
            
            if body_start >= len(paragraphs):
                logger.warning(f"  Skipping section '{section_id}' - body_start {body_start} >= total paras {len(paragraphs)}")
                continue
            
            # Get the style from the first body paragraph
            body_style = None
            body_font_name = None
            body_font_size = None
            
            if body_start < len(paragraphs):
                first_body = paragraphs[body_start]
                body_style = first_body.style
                logger.info(f"  First body para style: {body_style.name if body_style else 'None'}")
                if first_body.runs:
                    first_run = first_body.runs[0]
                    if first_run.font.name:
                        body_font_name = first_run.font.name
                    if first_run.font.size:
                        body_font_size = first_run.font.size
                    logger.info(f"  First body font: {body_font_name}, size: {body_font_size}")
            
            # Clear body paragraphs
            cleared_count = 0
            for idx in range(body_start, min(body_end, len(paragraphs))):
                para = paragraphs[idx]
                for run in para.runs:
                    run.text = ""
                cleared_count += 1
            logger.info(f"  Cleared {cleared_count} body paragraphs")
            
            # Insert new content into the first body paragraph
            if body_start < len(paragraphs):
                target_para = paragraphs[body_start]
                
                # Split content by double newlines for paragraph breaks
                content_parts = new_content.split("\n\n")
                logger.info(f"  Inserting {len(content_parts)} content parts")
                
                # First part goes into existing paragraph
                if content_parts:
                    if target_para.runs:
                        target_para.runs[0].text = content_parts[0]
                        if body_font_name:
                            target_para.runs[0].font.name = body_font_name
                        if body_font_size:
                            target_para.runs[0].font.size = body_font_size
                        logger.info(f"  Set first para text ({len(content_parts[0])} chars)")
                    else:
                        run = target_para.add_run(content_parts[0])
                        if body_font_name:
                            run.font.name = body_font_name
                        if body_font_size:
                            run.font.size = body_font_size
                        logger.info(f"  Added run with text ({len(content_parts[0])} chars)")
                
                # Additional parts: use subsequent empty paragraphs
                for i, part in enumerate(content_parts[1:], start=1):
                    next_idx = body_start + i
                    if next_idx < min(body_end, len(paragraphs)):
                        next_para = paragraphs[next_idx]
                        if next_para.runs:
                            next_para.runs[0].text = part
                        else:
                            run = next_para.add_run(part)
                            if body_style:
                                next_para.style = body_style
                        logger.info(f"  Set para {next_idx} text ({len(part)} chars)")
        
        # Save
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(output_path))
        logger.info(f"Saved rendered document to: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Rendering failed: {e}")
        raise RenderingError(f"Failed to render DOCX: {str(e)}", details=str(e))


def _render_pptx_sections(
    template_path: Path,
    output_path: Path,
    mapping: SectionMapping,
    analysis: TemplateAnalysis
) -> Path:
    """
    Render PPTX template with section-based content replacement.
    Each slide = one section. Replace body text while keeping title and layout.
    """
    try:
        from pptx import Presentation
        
        prs = Presentation(str(template_path))
        mappings = mapping.mappings
        
        for section in analysis.sections:
            section_id = section.section_id
            new_content = mappings.get(section_id, "")
            
            if not new_content:
                continue
            
            # Extract slide index from section_id (e.g., "slide_0" -> 0)
            if not section_id.startswith("slide_"):
                continue
            
            try:
                slide_idx = int(section_id.split("_")[1])
            except (ValueError, IndexError):
                continue
            
            if slide_idx >= len(prs.slides):
                continue
            
            slide = prs.slides[slide_idx]
            
            # Find body shapes (non-title text frames)
            for shape in slide.shapes:
                if not shape.has_text_frame:
                    continue
                
                # Skip title shapes
                is_title = False
                if hasattr(shape, "placeholder_format") and shape.placeholder_format:
                    ph_type = shape.placeholder_format.type
                    if ph_type in [1, 2, 3]:
                        is_title = True
                
                if not is_title:
                    # Replace body text
                    tf = shape.text_frame
                    if tf.paragraphs:
                        # Get style from first paragraph
                        first_para = tf.paragraphs[0]
                        
                        # Set content in first paragraph
                        if first_para.runs:
                            first_para.runs[0].text = new_content
                            for run in first_para.runs[1:]:
                                run.text = ""
                        else:
                            first_para.text = new_content
                        
                        # Clear other paragraphs
                        for para in tf.paragraphs[1:]:
                            for run in para.runs:
                                run.text = ""
                    
                    # Only replace first body shape per slide
                    break
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        prs.save(str(output_path))
        return output_path
        
    except Exception as e:
        raise RenderingError(f"Failed to render PPTX: {str(e)}", details=str(e))
