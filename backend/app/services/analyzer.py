"""
Template analyzer for target documents.
Uses section-based analysis: identifies Heading + Body pairs to create semantic sections.
"""
import logging
import re
from pathlib import Path
from typing import Literal, Any

from pydantic import BaseModel

from app.core.exceptions import (
    ParsingError, 
    UnsupportedFileTypeError
)

logger = logging.getLogger(__name__)


class TemplateSection(BaseModel):
    """A section in the template: heading + body content."""
    section_id: str
    heading_text: str
    heading_paragraph_idx: int  # Index of heading paragraph
    body_start_idx: int  # First body paragraph index
    body_end_idx: int  # Last body paragraph index (exclusive)
    body_preview: str  # First ~100 chars of body for context
    section_type: Literal["title", "section", "subsection"]


class TemplateAnalysis(BaseModel):
    """Result of template section analysis."""
    sections: list[TemplateSection]
    section_ids: list[str]
    template_file: str
    total_paragraphs: int


def analyze_template(file_path: Path) -> TemplateAnalysis:
    """
    Analyze a template document to detect sections (Heading + Body pairs).
    
    Args:
        file_path: Path to the template document
        
    Returns:
        TemplateAnalysis with detected sections
    """
    suffix = file_path.suffix.lower()
    
    if suffix == ".docx":
        return _analyze_docx_sections(file_path)
    elif suffix == ".pptx":
        return _analyze_pptx_sections(file_path)
    elif suffix == ".pdf":
        return _analyze_pdf_sections(file_path)
    else:
        raise UnsupportedFileTypeError(f"Unsupported template type: {suffix}")


def _analyze_docx_sections(file_path: Path) -> TemplateAnalysis:
    """
    Analyze DOCX template for sections based on heading styles.
    A section = Heading paragraph + all subsequent paragraphs until next heading.
    """
    try:
        from docx import Document
        
        doc = Document(str(file_path))
        sections: list[TemplateSection] = []
        section_ids: list[str] = []
        
        total_paras = len(doc.paragraphs)
        heading_indices: list[tuple[int, str, str]] = []  # (idx, text, type)
        
        logger.info(f"Analyzing DOCX template: {file_path.name} ({total_paras} paragraphs)")
        
        # First pass: find all headings
        for idx, para in enumerate(doc.paragraphs):
            text = para.text.strip()
            style_name = para.style.name if para.style else "None"
            
            if text:
                logger.debug(f"  Para {idx}: style='{style_name}', text='{text[:50]}...'")
            
            if not text:
                continue
            
            style_lower = style_name.lower()
            
            if "title" in style_lower:
                heading_indices.append((idx, text, "title"))
                logger.info(f"  Found TITLE at para {idx}: '{text[:50]}'")
            elif "heading 1" in style_lower:
                heading_indices.append((idx, text, "section"))
                logger.info(f"  Found HEADING 1 at para {idx}: '{text[:50]}'")
            elif "heading" in style_lower:
                heading_indices.append((idx, text, "subsection"))
                logger.info(f"  Found HEADING at para {idx}: '{text[:50]}'")
        
        logger.info(f"  Total headings found: {len(heading_indices)}")
        
        # Second pass: create sections from headings
        for i, (h_idx, h_text, h_type) in enumerate(heading_indices):
            # Determine body range
            body_start = h_idx + 1
            if i + 1 < len(heading_indices):
                body_end = heading_indices[i + 1][0]
            else:
                body_end = total_paras
            
            # Get body preview
            body_preview = ""
            for b_idx in range(body_start, min(body_start + 3, body_end)):
                para_text = doc.paragraphs[b_idx].text.strip()
                if para_text:
                    body_preview += para_text + " "
                    if len(body_preview) > 100:
                        break
            body_preview = body_preview[:150].strip()
            
            section_id = f"sec_{i}"
            sections.append(TemplateSection(
                section_id=section_id,
                heading_text=h_text,
                heading_paragraph_idx=h_idx,
                body_start_idx=body_start,
                body_end_idx=body_end,
                body_preview=body_preview,
                section_type=h_type
            ))
            section_ids.append(section_id)
            
            logger.info(f"  Section '{section_id}': heading='{h_text[:30]}', body_range=[{body_start}, {body_end})")
        
        # If no sections found, treat entire document as one section
        if not sections:
            logger.warning("  No headings found! Creating single generic section for entire document.")
            first_text = ""
            for para in doc.paragraphs:
                if para.text.strip():
                    first_text = para.text.strip()
                    break
            
            sections.append(TemplateSection(
                section_id="sec_0",
                heading_text=first_text[:50] if first_text else "Document",
                heading_paragraph_idx=0,
                body_start_idx=1,
                body_end_idx=total_paras,
                body_preview="",
                section_type="section"
            ))
            section_ids.append("sec_0")
        
        logger.info(f"  Final sections: {section_ids}")
        
        return TemplateAnalysis(
            sections=sections,
            section_ids=section_ids,
            template_file=file_path.name,
            total_paragraphs=total_paras
        )
        
    except Exception as e:
        raise ParsingError(f"Failed to analyze DOCX sections: {str(e)}", details=str(e))


