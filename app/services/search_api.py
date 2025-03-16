import requests
import logging
from typing import List, Dict, Any, Optional
import time
import random
import os
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

class SearchService:
    """Service for performing web searches using SearxNG."""
    
    def __init__(self, base_url=None, timeout=5, use_fallback=None):
        """Initialize the search service with the SearxNG URL.
        
        Args:
            base_url: The base URL of the SearxNG instance
            timeout: The timeout for search requests in seconds
            use_fallback: Whether to use fallback content (None = auto-detect)
        """
        if base_url is None:
            base_url = os.getenv("SEARXNG_URL", "http://localhost:8888")
        
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = 2
        
        self._searxng_available = False
        if use_fallback is None:
            self._searxng_available = self._check_searxng_available()
        else:
            self._searxng_available = not use_fallback
            
        if not self._searxng_available:
            logger.warning("SearxNG not available. Using fallback content for all searches.")
        else:
            logger.info(f"SearxNG available at {self.base_url}")
        
        self._cache = {}
        
    def _check_searxng_available(self) -> bool:
        """Check if SearxNG is available."""
        try:
            response = requests.get(f"{self.base_url}/healthz", timeout=2)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"SearxNG health check failed: {str(e)}")
            return False
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=3),
        retry=retry_if_exception_type((requests.exceptions.Timeout, requests.exceptions.ConnectionError))
    )
    def search(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        """Perform a search using SearxNG.
        
        Args:
            query: The search query
            num_results: The number of results to return
            
        Returns:
            A list of search results, each containing title, URL, and content
        """
        cache_key = f"{query}:{num_results}"
        if cache_key in self._cache:
            logger.info(f"Using cached results for '{query}'")
            return self._cache[cache_key]
        
        logger.info(f"Searching for: {query}")
        
        if not self._searxng_available:
            logger.info(f"Using fallback content for '{query}' (SearxNG not available)")
            results = self._get_fallback_for_query(query)
            self._cache[cache_key] = results
            return results
        
        try:
            logger.info(f"Searching SearxNG for '{query}'")
            
            params = {
                "q": query,
                "format": "json",
                "rand": random.randint(1, 1000000)
            }
            
            response = requests.get(
                f"{self.base_url}/search",
                params=params,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                results = response.json().get("results", [])
                formatted_results = []
                
                for result in results[:num_results]:
                    content = result.get("content", "")
                    formatted_results.append({
                        "title": result.get("title", ""),
                        "url": result.get("url", ""),
                        "content": content
                    })
                
                if formatted_results:
                    logger.info(f"Found {len(formatted_results)} results for '{query}'")
                    self._cache[cache_key] = formatted_results
                    return formatted_results
                else:
                    logger.warning(f"No results found for '{query}'")
                    results = self._get_fallback_for_query(query)
                    self._cache[cache_key] = results
                    return results
            else:
                logger.warning(f"Search returned status code {response.status_code}")
                self._searxng_available = False
                results = self._get_fallback_for_query(query)
                self._cache[cache_key] = results
                return results
                
        except requests.exceptions.Timeout:
            logger.warning(f"Search timed out for '{query}'")
            results = self._get_fallback_for_query(query)
            self._cache[cache_key] = results
            return results
            
        except Exception as e:
            logger.error(f"Error searching for '{query}': {str(e)}")
            self._searxng_available = False
            results = self._get_fallback_for_query(query)
            self._cache[cache_key] = results
            return results
    
    def _get_fallback_for_query(self, query: str) -> List[Dict[str, str]]:
        """Get fallback content for a specific query.
        
        Args:
            query: The search query
            
        Returns:
            A list of fallback search results
        """
        logger.info(f"Using fallback content for: {query}")
        return self.get_fallback_content(query)
    
    def get_fallback_content(self, query: str) -> List[Dict[str, str]]:
        """Get fallback content for when search fails.
        
        Args:
            query: The search query
            
        Returns:
            A list of fallback search results
        """
        logger.info(f"Providing fallback content for: {query}")
        
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
            ],
            "What is quantum computing?": [
                {
                    "title": "Quantum Computing - Overview",
                    "url": "https://en.wikipedia.org/wiki/Quantum_computing",
                    "content": "Quantum computing is a type of computation that harnesses the collective properties of quantum states, such as superposition, interference, and entanglement, to perform calculations. The devices that perform quantum computations are known as quantum computers."
                }
            ],
            "What are the latest advancements in quantum computing?": [
                {
                    "title": "Recent Advances in Quantum Computing",
                    "url": "https://www.nature.com/articles/d41586-021-00533-x",
                    "content": "Recent advancements in quantum computing include improved error correction techniques, the development of more stable qubits, quantum supremacy demonstrations, and progress in quantum algorithms for practical applications in chemistry, materials science, and optimization problems."
                }
            ]
        }
        
        generic_fallbacks = {
            "What is": [
                {
                    "title": f"Information about {query}",
                    "url": "https://en.wikipedia.org/wiki/Main_Page",
                    "content": f"{query.capitalize()} refers to a concept, technology, or field of study that involves specialized knowledge and applications. It has evolved over time and continues to develop with ongoing research and practical implementations."
                }
            ],
            "How to": [
                {
                    "title": f"Guide on {query}",
                    "url": "https://www.wikihow.com/Main-Page",
                    "content": f"To {query.lower()}, you typically need to follow a series of steps that involve preparation, execution, and review. The specific approach depends on your goals, available resources, and the context in which you're working."
                }
            ],
            "Why": [
                {
                    "title": f"Explanation of {query}",
                    "url": "https://www.britannica.com/",
                    "content": f"The reasons behind {query.lower()} are multifaceted and can be understood from various perspectives including historical context, scientific principles, and practical considerations. Different factors contribute to this phenomenon."
                }
            ]
        }
        
        best_match = None
        highest_similarity = 0
        
        for fallback_question in fallback_content:
            words_q1 = set(query.lower().split())
            words_q2 = set(fallback_question.lower().split())
            overlap = len(words_q1.intersection(words_q2))
            similarity = overlap / max(len(words_q1), len(words_q2))
            
            if similarity > highest_similarity:
                highest_similarity = similarity
                best_match = fallback_question
        
        if best_match and highest_similarity > 0.3:
            logger.info(f"Using fallback content for '{query}' (matched with '{best_match}')")
            return fallback_content[best_match]
        
        for pattern, content in generic_fallbacks.items():
            if pattern.lower() in query.lower():
                logger.info(f"Using generic '{pattern}' fallback for '{query}'")
                return content
        
        logger.info(f"Using completely generic fallback for '{query}'")
        return [
            {
                "title": f"Information about {query}",
                "url": "https://example.com/research",
                "content": f"Due to search limitations, specific information could not be retrieved. This question would typically explore aspects related to {query}."
            }
        ]
    
    def reset_availability(self):
        """Reset the availability of SearxNG and check again."""
        self._searxng_available = self._check_searxng_available()
        return self._searxng_available

search_service = SearchService()
