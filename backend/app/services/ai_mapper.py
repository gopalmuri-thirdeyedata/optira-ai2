"""
AI Mapper using Groq LLM for semantic section mapping.
Maps source content blocks to template sections based on meaning.
"""
import json
import logging
from typing import Any, Literal

from groq import Groq
from pydantic import BaseModel, ValidationError

from app.core.config import get_settings
from app.core.exceptions import AIMapperError, AIResponseValidationError, GroqAPIError
from app.services.parser import ExtractedContent, content_to_text_summary
from app.services.analyzer import TemplateAnalysis, get_section_descriptions

logger = logging.getLogger(__name__)


class SectionMapping(BaseModel):
    """Validated mapping of section IDs to content."""
    mappings: dict[str, Any]


def create_section_mapping_prompt(
    content: ExtractedContent,
    analysis: TemplateAnalysis
) -> str:
    """
    Create prompt for AI to convert flat or semi-structured source content
    into deterministic, template-ready sections.
    """

    content_text = content_to_text_summary(content)

    prompt = f"""
You are a document structure parser, NOT a writer.

Your task is to convert raw source content into a clean, structured JSON format
that can be injected into a predefined company document template.

You must preserve meaning exactly. Do NOT summarize, rewrite, or embellish.

---

## PRIMARY OBJECTIVE
Convert the source content into an ordered list of Sections.
Each Section MUST have:
- a "title"
- a "body" array of structured content blocks

This output will be mapped directly into a document template.
Accuracy and stability are more important than creativity.

---

## SOURCE CONTENT CHARACTERISTICS
The source text may be:
- completely flat
- poorly formatted
- missing headings
- a wall of text
- loosely structured prose

You MUST infer structure carefully, conservatively, and consistently.

---

## SECTION INFERENCE RULES (VERY IMPORTANT)

### 0. Document Title Detection (FIRST PRIORITY – BEFORE Section Inference)

If the FIRST non-empty line appears to be a meaningful document title, you MUST use it as the first section title.

Treat the first line as a title only when:
- it is short (typically < 12–15 words)
- it is standalone
- it is not a paragraph
- it clearly represents the whole document

---

### 0.1 Title Consumption (MANDATORY)

When a title is detected:

- Remove it completely from the content before parsing begins
- Do NOT include it again inside any section body
- Do NOT convert it into text/subheading/bullet
- It must appear ONLY once as the section title

Parsing MUST start strictly AFTER the title line.

---

### 0.2 Sequential Parsing (MANDATORY – DO NOT REORDER) ⚠️ CRITICAL

Process the document STRICTLY from top to bottom.
This is the MOST IMPORTANT rule. Violating this rule is a CRITICAL FAILURE.

ABSOLUTELY NEVER:
- regroup content by topic
- reorganize by semantic meaning
- move paragraphs to different positions
- place middle content at the end
- place end content in the middle
- merge text from distant parts of the document
- "optimize" the order in any way
- "improve" the structure

If line A appears before line B in the source,
line A MUST appear before line B in output.

If paragraph X is in the middle of the source,
paragraph X MUST be in the middle of the output.

EXAMPLE:
Source order: Name → Contact → Summary → Experience → Education
Output order: Name → Contact → Summary → Experience → Education

WRONG output: Name → Summary → Experience → Education → Contact (shuffled!)

Order preservation is ABSOLUTE and NON-NEGOTIABLE.

---

### 0.3 Title Validation (ANTI-GENERIC SAFETY)

Generic labels are NOT valid titles.

Words like:
- Document
- Resume
- CV
- File
- Report
- Page
- Template
- Draft
- Notes
- Form
- Data

are NOT meaningful titles IF they appear standalone.

If the first non-empty line is EXACTLY one of these words, you MUST ignore it and look for the next line.
If it is part of a longer meaningful title (e.g. "Project Report 2024" or "Software Engineer Resume"), it is a VALID title and you should use it.

---

### 0.4 Line-by-Line Streaming Parse (STRICT)

Parse incrementally:

- read one line
- assign immediately
- move to next line

NEVER analyze the whole document first.
NEVER batch or restructure.

This guarantees zero shuffling.

---

### 0.5 Title Hard Rejection (STRICT – MUST NOT USE GENERIC WORDS)

If the first line equals or mostly consists of generic placeholders such as:

Document, Resume, CV, File, Report, Page, Template, Draft, Form, Data

You MUST:

1. Skip the line completely
2. NOT use it as a title
3. NOT output it anywhere
4. Continue scanning for the next meaningful line

These words are metadata only.

Under NO circumstances may they be used as section titles.

If a person's name or meaningful heading appears next, use THAT.
A title is rejected ONLY if it is a single standalone generic word.

---

### 0.6 Resume/CV Special Handling (CRITICAL FOR RESUMES)

For RESUME or CV documents:
- The FIRST SECTION TITLE should be the PERSON'S FULL NAME (not "Resume", "CV", or "Document")
- Look for a name-like pattern: typically 2-4 capitalized words at or near the beginning
- Examples of VALID first section titles for resumes:
  - "John Smith"
  - "Sarah Jane Johnson"
  - "Gopal Murthy"
  
If the document appears to be a resume (contains keywords like: experience, education, skills, qualifications, employment history):
- FIND the person's name and use it as the first section title
- Skip any generic labels that appear before the name

---

### 1. Section Titles
Infer a section title ONLY when there is strong evidence:
- a short standalone line
- a clear topic shift
- a repeated thematic phrase
- a commonly expected document section (e.g. Introduction, Overview, Conclusion)

If unsure, prefer SAFE, GENERIC titles such as:
- "Introduction"
- "Overview"
- "Details"
- "Additional Information"

DO NOT invent overly specific or creative titles.

---

### 2. Body Content Types
Each body item MUST be one of the following types:

- "text"  
  → Standard paragraph content.

- "subheading"  
  → Minor internal headings inside a section.

- "bullet"  
  → List items.

---

### 3. Paragraph Splitting
- Break long paragraphs only when necessary
- Do NOT fragment sentences
- Maintain order strictly

---

## STRICT RULES (NON-NEGOTIABLE)
1. **VERBATIM CONTENT**: Copy text EXACTLY as it appears in the source. Do NOT rephrase, paraphrase, or improve wording.
2. Preserve ALL original meaning and wording CHARACTER BY CHARACTER.
3. DO NOT summarize or shorten content.
4. DO NOT add new facts, interpretations, or infer content that is not explicitly stated.
5. DO NOT repeat content.
6. Maintain EXACT original order.
7. NEVER reorganize structure.
8. If structure is ambiguous, default to "text" type. Do NOT invent subheadings that aren't in the source.
9. Output MUST be valid JSON.
10. Output MUST match the required schema exactly.

---

## SOURCE CONTENT
{content_text}

---

## REQUIRED OUTPUT FORMAT (JSON ONLY)

[
  {{
    "title": "Section Title",
    "body": [
      {{
        "type": "text",
        "content": "Paragraph text exactly as derived from source."
      }},
      {{
        "type": "subheading",
        "content": "Sub-section title"
      }},
      {{
        "type": "bullet",
        "content": "Bullet item text"
      }}
    ]
  }}
]

⚠️ FINAL REMINDER: The output MUST follow the EXACT SAME ORDER as the source content.
Do NOT shuffle, reorganize, or reorder any content. First item in source = first item in output.

Return ONLY the JSON array. No explanations. No markdown. No extra text.
"""
    return prompt






