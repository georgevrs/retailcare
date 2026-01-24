import json
import os
import logging
from typing import List
from src.models import FAQResult

logger = logging.getLogger(__name__)

class FAQKnowledgeBase:
    def __init__(self, file_path: str = "data/faq_el.json"):
        self.file_path = file_path
        self.kb = self._load_kb()

    def _load_kb(self) -> List[dict]:
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                logger.warning(f"FAQ file not found at {self.file_path}")
                return []
        except Exception as e:
            logger.error(f"Error loading FAQ KB: {e}")
            return []

    def search(self, query: str, limit: int = 2) -> List[FAQResult]:
        # Simple keyword matching for demo purposes
        # In production, use embeddings (e.g. Azure OpenAI embeddings + AI Search)
        results = []
        query_words = set(query.lower().split())
        
        for entry in self.kb:
            q_text = entry["question"].lower()
            match_count = sum(1 for word in query_words if word in q_text)
            
            if match_count > 0:
                results.append(FAQResult(
                    question=entry["question"],
                    answer=entry["answer"],
                    score=match_count / len(query_words)
                ))
        
        # Sort by score descending
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]

# Singleton
faq_kb = FAQKnowledgeBase()
