import os
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.llms import HuggingFaceHub
import logging

logger = logging.getLogger(__name__)

class LLMProvider:
    """Provider for LLM services."""
    
    def __init__(self):
        """Initialize the LLM provider with the configured model."""
        self.hf_api_token = os.getenv("HUGGINGFACE_API_TOKEN", "")
        self.default_repo_id = os.getenv("HF_MODEL_REPO_ID", "mistralai/Mistral-7B-Instruct-v0.2")
        self.current_model = None
        
        self.set_model(self.default_repo_id)
        logger.info(f"Initialized LLM with default model: {self.default_repo_id}")
    
    def set_model(self, repo_id):
        """Set the model to use for inference.
        
        Args:
            repo_id: The Hugging Face model repository ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.llm = HuggingFaceHub(
                repo_id=repo_id,
                model_kwargs={"temperature": 0.7, "max_length": 16384},
                huggingfacehub_api_token=self.hf_api_token
            )
            self.current_model = repo_id
            logger.info(f"Set LLM model to: {repo_id}")
            return True
        except Exception as e:
            logger.error(f"Error setting model to {repo_id}: {str(e)}")
            if repo_id != self.default_repo_id:
                logger.info(f"Falling back to default model: {self.default_repo_id}")
                try:
                    self.llm = HuggingFaceHub(
                        repo_id=self.default_repo_id,
                        model_kwargs={"temperature": 0.7, "max_length": 16384},
                        huggingfacehub_api_token=self.hf_api_token
                    )
                    self.current_model = self.default_repo_id
                    return True
                except Exception as e2:
                    logger.error(f"Error setting default model: {str(e2)}")
            return False
    
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

llm_provider = LLMProvider() 