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
    Render DOCX using template-driven reconstruction.
    Preserves safe zone, rebuilds content sections using template DNA.
    """
    try:
        from docx import Document
        from docx.shared import RGBColor, Pt
        
        doc = Document(str(template_path))
        mappings = mapping.mappings
        template_dna = analysis.template_dna
        
        if not template_dna:
            logger.error("No template DNA found - cannot reconstruct")
            raise RenderError("Template DNA not extracted")
        
        logger.info(f"Rendering DOCX using template reconstruction")
        logger.info(f"  Template DNA: heading='{template_dna.heading_style_name}', body='{template_dna.body_style_name}'")
        logger.info(f"  Safe zone: paras 0-{template_dna.safe_zone_end_idx}")
        logger.info(f"  First content section: para {template_dna.first_content_section_idx}")
        
        # Parse the AI response - expecting array of sections
        sections_data = mappings.get("sections", [])
        if not sections_data:
            # Fallback: check if it's the old format
            if "sec_all" in mappings:
                logger.warning("Received old format, converting to sections")
                sections_data = [{"title": "Document", "body": mappings["sec_all"]}]
            else:
                logger.error("No sections data found in mappings")
                raise RenderError("No sections found in AI response")
        
        logger.info(f"  Rebuilding with {len(sections_data)} source sections")
        
        # Step 1: Delete all paragraphs after safe zone
        paragraphs_to_remove = list(range(template_dna.safe_zone_end_idx, len(doc.paragraphs)))
        logger.info(f"  Removing {len(paragraphs_to_remove)} old content paragraphs")
        
        for idx in reversed(paragraphs_to_remove):
            if idx < len(doc.paragraphs):
                p = doc.paragraphs[idx]._element
                p.getparent().remove(p)
        
        # Step 2: Rebuild sections using template DNA
        for i, section in enumerate(sections_data):
            title = section.get("title", f"Section {i+1}")
            body = section.get("body", [])
            
            # Handle backwards compatibility - if body is a string, convert to array
            if isinstance(body, str):
                body = [{"type": "text", "content": body}]
            
            logger.info(f"  Adding section {i+1}: '{title[:40]}' ({len(body)} body items)")
            
            # Add heading with template style
            heading_para = doc.add_paragraph(title, style=template_dna.heading_style_name)
            
            # Apply heading font properties
            if heading_para.runs:
                heading_run = heading_para.runs[0]
                if template_dna.heading_font_name:
                    heading_run.font.name = template_dna.heading_font_name
                if template_dna.heading_font_size:
                    from docx.shared import Pt
                    heading_run.font.size = Pt(template_dna.heading_font_size)
                if template_dna.heading_font_bold is not None:
                    heading_run.font.bold = template_dna.heading_font_bold
                if template_dna.heading_font_color:
                    try:
                        from docx.shared import RGBColor
                        heading_run.font.color.rgb = template_dna.heading_font_color
                    except:
                        pass
            
            # Add body items based on type
            for item in body:
                item_type = item.get("type", "text")
                content = item.get("content", "")
                
                if not content:
                    continue
                
                if item_type == "subheading":
                    # Try to use subheading style, fall back to body style with bold
                    try:
                        para = doc.add_paragraph(content, style=template_dna.subheading_style_name)
                    except:
                        logger.warning(f"Subheading style '{template_dna.subheading_style_name}' not found, using body style")
                        para = doc.add_paragraph(content, style=template_dna.body_style_name)
                        if para.runs:
                            para.runs[0].font.bold = True
                    
                    # Apply formatting
                    if para.runs and template_dna.subheading_font_name:
                        para.runs[0].font.name = template_dna.subheading_font_name
                    if para.runs and template_dna.subheading_font_size:
                        from docx.shared import Pt
                        para.runs[0].font.size = Pt(template_dna.subheading_font_size)
                    elif para.runs and template_dna.body_font_size:
                        # Fall back to slightly larger body size
                        from docx.shared import Pt
                        para.runs[0].font.size = Pt(int(template_dna.body_font_size * 1.1))
                    if para.runs and template_dna.subheading_font_bold is not None:
                        para.runs[0].font.bold = template_dna.subheading_font_bold
                        
                elif item_type == "bullet":
                    # Try to use bullet style, fall back to manual bullet formatting
                    try:
                        para = doc.add_paragraph(content, style=template_dna.bullet_style_name)
                    except:
                        logger.warning(f"Bullet style '{template_dna.bullet_style_name}' not found, using manual formatting")
                        para = doc.add_paragraph(style=template_dna.body_style_name)
                        # Add bullet manually
                        para.add_run("• " + content)
                        # Indent for bullet
                        from docx.shared import Pt
                        para.paragraph_format.left_indent = Pt(18)
                        para.paragraph_format.first_line_indent = Pt(-18)
                    
                    # Apply font formatting
                    if para.runs and template_dna.bullet_font_name:
                        para.runs[0].font.name = template_dna.bullet_font_name
                    elif para.runs and template_dna.body_font_name:
                        para.runs[0].font.name = template_dna.body_font_name
                    if para.runs and template_dna.bullet_font_size:
                        from docx.shared import Pt
                        para.runs[0].font.size = Pt(template_dna.bullet_font_size)
                    elif para.runs and template_dna.body_font_size:
                        from docx.shared import Pt
                        para.runs[0].font.size = Pt(template_dna.body_font_size)
                        
                else:  # text
                    para = doc.add_paragraph(content, style=template_dna.body_style_name)
                    if para.runs:
                        if template_dna.body_font_name:
                            para.runs[0].font.name = template_dna.body_font_name
                        if template_dna.body_font_size:
                            from docx.shared import Pt
                            para.runs[0].font.size = Pt(template_dna.body_font_size)
                        if template_dna.body_font_bold is not None:
                            para.runs[0].font.bold = template_dna.body_font_bold
                        if template_dna.body_font_italic is not None:
                            para.runs[0].font.italic = template_dna.body_font_italic
            
            # Add some spacing between sections
            if i < len(sections_data) - 1:
                doc.add_paragraph()  # Empty paragraph for spacing
        
        # Save
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(output_path))
        logger.info(f"Saved reconstructed document to: {output_path}")
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