def _chunk_content_blocks(blocks: list, chunk_size: int = 25) -> list[list]:
    """
    Split content blocks into chunks for processing long documents.
    
    Args:
        blocks: List of ContentBlock objects
        chunk_size: Maximum number of blocks per chunk
        
    Returns:
        List of chunk lists
    """
    if len(blocks) <= chunk_size:
        return [blocks]
    
    chunks = []
    for i in range(0, len(blocks), chunk_size):
        chunk = blocks[i:i + chunk_size]
        chunks.append(chunk)
    
    logger.info(f"Split {len(blocks)} blocks into {len(chunks)} chunks of ~{chunk_size} blocks each")
    return chunks


def _merge_section_mappings(all_sections: list[list[dict]]) -> list[dict]:
    """
    Merge section mappings from multiple chunks.
    
    Strategy: 
    1. First, merge adjacent sections across chunk boundaries
    2. Then, deduplicate sections with the same title globally
    
    Args:
        all_sections: List of section lists from each chunk
        
    Returns:
        Merged and deduplicated list of sections
    """
    if not all_sections:
        return []
    
    if len(all_sections) == 1:
        return all_sections[0]
    
    # Step 1: Merge adjacent sections across chunk boundaries
    merged = []
    
    for i, chunk_sections in enumerate(all_sections):
        if not chunk_sections:
            continue
            
        if i == 0:
            # First chunk: add all sections
            merged.extend(chunk_sections)
        else:
            # Check if we need to merge with the last section from previous chunk
            if merged and chunk_sections:
                last_section = merged[-1]
                first_section = chunk_sections[0]
                
                # Normalize titles for comparison (lowercase, strip)
                last_title = last_section.get("title", "").lower().strip()
                first_title = first_section.get("title", "").lower().strip()
                
                if last_title and first_title and last_title == first_title:
                    # Merge bodies
                    logger.info(f"  Merging section across chunks: '{last_section.get('title', '')}'")
                    last_body = last_section.get("body", [])
                    first_body = first_section.get("body", [])
                    
                    if isinstance(last_body, str):
                        last_body = [{"type": "text", "content": last_body}]
                    if isinstance(first_body, str):
                        first_body = [{"type": "text", "content": first_body}]
                    
                    # Merge bodies
                    merged[-1]["body"] = last_body + first_body
                    
                    # Add remaining sections from this chunk (skip first since we merged it)
                    merged.extend(chunk_sections[1:])
                else:
                    # No merge needed, just append all sections
                    merged.extend(chunk_sections)
            else:
                # No previous sections, just append
                merged.extend(chunk_sections)
    
    logger.info(f"Merged {len(all_sections)} chunks into {len(merged)} sections")
    
    # Step 2: Global deduplication - merge all sections with the same title
    deduplicated = []
    seen_titles = {}  # Map of normalized title -> index in deduplicated list
    
    for section in merged:
        title = section.get("title", "")
        normalized_title = title.lower().strip()
        
        if normalized_title in seen_titles:
            # Merge with existing section
            existing_idx = seen_titles[normalized_title]
            logger.info(f"  Deduplicating section: '{title}' (merging into previous occurrence)")
            
            existing_body = deduplicated[existing_idx].get("body", [])
            new_body = section.get("body", [])
            
            if isinstance(existing_body, str):
                existing_body = [{"type": "text", "content": existing_body}]
            if isinstance(new_body, str):
                new_body = [{"type": "text", "content": new_body}]
            
            # Merge bodies
            deduplicated[existing_idx]["body"] = existing_body + new_body
        else:
            # First occurrence of this title
            seen_titles[normalized_title] = len(deduplicated)
            deduplicated.append(section)
    
    logger.info(f"After deduplication: {len(deduplicated)} unique sections")
    return deduplicated



