"""
Context Compactor
=================
Intelligently compresses conversation context when it grows too large.

Features:
- Importance scoring of messages
- Semantic clustering of related messages
- Automatic summarization of old context
- Hierarchical sub-context generation
"""

import re
import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from collections import defaultdict


@dataclass
class MessageImportance:
    """Importance score for a message."""
    message_id: int
    content: str
    importance_score: float  # 0.0 to 1.0
    factors: Dict[str, float]  # Breakdown of why it's important
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class SubContext:
    """A compressed representation of a conversation segment."""
    id: str
    title: str
    summary: str
    key_points: List[str]
    original_message_count: int
    compressed_token_estimate: int
    created_at: str
    message_range: Tuple[int, int]  # (start_idx, end_idx)
    
    def to_dict(self) -> Dict:
        return asdict(self)


class ContextAnalyzer:
    """Analyzes conversation context for importance and patterns."""
    
    # Keywords that indicate importance
    IMPORTANT_KEYWORDS = [
        # Decisions
        'decidi', 'decided', 'vamos usar', 'let\'s use', 'escolhi', 'chose',
        'adotar', 'adopt', 'implementar', 'implement', 'solução', 'solution',
        # Preferences
        'prefiro', 'prefer', 'gosto de', 'like', 'não gosto', 'don\'t like',
        'sempre uso', 'always use', 'nunca uso', 'never use',
        # Important info
        'importante', 'important', 'crucial', 'critical', 'key', 'chave',
        'principal', 'main', 'essential', 'essencial',
        # Actions/Tasks
        'preciso', 'need to', 'devemos', 'should', 'tarefa', 'task',
        'ação', 'action', 'próximo passo', 'next step',
        # Problems
        'problema', 'problem', 'erro', 'error', 'bug', 'issue',
        # Success
        'funcionou', 'worked', 'sucesso', 'success', 'resolvido', 'solved',
    ]
    
    # Code patterns indicate high importance for technical conversations
    CODE_PATTERNS = [
        r'```[\s\S]*?```',  # Code blocks
        r'`[^`]+`',  # Inline code
        r'(def|class|function|import|from)\s+',  # Python/JS keywords
        r'(SELECT|INSERT|UPDATE|DELETE|CREATE)\s+',  # SQL
    ]
    
    @classmethod
    def analyze_importance(cls, message: Dict, conversation_history: List[Dict]) -> MessageImportance:
        """
        Analyze how important a message is to keep in context.
        Returns importance score 0.0 to 1.0
        """
        content = message.get("text", "").lower()
        sender = message.get("sender", "user")
        # Ensure msg_id is an integer
        try:
            msg_id = int(message.get("id", 0))
        except (ValueError, TypeError):
            msg_id = 0
        
        factors = {}
        
        # Factor 1: Contains important keywords
        keyword_matches = sum(1 for kw in cls.IMPORTANT_KEYWORDS if kw.lower() in content)
        factors["keywords"] = min(keyword_matches * 0.1, 0.3)
        
        # Factor 2: Contains code (very important for dev conversations)
        code_score = 0
        for pattern in cls.CODE_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                code_score += 0.15
        factors["code"] = min(code_score, 0.3)
        
        # Factor 3: User questions (usually important for context)
        is_question = '?' in content or any(q in content for q in [
            'qual', 'what', 'como', 'how', 'por que', 'why', 'onde', 'where'
        ])
        factors["question"] = 0.15 if is_question else 0
        
        # Factor 4: Recency boost (more recent = more important)
        # This will be applied by the caller based on position
        factors["recency"] = 0.0  # Placeholder
        
        # Factor 5: Length (very short messages less important, very long might be important)
        word_count = len(content.split())
        if word_count < 3:
            factors["length"] = -0.1  # "ok", "yes" - not very informative
        elif word_count > 50:
            factors["length"] = 0.1  # Long messages often have substance
        else:
            factors["length"] = 0
        
        # Factor 6: Referenced by later messages
        references = cls._count_references(msg_id, content, conversation_history)
        factors["referenced"] = min(references * 0.05, 0.2)
        
        # Calculate total
        total_score = sum(factors.values())
        
        # Normalize to 0-1
        total_score = max(0.0, min(1.0, total_score))
        
        return MessageImportance(
            message_id=msg_id,
            content=message.get("text", "")[:100] + "..." if len(message.get("text", "")) > 100 else message.get("text", ""),
            importance_score=total_score,
            factors=factors
        )
    
    @classmethod
    def _count_references(cls, msg_id: int, content: str, history: List[Dict]) -> int:
        """Count how many later messages reference this message."""
        count = 0
        content_keywords = set(content.lower().split())
        
        for msg in history[msg_id+1:]:  # Only look at messages after
            msg_text = msg.get("text", "").lower()
            # Check for references ("isso", "that", "the code above", etc)
            reference_words = ['isso', 'isso aí', 'that', 'the above', 'o código', 'acima']
            if any(rw in msg_text for rw in reference_words):
                count += 1
        
        return count
    
    @classmethod
    def _generate_summary(cls, messages: List[Dict]) -> str:
        """Generate a brief summary of a list of messages."""
        if not messages:
            return "No messages to summarize."
        
        # Extract key content from messages
        user_msgs = [m.get("text", "") for m in messages if m.get("sender") == "user"]
        assistant_msgs = [m.get("text", "") for m in messages if m.get("sender") == "assistant"]
        
        # Create a concise summary
        summary_parts = []
        
        if user_msgs:
            # Get first user message (usually the query/topic)
            first_user = user_msgs[0][:80]
            if len(user_msgs[0]) > 80:
                first_user += "..."
            summary_parts.append(f"Q: {first_user}")
        
        if assistant_msgs:
            # Get first assistant response (usually the main answer)
            first_assistant = assistant_msgs[0][:100]
            if len(assistant_msgs[0]) > 100:
                first_assistant += "..."
            summary_parts.append(f"A: {first_assistant}")
        
        # Add count if there are more messages
        total = len(messages)
        if total > 2:
            summary_parts.append(f"({total} messages total)")
        
        return " | ".join(summary_parts) if summary_parts else "Compacted conversation segment."
    
    @classmethod
    def cluster_messages(cls, messages: List[Dict]) -> List[List[int]]:
        """
        Group related messages into clusters/topics.
        Simple implementation based on keyword overlap.
        """
        if len(messages) < 3:
            return [list(range(len(messages)))]
        
        clusters = []
        current_cluster = [0]
        
        for i in range(1, len(messages)):
            prev_msg = messages[i-1].get("text", "").lower()
            curr_msg = messages[i].get("text", "").lower()
            
            # Calculate word overlap
            prev_words = set(prev_msg.split())
            curr_words = set(curr_msg.split())
            
            overlap = len(prev_words & curr_words)
            total = len(prev_words | curr_words)
            
            similarity = overlap / total if total > 0 else 0
            
            # If similar to previous, add to same cluster
            if similarity > 0.3:  # Threshold
                current_cluster.append(i)
            else:
                clusters.append(current_cluster)
                current_cluster = [i]
        
        if current_cluster:
            clusters.append(current_cluster)
        
        return clusters


