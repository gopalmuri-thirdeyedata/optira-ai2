"""
AI Mapper using Groq LLM for semantic section mapping.
Maps source content blocks to template sections based on meaning.
"""
import json
import logging
from typing import Any

from groq import Groq
from pydantic import BaseModel, ValidationError

from app.core.config import get_settings
from app.core.exceptions import AIMapperError, AIResponseValidationError, GroqAPIError
from app.services.parser import ExtractedContent, content_to_text_summary
from app.services.analyzer import TemplateAnalysis, get_section_descriptions

logger = logging.getLogger(__name__)


class SectionMapping(BaseModel):
    """Validated mapping of section IDs to content."""
    mappings: dict[str, str]


def create_section_mapping_prompt(
    content: ExtractedContent, 
    analysis: TemplateAnalysis
) -> str:
    """
    Create the prompt for AI section mapping.
    """
    content_text = content_to_text_summary(content)
    section_desc = get_section_descriptions(analysis)
    
    prompt = f"""You are a document content mapper. Your task is to assign source content to template sections based on semantic meaning.

## STRICT RULES:
1. DO NOT generate new text - only use text from the source
2. DO NOT add anything not present in the source content
3. Match content to sections by meaning (e.g., source "Abstract" -> template "Executive Summary")
4. Combine multiple source paragraphs if they belong to the same section
5. If no matching content exists for a section, use empty string ""
6. Respond with ONLY valid JSON, no explanations

## Source Content:
{content_text}

## Template Sections:
{section_desc}

## Required Output Format (JSON only):
Return a JSON object where keys are section IDs and values are the mapped content:
{{
{chr(10).join(f'  "{sec.section_id}": "content for {sec.heading_text}",' for sec in analysis.sections[:-1])}
  "{analysis.sections[-1].section_id}": "content for {analysis.sections[-1].heading_text}"
}}

Map each section with the most semantically appropriate content from the source. Return ONLY the JSON object."""

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
                        "content": "You are a precise document content mapper. Return only valid JSON mapping section IDs to content."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=8192,
                timeout=settings.groq_timeout
            )
            
            response_text = response.choices[0].message.content.strip()
            logger.info(f"AI response received ({len(response_text)} chars)")
            logger.debug(f"AI response: {response_text[:500]}...")
            
            # Parse JSON response
            mapping_dict = _parse_ai_response(response_text)
            
            logger.info(f"Parsed mappings for sections: {list(mapping_dict.keys())}")
            for sec_id, content_val in mapping_dict.items():
                logger.info(f"  {sec_id}: {len(content_val)} chars - '{content_val[:50]}...'")
            
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