async def map_content_to_sections(
    content: ExtractedContent,
    analysis: TemplateAnalysis,
    max_retries: int = 2,
    chunk_size: int = 25
) -> SectionMapping:
    """
    Use Groq LLM to map content blocks to template sections.
    For long documents, splits content into chunks to maintain accuracy.
    """
    settings = get_settings()
    
    logger.info(f"Starting AI mapping: {len(content.blocks)} content blocks -> {len(analysis.sections)} sections")
    
    if not settings.groq_api_key:
        logger.error("GROQ_API_KEY not configured!")
        raise AIMapperError("GROQ_API_KEY not configured")
    
    if not analysis.sections:
        logger.error("No sections found in template!")
        raise AIMapperError("No sections found in template")
    
    client = Groq(api_key=settings.groq_api_key)
    
    # Split content into chunks if needed
    chunks = _chunk_content_blocks(content.blocks, chunk_size)
    all_sections = []
    
    # Process each chunk
    for chunk_idx, chunk_blocks in enumerate(chunks):
        logger.info(f"Processing chunk {chunk_idx + 1}/{len(chunks)} ({len(chunk_blocks)} blocks)")
        
        # Create a temporary ExtractedContent for this chunk
        chunk_content = ExtractedContent(blocks=chunk_blocks, source_file=content.source_file)
        prompt = create_section_mapping_prompt(chunk_content, analysis)
        
        logger.debug(f"Chunk {chunk_idx + 1} prompt preview: {prompt[:300]}...")
        
        last_error: Exception | None = None
        chunk_sections = None
        
        for attempt in range(max_retries + 1):
            logger.info(f"  Chunk {chunk_idx + 1} attempt {attempt + 1}/{max_retries + 1}")
            try:
                response = client.chat.completions.create(
                    model=settings.groq_model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a document parser that preserves EXACT order. Return only valid JSON array of sections with 'title' and 'body' fields. CRITICAL: Content order in output MUST match source order exactly. Never reorganize or shuffle content."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.0,  # Zero temperature for maximum determinism - no creativity
                    max_tokens=32768,
                    timeout=settings.groq_timeout
                )
                
                response_text = response.choices[0].message.content.strip()
                logger.info(f"  Chunk {chunk_idx + 1} AI response received ({len(response_text)} chars)")
                logger.debug(f"  Chunk {chunk_idx + 1} AI response: {response_text[:500]}...")
                
                # Parse JSON response - expecting array
                sections_array = _parse_ai_response(response_text)
                
                if isinstance(sections_array, list):
                    chunk_sections = sections_array
                    logger.info(f"  Chunk {chunk_idx + 1} parsed {len(sections_array)} sections")
                    for i, sec in enumerate(sections_array):
                        title = sec.get("title", "")
                        body = sec.get("body", "")
                        logger.info(f"    Section {i+1}: '{title[:40]}' ({len(body)} items)")
                    break  # Success, exit retry loop
                else:
                    # Unexpected format
                    logger.warning(f"  Chunk {chunk_idx + 1} returned unexpected format")
                    chunk_sections = []
                    break
                    
            except ValidationError as e:
                logger.error(f"  Chunk {chunk_idx + 1} validation error: {e}")
                last_error = AIResponseValidationError(
                    f"AI response validation failed: {str(e)}",
                    details=str(e)
                )
            except json.JSONDecodeError as e:
                logger.error(f"  Chunk {chunk_idx + 1} JSON decode error: {e}")
                last_error = AIResponseValidationError(
                    f"AI response is not valid JSON: {str(e)}",
                    details=response_text if 'response_text' in locals() else None
                )
            except Exception as e:
                logger.error(f"  Chunk {chunk_idx + 1} API error: {e}")
                if "timeout" in str(e).lower():
                    last_error = GroqAPIError(f"Groq API timeout: {str(e)}")
                else:
                    last_error = GroqAPIError(f"Groq API error: {str(e)}")
        
        # If chunk processing failed after retries, use fallback
        if chunk_sections is None:
            logger.warning(f"  Chunk {chunk_idx + 1} failed, using fallback")
            # Create a simple fallback - treat all blocks as a single section
            chunk_sections = [{
                "title": f"Section {chunk_idx + 1}",
                "body": [{"type": "text", "content": block.content} for block in chunk_blocks]
            }]
        
        all_sections.append(chunk_sections)
    
    # Merge all chunk results
    merged_sections = _merge_section_mappings(all_sections)
    
    # Store as {"sections": [...]} for the renderer
    mapping_dict = {"sections": merged_sections}
    logger.info(f"Final result: {len(merged_sections)} sections total")
    
    return SectionMapping(mappings=mapping_dict)


