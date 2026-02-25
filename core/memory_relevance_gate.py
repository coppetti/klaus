"""
Memory Relevance Gate
=====================
Filters low-utility interactions (greetings, simple confirmations, noise)
from being stored in the Knowledge Graph.
"""

import re
from typing import Tuple

class MemoryRelevanceGate:
    """
    Decides if a piece of text is "relevant" enough to be added to long-term memory.
    """
    
    # Junk patterns (Portuguese & English)
    JUNK_PHRASES = [
        r'^\s*(ok|valeu|thanks|obrigado|de nada|tmj|vlw|boa|show|hey|heyy|hey man|hey man!|ola|olá)\W*$',
        r'^\s*(oi|olá|hello|hi|bom dia|boa tarde|boa noite)\W*$',
        r'^\s*(entendi|compreendo|i understand|got it|makes sense)\W*$',
        r'^\s*(perfeito|perfect|maravilha|ótimo|great)\W*$',
        r'^\s*(teste|testing|testando|hello world)\W*$',
    ]
    
    @classmethod
    def is_relevant(cls, text: str) -> Tuple[bool, float, str]:
        """
        Check if text is relevant for memory storage.
        
        Returns:
            (is_relevant, score, reason)
        """
        if not text:
            return False, 0.0, "empty_text"
            
        text_clean = text.lower().strip()
        
        # 1. Length check
        if len(text_clean) < 10:
            # Check if it's a known junk phrase
            for pattern in cls.JUNK_PHRASES:
                if re.match(pattern, text_clean):
                    return False, 0.1, "low_utility_phrase"
            
            # Too short and not a known term
            if len(text_clean.split()) < 3:
                return False, 0.2, "too_short"

        # 2. Check for technical content (heuristics)
        tech_indicators = [
            '```', '{', '[', '(', '=', 'def ', 'class ', 'import ', '/', '.py', '.js'
        ]
        has_code = any(ind in text for ind in tech_indicators)
        
        # 3. Keyword density (Portuguese & English)
        keywords = [
            'erro', 'fail', 'bug', 'fix', 'setup', 'config', 'deploy', 'arquitetura', 'design',
            'python', 'javascript', 'backend', 'frontend', 'database', 'api', 'docker', 'graph',
            'machine learning', 'ai', 'ia', 'projeto', 'código', 'desenvolvimento', 'engine'
        ]
        keyword_match = any(word in text_clean for word in keywords)
        
        # Calculate heuristic score
        score = 0.5 # Base
        if has_code: score += 0.4
        if keyword_match: score += 0.3
        if len(text_clean) > 50: score += 0.2
        if len(text_clean) > 150: score += 0.1
        
        # Penalyze common junk
        for pattern in cls.JUNK_PHRASES:
            if re.search(pattern, text_clean):
                score -= 0.6
                
        # Boost if it looks like a fact about the user or project
        if any(w in text_clean for w in ['trabalha', 'projeto', 'prefere', 'gosta', 'estou']):
            score += 0.2
                
        score = min(max(score, 0.0), 1.0)
        
        threshold = 0.35 # Slightly lower threshold
        if score >= threshold:
            return True, score, "content_useful"
        else:
            return False, score, "below_relevance_threshold"

def should_store_memory(content: str) -> bool:
    """Convenience wrapper for the relevance gate."""
    relevant, _, _ = MemoryRelevanceGate.is_relevant(content)
    return relevant
