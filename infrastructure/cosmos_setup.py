"""
One-time setup script to initialize the Azure Cosmos DB database and container
for the Smart Interviewer module.
"""

import sys
import os

# Add parent directory to path so we can import config
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.config import get_settings
from app.utils.logger import setup_logging, get_logger

setup_logging(debug=True)
logger = get_logger("infrastructure.cosmos_setup")

def setup_cosmos():
    settings = get_settings()

    endpoint = settings.COSMOS_ENDPOINT
    key = settings.COSMOS_KEY
    db_name = settings.COSMOS_DATABASE
    container_name = settings.COSMOS_CONTAINER

    if not endpoint or "your-" in endpoint:
        logger.error("COSMOS_ENDPOINT is not configured or is placeholder. Please configure it in your .env file.")
        sys.exit(1)

    if not key or "your-" in key:
        logger.error("COSMOS_KEY is not configured or is placeholder. Please configure it in your .env file.")
        sys.exit(1)

    logger.info(f"Connecting to Cosmos DB endpoint: {endpoint}")
    
    try:
        from azure.cosmos import CosmosClient, PartitionKey
        from azure.cosmos.exceptions import CosmosHttpResponseError
        
        client = CosmosClient(endpoint, credential=key)
        
        # Create database
        logger.info(f"Ensuring database '{db_name}' exists...")
        db_client = client.create_database_if_not_exists(id=db_name)
        logger.info(f"✓ Database '{db_name}' is ready.")

        # Create container partitioned by /candidate_id
        logger.info(f"Ensuring container '{container_name}' exists (partition key: /candidate_id)...")
        container_client = db_client.create_container_if_not_exists(
            id=container_name,
            partition_key=PartitionKey(path="/candidate_id"),
            offer_throughput=400 # Minimum throughput
        )
        logger.info(f"✓ Container '{container_name}' is ready.")
        logger.info("⚡ Azure Cosmos DB setup completed successfully!")

    except ImportError:
        logger.error("Failed to import azure-cosmos. Ensure backend virtual environment is activated and dependencies are installed.")
        sys.exit(1)
    except CosmosHttpResponseError as e:
        logger.error(f"Azure Cosmos DB API error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    setup_cosmos()
