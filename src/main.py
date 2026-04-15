from fastapi import FastAPI
from src.api.routes import router
from src.api.middleware import logging_middleware
from src.api.admin_routes import router as admin_router
from src.api.graph_routes import router as graph_router
from src.logs import logger

logger = logging.getLogger(__name__)

app = FastAPI(title='动力电池拆卸知识图谱推理系统', version='1.0.0')

app.middleware('http')(logging_middleware)

app.include_router(router)
app.include_router(admin_router, prefix='/admin')
app.include_router(graph_router, prefix='/api/v1')


@app.on_event('shutdown')
async def shutdown_event():
    logger.info('Shutting down application')


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)