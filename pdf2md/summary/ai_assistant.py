"""AI-assisted summary generation.

This module provides optional AI-enhanced summarization capabilities
for PDF to Markdown conversion.
"""

from typing import Dict, List, Optional

from pdf2md.utils.logger import get_logger

logger = get_logger()


class AIAssistant:
    """AI assistant for enhanced summary generation.

    This class provides an interface for AI-powered summarization.
    Actual implementation requires configuration with an AI service provider.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """Initialize the AI assistant.

        Args:
            api_key: API key for the AI service.
            model: Model name to use.

        Raises:
            ImportError: If AI dependencies are not available.
        """
        self.api_key = api_key
        self.model = model

        # Try to import OpenAI
        try:
            import openai

            self.openai = openai
            self.client = None

            if api_key:
                self.client = openai.OpenAI(api_key=api_key)

            logger.info("AI assistant initialized with OpenAI")

        except ImportError:
            logger.warning("OpenAI not installed. Install with: pip install openai")
            raise ImportError(
                "AI assistant requires OpenAI. Install with: pip install openai"
            )

    def generate_summary(
        self,
        title: str,
        content: str,
        rule_based_context: Optional[List] = None,
        max_length: int = 500,
    ) -> Dict:
        """Generate a summary using AI.

        Args:
            title: Document title.
            content: Document content.
            rule_based_context: Rule-based summary items for context.
            max_length: Maximum summary length in words.

        Returns:
            Dictionary with summary components:
            - headings: List of main headings
            - key_points: List of key points
            - table_of_contents: List of TOC entries
        """
        if not self.client:
            logger.warning("OpenAI client not configured, returning rule-based summary")
            return self._fallback_to_rule_based(rule_based_context)

        # Truncate content if too long
        truncated_content = self._truncate_content(content, max_words=2000)

        # Build prompt
        prompt = self._build_prompt(title, truncated_content, rule_based_context)

        try:
            response = self.client.chat.completions.create(
                model=self.model or "gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that summarizes PDF documents.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=1000,
            )

            summary_text = response.choices[0].message.content

            # Parse summary into structured format
            return self._parse_ai_summary(summary_text)

        except Exception as e:
            logger.error(f"Error generating AI summary: {e}")
            return self._fallback_to_rule_based(rule_based_context)

    def _build_prompt(
        self,
        title: str,
        content: str,
        rule_based_context: Optional[List],
    ) -> str:
        """Build the prompt for AI summarization.

        Args:
            title: Document title.
            content: Document content.
            rule_based_context: Rule-based summary context.

        Returns:
            Prompt string.
        """
        prompt = f"Please summarize the following PDF document:\n\n"
        prompt += f"Title: {title}\n\n"
        prompt += f"Content:\n{content}\n\n"

        if rule_based_context:
            prompt += "We have identified the following elements:\n"

            for item in rule_based_context:
                prompt += f"- {item.item_type}: {item.text} (page {item.page_number})\n"

        prompt += "\nPlease provide a summary with:\n"
        prompt += "1. Main headings\n"
        prompt += "2. Key points (bulleted list)\n"
        prompt += "3. Table of contents with page numbers\n"

        return prompt

    def _parse_ai_summary(self, summary_text: str) -> Dict:
        """Parse AI-generated summary into structured format.

        Args:
            summary_text: AI-generated summary text.

        Returns:
            Structured dictionary.
        """
        # Simple parsing - in production, this would use
        # structured output or more sophisticated parsing
        lines = summary_text.split("\n")

        headings = []
        key_points = []
        toc = []

        current_section = None

        for line in lines:
            line = line.strip()

            if not line:
                current_section = None
                continue

            # Detect sections
            if line.startswith("##"):
                current_section = "headings"
                headings.append(line.replace("#", "").strip())
            elif line.startswith("-") and current_section == "key_points":
                key_points.append(line[1:].strip())
            elif current_section == "table_of_contents":
                # Try to parse TOC entry
                toc.append(self._parse_toc_line(line))

        return {
            "headings": headings,
            "key_points": key_points,
            "table_of_contents": toc,
        }

    def _parse_toc_line(self, line: str) -> dict:
        """Parse a table of contents line.

        Args:
            line: TOC line string.

        Returns:
            Dictionary with title and page number.
        """
        # Simple parser - looks for "(page X)" pattern
        import re

        match = re.search(r"\(page\s*(\d+)\)", line)
        page_num = int(match.group(1)) if match else 0

        title = re.sub(r"\(page\s*\d+\)", "", line).strip()
        level = title.count("#")
        title = title.replace("#", "").strip()

        return {"level": level, "title": title, "page": page_num}

    def _truncate_content(self, content: str, max_words: int) -> str:
        """Truncate content to maximum word count.

        Args:
            content: Content to truncate.
            max_words: Maximum word count.

        Returns:
            Truncated content.
        """
        words = content.split()

        if len(words) <= max_words:
            return content

        return " ".join(words[:max_words]) + "..."

    def _fallback_to_rule_based(
        self, rule_based_context: Optional[List]
    ) -> Dict:
        """Fallback to rule-based extraction.

        Args:
            rule_based_context: Rule-based summary items.

        Returns:
            Summary dictionary.
        """
        if not rule_based_context:
            return {
                "headings": [],
                "key_points": [],
                "table_of_contents": [],
            }

        # Extract headings
        headings = [
            item.text for item in rule_based_context if item.item_type == "heading"
        ]

        return {
            "headings": headings,
            "key_points": [],
            "table_of_contents": [],
        }

    def is_available(self) -> bool:
        """Check if AI assistant is available.

        Returns:
            True if AI assistant is configured and available.
        """
        return self.client is not None

    def generate_key_points(
        self, content: str, num_points: int = 5
    ) -> List[str]:
        """Generate key points using AI.

        Args:
            content: Content to summarize.
            num_points: Number of key points to generate.

        Returns:
            List of key point strings.
        """
        if not self.client:
            logger.warning("AI client not configured")
            return []

        try:
            prompt = f"Please extract {num_points} key points from the following text:\n\n{content[:2000]}"

            response = self.client.chat.completions.create(
                model=self.model or "gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that extracts key information.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=500,
            )

            text = response.choices[0].message.content

            # Parse as bullet points
            key_points = []
            for line in text.split("\n"):
                line = line.strip()
                if line.startswith("-") or line.startswith("*"):
                    key_points.append(line[1:].strip())

            return key_points[:num_points]

        except Exception as e:
            logger.error(f"Error generating key points: {e}")
            return []


# Factory function
def create_ai_assistant(
    api_key: Optional[str] = None, model: Optional[str] = None
) -> Optional[AIAssistant]:
    """Create an AI assistant instance.

    Args:
        api_key: API key for the AI service.
        model: Model name to use.

    Returns:
        AIAssistant instance, or None if not configured.
    """
    try:
        return AIAssistant(api_key=api_key, model=model)
    except (ImportError, Exception) as e:
        logger.warning(f"Could not create AI assistant: {e}")
        return None