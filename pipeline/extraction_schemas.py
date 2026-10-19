"""JSON Schema definitions for structured extraction via LLM tool calls.

These schemas replace raw text/JSON parsing with type-safe function call schemas,
ensuring 100% valid structured output from the extraction pipeline.
"""

from service.agents.base import ToolDefinition


ARTICLE_EXTRACTION_TOOL = ToolDefinition(
    name="submit_extracted_article",
    description="Submit the extracted and structured news article metadata. Call this exactly once with all extracted fields.",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "The article headline."},
            "publication_date": {"type": "string", "description": "Publication date in ISO 8601 format."},
            "summary": {"type": "string", "description": "A concise summary of the article, maximum 100 words."},
            "content": {
                "type": "string",
                "description": "The full article body text. Preserve paragraph breaks. Write in third-person voice for community sources.",
            },
            "category": {
                "type": "string",
                "enum": ["World", "Business", "Technology", "Entertainment", "Sports", "Science", "Health"],
                "description": "The primary news category.",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Relevant keyword tags (e.g., politics, economy, AI).",
            },
            "location": {
                "type": "string",
                "description": "Geographic location mentioned or inferred from the article. Use 'unknown' if not inferable.",
            },
        },
        "required": ["title", "publication_date", "summary", "content", "category", "tags", "location"],
    },
)

NEWS_CLASSIFICATION_TOOL = ToolDefinition(
    name="submit_classification",
    description="Submit whether this content is a newsworthy article or not.",
    parameters={
        "type": "object",
        "properties": {
            "is_news": {"type": "boolean", "description": "True if the content is newsworthy, false otherwise."},
            "reason": {"type": "string", "description": "Brief explanation of the classification decision."},
        },
        "required": ["is_news"],
    },
)

MARKDOWN_FORMAT_TOOL = ToolDefinition(
    name="submit_formatted_content",
    description="Submit the markdown-formatted version of the article content.",
    parameters={
        "type": "object",
        "properties": {
            "markdown": {"type": "string", "description": "The article content formatted with markdown headings, bullet points, and block quotes."},
        },
        "required": ["markdown"],
    },
)

NEWS_BIAS_DETECTION_TOOL = ToolDefinition(
    name="submit_news_bias_analysis",
    description="Submit structured media bias analysis for a news article, evaluating overall biasness score, bias types, and favored/disfavored entities.",
    parameters={
        "type": "object",
        "properties": {
            "bias_score": {
                "type": "number",
                "description": "Overall biasness score from 0.0 (completely neutral, balanced, factual) to 1.0 (heavily biased, one-sided, or propagandistic).",
            },
            "bias_types": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [
                        "political",
                        "linguistic",
                        "cognitive",
                        "commercial",
                        "geopolitical",
                        "selection_omission",
                        "demographic",
                    ],
                },
                "description": "Types of bias identified in the article.",
            },
            "who_it_favors": {
                "type": "string",
                "description": "Who or what the article's narrative favors (e.g. a political party, government, corporation, social group, or 'none / neutral').",
            },
            "who_it_opposes": {
                "type": "string",
                "description": "Who or what the article's narrative disfavors, criticizes, or marginalizes (or 'none / neutral').",
            },
            "loaded_language": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Specific words, adjectives, or loaded verbs exhibiting subjective bias or spin.",
            },
            "reasoning": {
                "type": "string",
                "description": "Detailed explanation justifying the bias score, identified bias types, and framing choices.",
            },
        },
        "required": ["bias_score", "bias_types", "who_it_favors", "reasoning"],
    },
)

