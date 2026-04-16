from pydantic_settings import BaseSettings
import os


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


settings = Settings(
    neo4j_password=os.getenv('NEO4J_PASSWORD', ''),
    openai_api_key=os.getenv('OPENAI_API_KEY', ''),
    openai_base_url=os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1'),
    llm_model=os.getenv('LLM_MODEL', 'gpt-4o')
)