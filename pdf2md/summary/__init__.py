"""Summary extraction modules for pdf2md."""

from pdf2md.summary.ai_assistant import AIAssistant, create_ai_assistant
from pdf2md.summary.extractor import Summary, SummaryExtractor
from pdf2md.summary.rule_based import RuleBasedExtractor, SummaryItem

__all__ = [
    # Main extraction
    "SummaryExtractor",
    "Summary",
    # Rule-based extraction
    "RuleBasedExtractor",
    "SummaryItem",
    # AI assistance
    "AIAssistant",
    "create_ai_assistant",
]