from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
import json
import logging
from src.api.progress import SyncProgressTracker, ProgressUpdate

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get('/api/v1/import/progress/{task_id}')
async def stream_progress(task_id: str):
    async def event_generator():
        def callback(update: ProgressUpdate):
            data = {
                'task_id': update.task_id,
                'stage': update.stage,
                'current': update.current,
                'total': update.total,
                'message': update.message,
                'detail': update.detail,
                'timestamp': update.timestamp
            }
            return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

        SyncProgressTracker.register_callback(task_id, callback)

        try:
            task_info = SyncProgressTracker.get_task_info(task_id)
            if task_info:
                yield f"data: {json.dumps({'task_id': task_id, 'stage': 'subscribed', 'message': 'Connected to progress stream', 'total': task_info.get('total', 100)}, ensure_ascii=False)}\n\n"

            while True:
                await asyncio.sleep(0.5)
                task_info = SyncProgressTracker.get_task_info(task_id)
                if task_info:
                    if task_info.get('stage') in ('completed', 'error'):
                        data = {
                            'task_id': task_id,
                            'stage': task_info['stage'],
                            'current': task_info.get('current', 0),
                            'total': task_info.get('total', 100),
                            'message': task_info.get('message', ''),
                        }
                        yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                        break
        except Exception as e:
            logger.error(f"Progress stream error: {e}")
        finally:
            SyncProgressTracker.unregister_callback(task_id)

    return StreamingResponse(
        event_generator(),
        media_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )


@router.get('/api/v1/import/status/{task_id}')
async def get_import_status(task_id: str):
    task_info = SyncProgressTracker.get_task_info(task_id)
    if not task_info:
        return {'code': 404, 'message': 'Task not found', 'data': None}

    return {
        'code': 0,
        'message': 'success',
        'data': {
            'task_id': task_id,
            'type': task_info.get('type', 'unknown'),
            'stage': task_info.get('stage', 'unknown'),
            'current': task_info.get('current', 0),
            'total': task_info.get('total', 100),
            'message': task_info.get('message', ''),
            'detail': task_info.get('detail')
        }
    }


import asyncio