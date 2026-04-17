import asyncio
import uuid
import time
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ImportStage(str, Enum):
    IDLE = "idle"
    PARSING = "parsing"
    EXTRACTING = "extracting"
    CREATING_NODES = "creating_nodes"
    CREATING_RELATIONS = "creating_relations"
    SCORING = "scoring"
    COMPLETING = "completing"


@dataclass
class ProgressUpdate:
    task_id: str
    stage: str
    current: int
    total: int
    message: str
    detail: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


class ProgressTracker:
    _instance: Optional['ProgressTracker'] = None
    _lock = asyncio.Lock()

    def __init__(self):
        self._tasks: Dict[str, asyncio.Queue] = {}
        self._task_info: Dict[str, Dict[str, Any]] = {}

    @classmethod
    async def get_instance(cls) -> 'ProgressTracker':
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = ProgressTracker()
        return cls._instance

    async def create_task(self, task_type: str, total: int = 100) -> str:
        task_id = str(uuid.uuid4())
        queue = asyncio.Queue()
        self._tasks[task_id] = queue
        self._task_info[task_id] = {
            'type': task_type,
            'total': total,
            'current': 0,
            'stage': ImportStage.IDLE.value,
            'message': 'Starting...',
            'detail': None,
            'created_at': time.time()
        }
        return task_id

    async def update(self, task_id: str, stage: str, current: int, total: int,
                     message: str, detail: Optional[str] = None) -> None:
        if task_id not in self._tasks:
            logger.warning(f"Task {task_id} not found")
            return

        self._task_info[task_id].update({
            'stage': stage,
            'current': current,
            'total': total,
            'message': message,
            'detail': detail
        })

        update = ProgressUpdate(
            task_id=task_id,
            stage=stage,
            current=current,
            total=total,
            message=message,
            detail=detail
        )
        await self._tasks[task_id].put(update)

    async def complete(self, task_id: str, message: str = "Completed") -> None:
        if task_id not in self._tasks:
            return

        self._task_info[task_id].update({
            'stage': 'completed',
            'current': self._task_info[task_id]['total'],
            'message': message
        })

        update = ProgressUpdate(
            task_id=task_id,
            stage='completed',
            current=self._task_info[task_id]['total'],
            total=self._task_info[task_id]['total'],
            message=message
        )
        await self._tasks[task_id].put(update)
        await self._tasks[task_id].put(None)

    async def error(self, task_id: str, error_message: str) -> None:
        if task_id not in self._tasks:
            return

        self._task_info[task_id].update({
            'stage': 'error',
            'message': error_message
        })

        update = ProgressUpdate(
            task_id=task_id,
            stage='error',
            current=0,
            total=self._task_info[task_id]['total'],
            message=error_message
        )
        await self._tasks[task_id].put(update)
        await self._tasks[task_id].put(None)

    async def subscribe(self, task_id: str):
        if task_id not in self._tasks:
            return

        queue = self._tasks[task_id]
        while True:
            update = await queue.get()
            if update is None:
                break
            yield update

    def get_task_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self._task_info.get(task_id)

    async def cleanup(self, task_id: str) -> None:
        if task_id in self._tasks:
            del self._tasks[task_id]
        if task_id in self._task_info:
            del self._task_info[task_id]


class SyncProgressTracker:
    _callbacks: Dict[str, Callable] = {}
    _task_info: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def register_callback(cls, task_id: str, callback: Callable[[ProgressUpdate], None]) -> None:
        cls._callbacks[task_id] = callback

    @classmethod
    def unregister_callback(cls, task_id: str) -> None:
        if task_id in cls._callbacks:
            del cls._callbacks[task_id]

    @classmethod
    def update(cls, task_id: str, stage: str, current: int, total: int,
               message: str, detail: Optional[str] = None) -> None:
        if task_id not in cls._task_info:
            cls._task_info[task_id] = {'type': 'unknown', 'total': total}

        cls._task_info[task_id].update({
            'stage': stage,
            'current': current,
            'total': total,
            'message': message,
            'detail': detail
        })

        update = ProgressUpdate(
            task_id=task_id,
            stage=stage,
            current=current,
            total=total,
            message=message,
            detail=detail
        )

        if task_id in cls._callbacks:
            try:
                cls._callbacks[task_id](update)
            except Exception as e:
                logger.error(f"Progress callback error: {e}")

    @classmethod
    def complete(cls, task_id: str, message: str = "Completed") -> None:
        if task_id in cls._task_info:
            cls._task_info[task_id].update({
                'stage': 'completed',
                'message': message
            })

        update = ProgressUpdate(
            task_id=task_id,
            stage='completed',
            current=cls._task_info.get(task_id, {}).get('total', 100),
            total=cls._task_info.get(task_id, {}).get('total', 100),
            message=message
        )

        if task_id in cls._callbacks:
            try:
                cls._callbacks[task_id](update)
            except Exception:
                pass

    @classmethod
    def error(cls, task_id: str, error_message: str) -> None:
        if task_id in cls._task_info:
            cls._task_info[task_id].update({
                'stage': 'error',
                'message': error_message
            })

    @classmethod
    def get_task_info(cls, task_id: str) -> Optional[Dict[str, Any]]:
        return cls._task_info.get(task_id)