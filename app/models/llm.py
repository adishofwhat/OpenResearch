import os
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.llms import HuggingFaceHub
import logging

# Configure logging
logger = logging.getLogger(__name__)

class LLMProvider:
    """Provider for LLM services."""
    
    def __init__(self):
        """Initialize the LLM provider with the configured model."""
        self.hf_api_token = os.getenv("HUGGINGFACE_API_TOKEN", "")
        self.repo_id = os.getenv("HF_MODEL_REPO_ID", "mistralai/Mistral-7B-Instruct-v0.2")
        
        # Initialize the LLM
        self.llm = HuggingFaceHub(
            repo_id=self.repo_id,
            model_kwargs={"temperature": 0.7, "max_length": 1024},
            huggingfacehub_api_token=self.hf_api_token
        )
        logger.info(f"Initialized LLM with model: {self.repo_id}")
    
    def create_chain(self, prompt_template, output_parser=None):
        """Create an LLM chain with the given prompt template and output parser.
        
        Args:
            prompt_template: The prompt template to use
            output_parser: The output parser to use (defaults to StrOutputParser)
            
        Returns:
            A runnable chain that can be invoked with input variables
        """
        if output_parser is None:
            output_parser = StrOutputParser()
            
        prompt = PromptTemplate.from_template(prompt_template)
        chain = prompt | self.llm | output_parser
        
        return chain

# Create a singleton instance
llm_provider = LLMProvider() 