def _analyze_pptx_sections(file_path: Path) -> TemplateAnalysis:
    """
    Analyze PPTX template: each slide is a section.
    """
    try:
        from pptx import Presentation
        
        prs = Presentation(str(file_path))
        sections: list[TemplateSection] = []
        section_ids: list[str] = []
        
        for slide_idx, slide in enumerate(prs.slides):
            title_text = f"Slide {slide_idx + 1}"
            body_preview = ""
            
            for shape in slide.shapes:
                if not shape.has_text_frame:
                    continue
                
                text = shape.text_frame.text.strip()
                if not text:
                    continue
                
                # Check if title
                is_title = False
                if hasattr(shape, "placeholder_format") and shape.placeholder_format:
                    ph_type = shape.placeholder_format.type
                    if ph_type in [1, 2, 3]:
                        is_title = True
                        title_text = text
                
                if not is_title and not body_preview:
                    body_preview = text[:100]
            
            section_id = f"slide_{slide_idx}"
            sections.append(TemplateSection(
                section_id=section_id,
                heading_text=title_text,
                heading_paragraph_idx=slide_idx,
                body_start_idx=slide_idx,
                body_end_idx=slide_idx + 1,
                body_preview=body_preview,
                section_type="section"
            ))
            section_ids.append(section_id)
        
        return TemplateAnalysis(
            sections=sections,
            section_ids=section_ids,
            template_file=file_path.name,
            total_paragraphs=len(prs.slides)
        )
        
    except Exception as e:
        raise ParsingError(f"Failed to analyze PPTX sections: {str(e)}", details=str(e))


def _analyze_pdf_sections(file_path: Path) -> TemplateAnalysis:
    """
    Analyze PDF template: basic page-based sections.
    Note: PDF modification is limited, this is for read purposes.
    """
    try:
        import fitz
        
        doc = fitz.open(str(file_path))
        sections: list[TemplateSection] = []
        section_ids: list[str] = []
        
        for page_idx, page in enumerate(doc):
            text = page.get_text()
            lines = text.strip().split('\n')
            
            title = lines[0][:50] if lines else f"Page {page_idx + 1}"
            body_preview = ' '.join(lines[1:5])[:100] if len(lines) > 1 else ""
            
            section_id = f"page_{page_idx}"
            sections.append(TemplateSection(
                section_id=section_id,
                heading_text=title,
                heading_paragraph_idx=page_idx,
                body_start_idx=page_idx,
                body_end_idx=page_idx + 1,
                body_preview=body_preview,
                section_type="section"
            ))
            section_ids.append(section_id)
        
        doc.close()
        
        return TemplateAnalysis(
            sections=sections,
            section_ids=section_ids,
            template_file=file_path.name,
            total_paragraphs=len(sections)
        )
        
    except Exception as e:
        raise ParsingError(f"Failed to analyze PDF sections: {str(e)}", details=str(e))


def get_section_descriptions(analysis: TemplateAnalysis) -> str:
    """
    Generate descriptions of template sections for AI prompt.
    """
    lines = []
    for sec in analysis.sections:
        context = f" (Context: '{sec.body_preview[:80]}...')" if sec.body_preview else ""
        lines.append(f"- {sec.section_id}: \"{sec.heading_text}\"{context}")
    
    return "\n".join(lines)
