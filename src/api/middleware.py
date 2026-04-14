from fastapi import Request
import logging
import time

logger = logging.getLogger(__name__)


async def logging_middleware(request: Request, call_next):
    start_time = time.time()
    
    logger.info(f'{request.method} {request.url.path}')
    
    response = await call_next(request)
    
    duration = int((time.time() - start_time) * 1000)
    logger.info(f'{request.method} {request.url.path} - {response.status_code} - {duration}ms')
    
    return response