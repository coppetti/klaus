"""
Tools for Klaus Agent
=====================
Web search, data retrieval, and external API access.
"""

from .web_search import WebSearchTool, search_web, get_weather

__all__ = ['WebSearchTool', 'search_web', 'get_weather']
