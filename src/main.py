from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import router
from src.api.middleware import logging_middleware
from src.api.admin_routes import router as admin_router
from src.api.graph_routes import router as graph_router
from src.api.query_routes import router as query_router
from src.api.config_routes import router as config_router
from src.api.import_routes import router as import_router
from src.api.progress_routes import router as progress_router
from src.api.cross_layer_routes import router as cross_layer_router
from src.logs import logger
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = FastAPI(title='动力电池拆卸知识图谱推理系统', version='1.24')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.middleware('http')(logging_middleware)

app.include_router(router)
app.include_router(admin_router, prefix='/admin')
app.include_router(graph_router, prefix='/api/v1')
app.include_router(query_router, prefix='/api/v1')
app.include_router(config_router, prefix='/api/v1')
app.include_router(import_router, prefix='/api/v1')
app.include_router(progress_router)
app.include_router(cross_layer_router)


@app.on_event('shutdown')
async def shutdown_event():
    logger.info('Shutting down application')


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
