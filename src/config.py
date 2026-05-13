from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

load_dotenv()


class Settings(BaseSettings):
    neo4j_uri: str = 'bolt://localhost:7687'
    neo4j_user: str = 'neo4j'
    neo4j_password: str = ''
    milvus_host: str = 'localhost'
    milvus_port: int = 19530
    openai_api_key: str = ''
    openai_base_url: str = 'https://api.openai.com/v1'
    llm_model: str = 'gpt-4o'
    log_level: str = 'INFO'

    temperature: float = 0.1
    max_tokens: int = 2000

    top_k: int = 30
    retrieval_depth: int = 2
    similarity_threshold: float = 0.72
    max_iterations: int = 3

    class Config:
        env_file = '.env'
        extra = 'ignore'


def load_settings():
    """Load settings from environment variables with .env file support"""
    return Settings(
        neo4j_uri=os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
        neo4j_user=os.getenv('NEO4J_USER', 'neo4j'),
        neo4j_password=os.getenv('NEO4J_PASSWORD', ''),
        milvus_host=os.getenv('MILVUS_HOST', 'localhost'),
        milvus_port=int(os.getenv('MILVUS_PORT', '19530')),
        openai_api_key=os.getenv('OPENAI_API_KEY', ''),
        openai_base_url=os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1'),
        llm_model=os.getenv('LLM_MODEL', 'gpt-4o'),
        max_tokens=int(os.getenv('MAX_TOKENS', '2000')),
        log_level=os.getenv('LOG_LEVEL', 'INFO'),
    )


settings = load_settings()