def _parse_ai_response(response_text: str) -> Any:
    """Parse AI response, handling markdown code blocks."""
    text = response_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    
    return json.loads(text)


def _fallback_sequential_mapping(
    content: ExtractedContent,
    analysis: TemplateAnalysis
) -> SectionMapping:
    """
    Fallback: sequentially distribute content across sections.
    """
    mappings: dict[str, str] = {}
    
    if not content.blocks:
        for sec in analysis.sections:
            mappings[sec.section_id] = ""
        return SectionMapping(mappings=mappings)
    
    # Distribute blocks evenly across sections
    blocks_per_section = max(1, len(content.blocks) // len(analysis.sections))
    block_idx = 0
    
    for sec in analysis.sections:
        section_content = []
        for _ in range(blocks_per_section):
            if block_idx < len(content.blocks):
                section_content.append(content.blocks[block_idx].content)
                block_idx += 1
        
        mappings[sec.section_id] = "\n\n".join(section_content)
    
    # Add remaining blocks to last section
    if block_idx < len(content.blocks):
        remaining = [b.content for b in content.blocks[block_idx:]]
        last_section = analysis.sections[-1].section_id
        if mappings[last_section]:
            mappings[last_section] += "\n\n" + "\n\n".join(remaining)
        else:
            mappings[last_section] = "\n\n".join(remaining)
    
    return SectionMapping(mappings=mappings)


# Backwards compatibility alias
async def map_content_to_placeholders(
    content: ExtractedContent,
    analysis: TemplateAnalysis,
    max_retries: int = 2
) -> SectionMapping:
    """Alias for map_content_to_sections for backwards compatibility."""
    return await map_content_to_sections(content, analysis, max_retries)


ContentMapping = SectionMapping  # Type alias for backwards compatibility
