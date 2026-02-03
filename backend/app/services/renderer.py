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


def clean_bullet_text(text: str) -> str:
    """
    Remove leading bullet markers from text to prevent duplicates.
    Handles: -, *, •, numbered lists (1., 2.), lettered lists (a., b.)
    """
    # Strip leading whitespace first
    text = text.strip()
    # Remove common bullet/list markers at the start
    patterns = [
        r'^[-*•]\s*',           # Dash, asterisk, bullet
        r'^\d+\.\s*',           # Numbered (1., 2., etc.)
        r'^[a-zA-Z]\.\s*',      # Lettered (a., b., etc.)
        r'^[a-zA-Z]\)\s*',      # Lettered with paren (a), b))
    ]
    for pattern in patterns:
        text = re.sub(pattern, '', text)
    return text.strip()


def _update_safe_zone(doc, template_dna, section_titles: list[str]):
    """
    Update the safe zone (cover page, TOC) with new content information.
    - Updates TOC entries with new section titles
    - Optionally updates cover page title
    """
    safe_zone_end = template_dna.safe_zone_end_idx
    
    # Find TOC entries and replace them
    toc_start = -1
    toc_entries = []
    
    for idx in range(safe_zone_end):
        para = doc.paragraphs[idx]
        text = para.text.strip()
        style_name = para.style.name.lower() if para.style else ""
        
        # Detect TOC heading
        if "table of contents" in text.lower() or "toc" in style_name:
            toc_start = idx
            logger.info(f"  Found TOC heading at para {idx}")
            continue
        
        # If we're past TOC heading, look for TOC entries (lines with dots/tabs)
        if toc_start >= 0 and text:
            # TOC entries typically have tabs or dotted leaders
            if "\t" in para.text or "..." in text or re.match(r'^[\d.]+\s+\w+', text):
                toc_entries.append(idx)
    
    logger.info(f"  Found {len(toc_entries)} potential TOC entries")
    
    # Replace TOC entries with new section titles
    if toc_entries and section_titles:
        for i, para_idx in enumerate(toc_entries):
            if i < len(section_titles):
                para = doc.paragraphs[para_idx]
                new_title = section_titles[i]
                # Clear and add new text with same formatting
                for run in para.runs:
                    run.text = ""
                if para.runs:
                    para.runs[0].text = f"{i+1}. {new_title}"
                else:
                    para.add_run(f"{i+1}. {new_title}")
                logger.info(f"  Updated TOC entry {i+1}: '{new_title}'")


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
        
        # Extract section titles for TOC update
        section_titles = [sec.get("title", f"Section {i+1}") for i, sec in enumerate(sections_data)]
        
        # Step 0: Update safe zone (TOC) with new section titles
        try:
            _update_safe_zone(doc, template_dna, section_titles)
        except Exception as e:
            logger.warning(f"  Failed to update safe zone: {e}")
        
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
            
            # DEBUG: Log what we received
            logger.info(f"  BEFORE dedup: {len(body)} items")
            for idx, item in enumerate(body):
                logger.info(f"    Item {idx}: type={item.get('type', 'MISSING')}, content='{item.get('content', '')[:50]}'")
            
            # DEDUPLICATION: Remove items with duplicate content
            # Strategy: If duplicates exist, prioritize "bullet" > "subheading" > "text"
            
            # 1. Group items by normalized content
            content_groups = {}
            for item in body:
                content = item.get("content", "").strip()
                if not content:
                    continue
                    
                # Normalize (remove bullets, numbers, case)
                normalized = re.sub(r'^[-*•\d.)\s]+', '', content).lower()
                
                if normalized not in content_groups:
                    content_groups[normalized] = []
                content_groups[normalized].append(item)
            
            logger.info(f"  Content groups: {len(content_groups)} unique items")
            
            # 2. Select best item for each unique content
            deduplicated_body = []
            
            # We want to preserve order, so we iterate through original body
            seen_normalized = set()
            
            for item in body:
                content = item.get("content", "").strip()
                normalized = re.sub(r'^[-*•\d.)\s]+', '', content).lower()
                
                if not normalized or normalized in seen_normalized:
                    logger.info(f"  SKIP (already seen): '{content[:30]}'")
                    continue
                
                # Get all versions of this content
                candidates = content_groups.get(normalized, [])
                
                logger.info(f"  Processing '{normalized[:30]}': {len(candidates)} candidates")
                for c in candidates:
                    logger.info(f"    Candidate: type={c.get('type')}")
                
                # Pick the best one: Bullet > Subheading > Text
                best_item = item # Default to current
                
                has_bullet = any(c.get("type") == "bullet" for c in candidates)
                has_subheading = any(c.get("type") == "subheading" for c in candidates)
                
                if has_bullet:
                    # Find the first bullet version
                    best_item = next(c for c in candidates if c.get("type") == "bullet")
                    logger.info(f"  KEEP bullet version")
                elif has_subheading:
                    # Find the first subheading version
                    best_item = next(c for c in candidates if c.get("type") == "subheading")
                    logger.info(f"  KEEP subheading version")
                else:
                    logger.info(f"  KEEP text version")
                    
                deduplicated_body.append(best_item)
                seen_normalized.add(normalized)
            
            body = deduplicated_body
            logger.info(f"  AFTER dedup: {len(body)} items")
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
                    # Clean bullet text to remove any existing markers
                    bullet_content = clean_bullet_text(content)
                    
                    # Check if bullet style exists BEFORE trying to use it
                    has_bullet_style = False
                    try:
                        # Check if style exists without adding paragraph
                        _ = doc.styles[template_dna.bullet_style_name]
                        has_bullet_style = True
                    except:
                        has_bullet_style = False
                    
                    if has_bullet_style:
                        # Style exists, use it
                        para = doc.add_paragraph(bullet_content, style=template_dna.bullet_style_name)
                    else:
                        # Style doesn't exist, use manual formatting
                        logger.warning(f"Bullet style '{template_dna.bullet_style_name}' not found, using manual formatting")
                        para = doc.add_paragraph(style=template_dna.body_style_name)
                        # Add bullet manually
                        para.add_run("• " + bullet_content)
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
