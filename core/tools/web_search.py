"""
Web Search Tool
===============
Search the web and retrieve real-time information.
Uses multiple search providers for redundancy.
"""

import os
import json
import re
from typing import List, Dict, Optional
from datetime import datetime
import urllib.request
import urllib.parse
import urllib.error


class WebSearchTool:
    """
    Web search tool for retrieving real-time information.
    
    Supports multiple backends:
    - DuckDuckGo (default, no API key)
    - Serper.dev (Google, requires API key)
    - Bing (requires API key)
    """
    
    def __init__(self):
        self.serper_api_key = os.getenv("SERPER_API_KEY")
        self.bing_api_key = os.getenv("BING_API_KEY")
        self.last_search_results = []
    
    def search(self, query: str, num_results: int = 5) -> List[Dict]:
        """
        Search the web for information.
        
        Args:
            query: Search query
            num_results: Number of results to return (default: 5)
            
        Returns:
            List of search results with title, snippet, link
        """
        # Try search providers in order of preference
        
        # 1. Try Serper.dev if available (Google quality)
        if self.serper_api_key:
            try:
                return self._search_serper(query, num_results)
            except Exception as e:
                print(f"Serper search failed: {e}")
        
        # 2. Try DuckDuckGo (free, no API key)
        try:
            return self._search_duckduckgo(query, num_results)
        except Exception as e:
            print(f"DuckDuckGo search failed: {e}")
        
        # 3. Fallback: return empty results
        return []
    
    def _search_serper(self, query: str, num_results: int) -> List[Dict]:
        """Search using Serper.dev (Google results)."""
        import httpx
        
        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": self.serper_api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "q": query,
            "num": num_results
        }
        
        with httpx.Client() as client:
            response = client.post(url, headers=headers, json=payload, timeout=30.0)
            response.raise_for_status()
            data = response.json()
        
        results = []
        
        # Parse organic results
        for item in data.get("organic", [])[:num_results]:
            results.append({
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "link": item.get("link", ""),
                "source": "google"
            })
        
        # Include answer box if present
        if "answerBox" in data:
            answer = data["answerBox"]
            results.insert(0, {
                "title": answer.get("title", "Answer"),
                "snippet": answer.get("answer", answer.get("snippet", "")),
                "link": answer.get("link", ""),
                "source": "google_answer"
            })
        
        self.last_search_results = results
        return results
    
    def _search_duckduckgo(self, query: str, num_results: int) -> List[Dict]:
        """Search using DuckDuckGo (no API key required)."""
        try:
            # Try duckduckgo-search library if available
            from duckduckgo_search import DDGS
            
            with DDGS() as ddgs:
                results = []
                for r in ddgs.text(query, max_results=num_results):
                    results.append({
                        "title": r.get("title", ""),
                        "snippet": r.get("body", ""),
                        "link": r.get("href", ""),
                        "source": "duckduckgo"
                    })
                self.last_search_results = results
                return results
                
        except ImportError:
            # Fallback to HTML scraping (simplified)
            return self._search_duckduckgo_scrape(query, num_results)
    
    def _search_duckduckgo_scrape(self, query: str, num_results: int) -> List[Dict]:
        """Fallback DuckDuckGo search via HTML (limited)."""
        # This is a simplified implementation
        # In production, use the duckduckgo-search library
        
        encoded_query = urllib.parse.quote(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0"
        }
        
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8')
            
            results = []
            # Basic regex parsing (fragile, but works as fallback)
            result_blocks = re.findall(
                r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
                html, re.DOTALL
            )
            
            for link, title, snippet in result_blocks[:num_results]:
                # Clean up HTML entities
                title = re.sub(r'<[^>]+>', '', title)
                snippet = re.sub(r'<[^>]+>', '', snippet)
                
                results.append({
                    "title": title,
                    "snippet": snippet,
                    "link": urllib.parse.unquote(link),
                    "source": "duckduckgo"
                })
            
            self.last_search_results = results
            return results
            
        except Exception as e:
            print(f"DuckDuckGo scrape failed: {e}")
            return []
    
    def get_current_weather(self, location: str) -> Dict:
        """
        Get current weather for a location.
        Uses OpenWeatherMap API (requires API key) or falls back to web search.
        """
        api_key = os.getenv("OPENWEATHER_API_KEY")
        
        if api_key:
            try:
                return self._get_weather_api(location, api_key)
            except Exception as e:
                print(f"Weather API failed: {e}")
        
        # Fallback: search for weather
        return self._get_weather_search(location)
    
    def _get_weather_api(self, location: str, api_key: str) -> Dict:
        """Get weather using OpenWeatherMap API."""
        import httpx
        
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": location,
            "appid": api_key,
            "units": "metric"
        }
        
        with httpx.Client() as client:
            response = client.get(url, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()
        
        return {
            "location": f"{data['name']}, {data['sys']['country']}",
            "temperature": f"{data['main']['temp']}°C",
            "feels_like": f"{data['main']['feels_like']}°C",
            "description": data['weather'][0]['description'],
            "humidity": f"{data['main']['humidity']}%",
            "wind": f"{data['wind']['speed']} m/s",
            "source": "openweather"
        }
    
    def _get_weather_search(self, location: str) -> Dict:
        """Get weather via web search (fallback)."""
        query = f"current weather {location}"
        results = self.search(query, num_results=3)
        
        if not results:
            return {
                "location": location,
                "error": "Could not retrieve weather information",
                "source": "none"
            }
        
        # Combine snippets for context
        combined = " ".join([r.get("snippet", "") for r in results[:2]])
        
        return {
            "location": location,
            "weather_info": combined,
            "sources": [r.get("link") for r in results[:2]],
            "source": "web_search",
            "note": "Using web search results (consider adding OPENWEATHER_API_KEY for accurate data)"
        }
    
    def format_results_for_llm(self, results: List[Dict], max_length: int = 2000) -> str:
        """
        Format search results for inclusion in LLM context.
        
        Args:
            results: Search results from search()
            max_length: Maximum length of formatted output
            
        Returns:
            Formatted string for LLM consumption
        """
        if not results:
            return "No search results found."
        
        lines = ["=== WEB SEARCH RESULTS ===", ""]
        
        for i, result in enumerate(results, 1):
            lines.append(f"[{i}] {result.get('title', 'No title')}")
            lines.append(f"    {result.get('snippet', 'No snippet')}")
            lines.append(f"    Source: {result.get('link', 'Unknown')}")
            lines.append("")
        
        lines.append("=== END SEARCH RESULTS ===")
        
        output = "\n".join(lines)
        
        # Truncate if too long
        if len(output) > max_length:
            output = output[:max_length] + "\n... (truncated)"
        
        return output


# Convenience functions
def search_web(query: str, num_results: int = 5) -> List[Dict]:
    """Quick web search."""
    tool = WebSearchTool()
    return tool.search(query, num_results)


def get_weather(location: str) -> Dict:
    """Quick weather lookup."""
    tool = WebSearchTool()
    return tool.get_current_weather(location)


# Test if run directly
if __name__ == "__main__":
    tool = WebSearchTool()
    
    print("Testing web search...")
    results = tool.search("Python programming language", num_results=3)
    print(f"Found {len(results)} results")
    print(tool.format_results_for_llm(results))
    
    print("\nTesting weather...")
    weather = tool.get_current_weather("Amsterdam")
    print(json.dumps(weather, indent=2))
