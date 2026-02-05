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
  Use sparingly and only when the text clearly signals a subsection.

- "bullet"  
  → List items.
  Convert content into bullets when:
    - lines start with -, *, numbers, letters
    - features, benefits, steps, or key points are listed
    - multiple short, related statements appear sequentially

---

### 3. Paragraph Splitting
- Break long paragraphs into multiple "text" blocks if they contain:
  - multiple ideas
  - topic transitions
- Do NOT fragment sentences unnecessarily.

---

## STRICT RULES
1. Preserve ALL original meaning and wording.
2. DO NOT summarize or shorten content.
3. DO NOT add new facts or interpretations.
4. DO NOT repeat content across sections.
5. Maintain original order of information.
6. Output MUST be valid JSON.
7. Output MUST match the required schema exactly.

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

Return ONLY the JSON array. No explanations. No markdown. No extra text.
"""
    return prompt



async def map_content_to_sections(
    content: ExtractedContent,
    analysis: TemplateAnalysis,
    max_retries: int = 2
) -> SectionMapping:
    """
    Use Groq LLM to map content blocks to template sections.
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
    prompt = create_section_mapping_prompt(content, analysis)
    
    logger.debug(f"Prompt preview: {prompt[:500]}...")
    
    last_error: Exception | None = None
    
    for attempt in range(max_retries + 1):
        logger.info(f"AI mapping attempt {attempt + 1}/{max_retries + 1}")
        try:
            response = client.chat.completions.create(
                model=settings.groq_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a document parser. Return only valid JSON array of sections with 'title' and 'body' fields."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=32768,
                timeout=settings.groq_timeout
            )
            
            response_text = response.choices[0].message.content.strip()
            logger.info(f"AI response received ({len(response_text)} chars)")
            logger.debug(f"AI response: {response_text[:500]}...")
            
            # Parse JSON response - expecting array
            sections_array = _parse_ai_response(response_text)
            
            # Store as {"sections": [...]} for the renderer
            if isinstance(sections_array, list):
                mapping_dict = {"sections": sections_array}
                logger.info(f"Parsed {len(sections_array)} sections from source")
                for i, sec in enumerate(sections_array):
                    title = sec.get("title", "")
                    body = sec.get("body", "")
                    logger.info(f"  Section {i+1}: '{title[:40]}' ({len(body)} chars)")
            else:
                # Fallback if AI returns dict instead of array
                mapping_dict = sections_array
                logger.warning("AI returned dict instead of array, using as-is")
            
            return SectionMapping(mappings=mapping_dict)
            
        except ValidationError as e:
            logger.error(f"Validation error: {e}")
            last_error = AIResponseValidationError(
                f"AI response validation failed: {str(e)}",
                details=str(e)
            )
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            last_error = AIResponseValidationError(
                f"AI response is not valid JSON: {str(e)}",
                details=response_text if 'response_text' in locals() else None
            )
        except Exception as e:
            logger.error(f"API error: {e}")
            if "timeout" in str(e).lower():
                last_error = GroqAPIError(f"Groq API timeout: {str(e)}")
            else:
                last_error = GroqAPIError(f"Groq API error: {str(e)}")
    
    # All retries failed - use fallback
    logger.warning("AI mapping failed, using fallback sequential mapping")
    try:
        return _fallback_sequential_mapping(content, analysis)
    except Exception:
        raise AIMapperError(
            f"AI mapping failed after {max_retries + 1} attempts",
            details=str(last_error) if last_error else None
        )


def _parse_ai_response(response_text: str) -> dict[str, str]:
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
