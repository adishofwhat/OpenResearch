import weaviate
from weaviate.connect import ConnectionParams
import logging
from app.models.schemas import ResearchObject

# Configure logging
logger = logging.getLogger(__name__)

class WeaviateService:
    """Service for interacting with Weaviate vector database."""
    
    def __init__(self, host="openresearch-weaviate", http_port=8080, grpc_port=50051):
        """Initialize the Weaviate service with connection parameters.
        
        Args:
            host: The hostname of the Weaviate instance
            http_port: The HTTP port of the Weaviate instance
            grpc_port: The gRPC port of the Weaviate instance
        """
        self.client = weaviate.WeaviateClient(
            connection_params=ConnectionParams.from_params(
                http_host=host, 
                http_port=http_port, 
                http_secure=False,
                grpc_host=host,
                grpc_port=grpc_port,
                grpc_secure=False,
            )
        )
        self.is_connected = False
        
    def connect(self):
        """Connect to the Weaviate instance and initialize collections if needed."""
        try:
            self.client.connect()
            self.is_connected = self.client.is_ready()
            logger.info(f"Weaviate connection status: {self.is_connected}")
            
            if self.is_connected:
                # Create Research collection if it doesn't exist
                collections = self.client.collections.list_all()
                if "Research" not in collections:
                    # Using the new API for Weaviate client v4+
                    research_collection = self.client.collections.create(
                        name="Research",
                        properties=[
                            {"name": "name", "dataType": ["text"]},
                            {"name": "description", "dataType": ["text"]},
                            {"name": "tags", "dataType": ["text[]"]}
                        ]
                    )
                    logger.info("Created Research collection in Weaviate")
            
            return self.is_connected
        except Exception as e:
            logger.error(f"Error connecting to Weaviate: {e}")
            self.is_connected = False
            return False
    
    def add_research_object(self, research_object: ResearchObject):
        """Add a research object to the Weaviate database.
        
        Args:
            research_object: The research object to add
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected:
            logger.warning("Not connected to Weaviate, cannot add research object")
            return False
            
        try:
            data_object = {
                "name": research_object.name,
                "description": research_object.description,
                "tags": research_object.tags
            }
            
            self.client.collections.get("Research").data.insert(data_object)
            logger.info(f"Added research object: {research_object.name}")
            return True
        except Exception as e:
            logger.error(f"Error adding research object: {e}")
            return False
    
    def get_research_objects(self):
        """Get all research objects from the Weaviate database.
        
        Returns:
            A list of research objects, or an empty list if there was an error
        """
        if not self.is_connected:
            logger.warning("Not connected to Weaviate, cannot get research objects")
            return []
            
        try:
            response = self.client.collections.get("Research").query.fetch_objects()
            logger.info(f"Retrieved {len(response.objects)} research objects")
            return response.objects
        except Exception as e:
            logger.error(f"Error fetching research objects: {e}")
            return []

# Create a singleton instance
weaviate_service = WeaviateService()