class ContextCompactor:
    """
    Compresses conversation context intelligently.
    """
    
    def __init__(self, max_tokens: int = 200000, compression_threshold: float = 0.8):
        self.max_tokens = max_tokens
        self.compression_threshold = compression_threshold
        self.sub_contexts: List[SubContext] = []
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count."""
        return len(text) // 3  # Conservative estimate
    
    def should_compact(self, messages: List[Dict]) -> bool:
        """Check if context should be compacted."""
        total_text = " ".join(m.get("text", "") for m in messages)
        estimated_tokens = self.estimate_tokens(total_text)
        return estimated_tokens > self.max_tokens * self.compression_threshold
    
    def compact_context(self, messages: List[Dict], preserve_recent: int = 5) -> Tuple[List[Dict], SubContext]:
        """
        Compact old messages into sub-context while preserving recent ones.
        
        Returns:
            (remaining_messages, generated_sub_context)
        """
        if len(messages) <= preserve_recent:
            return messages, None
        
        # Split into old (to compact) and recent (to preserve)
        old_messages = messages[:-preserve_recent]
        recent_messages = messages[-preserve_recent:]
        
        # Analyze importance of old messages
        importance_scores = []
        for i, msg in enumerate(old_messages):
            imp = ContextAnalyzer.analyze_importance(msg, old_messages)
            # Add recency factor (within old batch)
            recency_boost = (i / len(old_messages)) * 0.1
            imp.importance_score += recency_boost
            imp.factors["recency"] = recency_boost
            importance_scores.append(imp)
        
        # Cluster old messages by topic
        clusters = ContextAnalyzer.cluster_messages(old_messages)
        
        # Generate sub-context from clusters
        sub_context = self._generate_sub_context(old_messages, importance_scores, clusters)
        
        # Create new message list: sub-context summary + recent messages
        summary_message = {
            "sender": "system",
            "text": f"[Previous conversation summary: {sub_context.summary} Key points: {'; '.join(sub_context.key_points[:5])}]",
            "timestamp": datetime.now().isoformat(),
            "is_compacted": True
        }
        
        new_messages = [summary_message] + recent_messages
        
        return new_messages, sub_context
    
    def _generate_sub_context(self, 
                              messages: List[Dict], 
                              importance_scores: List[MessageImportance],
                              clusters: List[List[int]]) -> SubContext:
        """Generate a sub-context from old messages."""
        
        # Get top important messages from each cluster
        key_points = []
        cluster_themes = []
        
        for cluster in clusters:
            cluster_msgs = [(i, importance_scores[i]) for i in cluster if i < len(importance_scores)]
            cluster_msgs.sort(key=lambda x: x[1].importance_score, reverse=True)
            
            if cluster_msgs:
                # Get theme from most important message
                top_msg = messages[cluster_msgs[0][0]]
                theme = self._extract_theme(top_msg.get("text", ""))
                cluster_themes.append(theme)
                
                # Add key points from top 2 messages in cluster
                for idx, _ in cluster_msgs[:2]:
                    msg_text = messages[idx].get("text", "")
                    # Truncate long messages
                    point = msg_text[:150] + "..." if len(msg_text) > 150 else msg_text
                    key_points.append(point)
        
        # Generate title from themes
        if cluster_themes:
            title = f"Discussion about {', '.join(cluster_themes[:2])}"
        else:
            title = "Previous conversation"
        
        # Generate summary
        summary = f"Covered {len(messages)} messages about {len(clusters)} topics. "
        if key_points:
            summary += f"Main points include: {key_points[0][:100]}..."
        
        sub_ctx = SubContext(
            id=f"subctx_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            title=title,
            summary=summary,
            key_points=key_points[:10],  # Top 10 key points
            original_message_count=len(messages),
            compressed_token_estimate=self.estimate_tokens(summary + " ".join(key_points)),
            created_at=datetime.now().isoformat(),
            message_range=(0, len(messages))
        )
        
        self.sub_contexts.append(sub_ctx)
        return sub_ctx
    
    def _extract_theme(self, text: str) -> str:
        """Extract main theme/topic from text."""
        # Simple keyword extraction
        words = text.lower().split()
        
        # Filter out common words
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                      'o', 'a', 'os', 'as', 'é', 'são', 'foi', 'foram'}
        keywords = [w for w in words if len(w) > 3 and w not in stop_words]
        
        # Return most frequent or first meaningful
        if keywords:
            from collections import Counter
            most_common = Counter(keywords).most_common(1)
            return most_common[0][0] if most_common else keywords[0]
        return "general"
    
    def get_sub_contexts_summary(self) -> str:
        """Get summary of all sub-contexts."""
        if not self.sub_contexts:
            return "No compacted contexts"
        
        lines = [f"Sub-contexts ({len(self.sub_contexts)}):"]
        for ctx in self.sub_contexts:
            lines.append(f"  • {ctx.title}: {ctx.original_message_count} msgs → {ctx.compressed_token_estimate} tokens")
        return "\n".join(lines)


# Helper for Web UI integration
class SessionContextCompactor:
    """Per-session context compaction."""
    
    def __init__(self, session_id: str, max_tokens: int = 200000):
        self.session_id = session_id
        self.max_tokens = max_tokens
        self.compactor = ContextCompactor(max_tokens)
        self.compaction_history: List[Dict] = []
    
    def check_and_compact(self, messages: List[Dict]) -> List[Dict]:
        """Check if compaction is needed and perform it."""
        if not self.compactor.should_compact(messages):
            return messages
        
        # Compact the context
        new_messages, sub_ctx = self.compactor.compact_context(messages)
        
        if sub_ctx:
            # Record compaction event
            self.compaction_history.append({
                "timestamp": datetime.now().isoformat(),
                "original_count": sub_ctx.original_message_count,
                "sub_context_id": sub_ctx.id,
                "summary": sub_ctx.summary
            })
        
        return new_messages
    
    def force_compact(self, messages: List[Dict], preserve_recent: int = 5) -> Tuple[List[Dict], SubContext]:
        """Force compaction regardless of size."""
        return self.compactor.compact_context(messages, preserve_recent)
    
    def get_stats(self) -> Dict:
        """Get compaction statistics."""
        return {
            "compactions_performed": len(self.compaction_history),
            "sub_contexts_created": len(self.compactor.sub_contexts),
            "total_original_messages": sum(h["original_count"] for h in self.compaction_history),
            "history": self.compaction_history
        }
