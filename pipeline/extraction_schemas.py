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
