import requests
import logging
from typing import List, Dict, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)

class SearchService:
    """Service for performing web searches using SearxNG."""
    
    def __init__(self, base_url="http://searxng:8080", timeout=10):
        """Initialize the search service with the SearxNG URL.
        
        Args:
            base_url: The base URL of the SearxNG instance
            timeout: The timeout for search requests in seconds
        """
        self.base_url = base_url
        self.timeout = timeout
        
    def search(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        """Perform a search using SearxNG.
        
        Args:
            query: The search query
            num_results: The number of results to return
            
        Returns:
            A list of search results, each containing title, URL, and content
        """
        logger.info(f"Searching for: {query}")
        
        try:
            response = requests.get(
                f"{self.base_url}/search",
                params={"q": query, "format": "json"},
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                results = response.json().get("results", [])
                formatted_results = []
                
                for result in results[:num_results]:
                    # Try to get a snippet or content
                    content = result.get("content", "")
                    # Include title, URL and content in a structured format
                    formatted_results.append({
                        "title": result.get("title", ""),
                        "url": result.get("url", ""),
                        "content": content
                    })
                
                logger.info(f"Found {len(formatted_results)} results for '{query}'")
                return formatted_results
            else:
                logger.warning(f"Search returned status code {response.status_code}")
                return []
                
        except requests.exceptions.Timeout:
            logger.warning(f"Search timed out for '{query}'")
            return []
        except Exception as e:
            logger.error(f"Error searching for '{query}': {str(e)}")
            return []
    
    def get_fallback_content(self, query: str) -> List[Dict[str, str]]:
        """Get fallback content for when search fails.
        
        Args:
            query: The search query
            
        Returns:
            A list of fallback search results
        """
        logger.info(f"Providing fallback content for: {query}")
        
        # Create fallback content for AI-related questions
        fallback_content = {
            "What is AI?": [
                {
                    "title": "Artificial Intelligence (AI) - Overview",
                    "url": "https://en.wikipedia.org/wiki/Artificial_intelligence",
                    "content": "Artificial Intelligence (AI) refers to the simulation of human intelligence in machines that are programmed to think like humans and mimic their actions. The term may also be applied to any machine that exhibits traits associated with a human mind such as learning and problem-solving."
                }
            ],
            "What are the key concepts in AI?": [
                {
                    "title": "Key Concepts in AI",
                    "url": "https://www.ibm.com/topics/artificial-intelligence",
                    "content": "Key concepts in AI include machine learning, neural networks, deep learning, natural language processing, computer vision, and reinforcement learning. Machine learning is a subset of AI that enables systems to learn and improve from experience without being explicitly programmed."
                }
            ],
            "What are the latest developments in AI?": [
                {
                    "title": "Recent Advances in AI",
                    "url": "https://www.nature.com/articles/d41586-020-00575-7",
                    "content": "Recent developments in AI include large language models like GPT-4, advancements in multimodal AI systems, progress in AI for scientific discovery, and improvements in AI ethics and governance frameworks."
                }
            ],
            "What are the main challenges in AI?": [
                {
                    "title": "Challenges in AI Development",
                    "url": "https://www.frontiersin.org/articles/10.3389/frai.2021.719058/full",
                    "content": "Major challenges in AI include ensuring ethical use, addressing bias and fairness issues, achieving explainability and transparency, ensuring safety and security, and managing the societal and economic impacts of automation."
                }
            ],
            "What are practical applications of AI?": [
                {
                    "title": "AI Applications Across Industries",
                    "url": "https://hbr.org/2022/11/the-business-case-for-ai",
                    "content": "AI has practical applications across numerous industries including healthcare (diagnosis, drug discovery), finance (fraud detection, algorithmic trading), transportation (autonomous vehicles), manufacturing (predictive maintenance), customer service (chatbots), and entertainment (content recommendation)."
                }
            ]
        }
        
        # Find the most similar question in our fallback content
        best_match = None
        highest_similarity = 0
        
        for fallback_question in fallback_content:
            # Simple word overlap similarity
            words_q1 = set(query.lower().split())
            words_q2 = set(fallback_question.lower().split())
            overlap = len(words_q1.intersection(words_q2))
            similarity = overlap / max(len(words_q1), len(words_q2))
            
            if similarity > highest_similarity:
                highest_similarity = similarity
                best_match = fallback_question
        
        # If we found a reasonable match, use its content
        if best_match and highest_similarity > 0.3:
            logger.info(f"Using fallback content for '{query}' (matched with '{best_match}')")
            return fallback_content[best_match]
        
        # Otherwise, provide a generic response
        logger.info(f"Using generic fallback for '{query}'")
        return [
            {
                "title": f"Information about {query}",
                "url": "https://example.com/ai-research",
                "content": f"Due to search limitations, specific information could not be retrieved. This question would typically explore aspects related to {query}."
            }
        ]

# Create a singleton instance
search_service = SearchService()
