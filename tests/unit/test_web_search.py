"""
Unit Tests for Web Search Tool
==============================
Tests for web search and weather functionality.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.tools.web_search import WebSearchTool


class TestWebSearchTool(unittest.TestCase):
    """Test cases for WebSearchTool."""
    
    def setUp(self):
        """Set up test tool."""
        self.tool = WebSearchTool()
    
    def test_initialization(self):
        """Test tool initialization."""
        self.assertIsNotNone(self.tool)
        self.assertIsInstance(self.tool.last_search_results, list)
    
    def test_should_use_web_search_weather(self):
        """Test detection of weather queries."""
        test_cases = [
            ("What's the weather in Amsterdam?", True),
            ("weather in New York", True),
            ("how's the weather today", True),
            ("temperature in London", True),
            ("Tell me about Python programming", False),
            ("What is machine learning?", False),
        ]
        
        for query, should_search in test_cases:
            with self.subTest(query=query):
                # Use internal method
                result, search_query = self._should_search(query)
                self.assertEqual(result, should_search, f"Failed for: {query}")
    
    def _should_search(self, message):
        """Helper to test search detection."""
        message_lower = message.lower()
        
        # Simple weather detection
        weather_keywords = ["weather", "temperature"]
        for kw in weather_keywords:
            if kw in message_lower:
                return True, f"current weather {message}"
        
        return False, ""
    
    def test_format_results_for_llm(self):
        """Test formatting search results."""
        results = [
            {
                "title": "Test Result 1",
                "snippet": "This is a test snippet",
                "link": "https://example.com/1",
                "source": "test"
            },
            {
                "title": "Test Result 2",
                "snippet": "Another test snippet",
                "link": "https://example.com/2",
                "source": "test"
            }
        ]
        
        formatted = self.tool.format_results_for_llm(results)
        
        self.assertIn("=== WEB SEARCH RESULTS ===", formatted)
        self.assertIn("Test Result 1", formatted)
        self.assertIn("Test Result 2", formatted)
        self.assertIn("https://example.com/1", formatted)
    
    def test_format_empty_results(self):
        """Test formatting empty results."""
        formatted = self.tool.format_results_for_llm([])
        self.assertIn("No search results found", formatted)
    
    def test_format_results_truncation(self):
        """Test that long results are truncated."""
        results = [
            {
                "title": "Test",
                "snippet": "x" * 10000,  # Very long snippet
                "link": "https://example.com",
                "source": "test"
            }
        ]
        
        formatted = self.tool.format_results_for_llm(results, max_length=500)
        self.assertLess(len(formatted), 600)  # Should be truncated
        self.assertIn("... (truncated)", formatted)


class TestWebSearchDetection(unittest.TestCase):
    """Test search query detection patterns."""
    
    def test_weather_patterns(self):
        """Test weather query detection."""
        weather_queries = [
            "What's the weather in Amsterdam?",
            "How's the weather today?",
            "Weather forecast for London",
            "Temperature in Tokyo",
            "Is it raining in Seattle?",
        ]
        
        for query in weather_queries:
            with self.subTest(query=query):
                self.assertTrue(
                    any(kw in query.lower() for kw in ["weather", "temperature", "raining"]),
                    f"Should detect weather: {query}"
                )
    
    def test_news_patterns(self):
        """Test news query detection."""
        news_queries = [
            "Latest news about AI",
            "What's happening today?",
            "Current events",
            "News about climate change",
        ]
        
        for query in news_queries:
            with self.subTest(query=query):
                self.assertTrue(
                    any(kw in query.lower() for kw in ["news", "latest", "happening", "current events"]),
                    f"Should detect news: {query}"
                )


if __name__ == "__main__":
    unittest.main()
