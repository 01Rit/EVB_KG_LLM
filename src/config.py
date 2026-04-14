from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    neo4j_uri: str = 'bolt://localhost:7687'
    neo4j_user: str = 'neo4j'
    neo4j_password: str
    milvus_host: str = 'localhost'
    milvus_port: int = 19530
    openai_api_key: str
    openai_base_url: str = 'https://api.openai.com/v1'
    log_level: str = 'INFO'
    
    model: str = 'gpt-4o'
    temperature: float = 0.1
    max_tokens: int = 2000
    
    top_k: int = 30
    retrieval_depth: int = 2
    similarity_threshold: float = 0.72
    max_iterations: int = 3
    
    class Config:
        env_file = '.env'
        extra = 'ignore'


settings = Settings()