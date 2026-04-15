from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
import yaml
import os

router = APIRouter()

CONFIG_PATH = os.environ.get('CONFIG_PATH', 'config.yaml')


def load_config() -> Dict[str, Any]:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    return get_default_config()


def save_config(config: Dict[str, Any]):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True)


def get_default_config() -> Dict[str, Any]:
    return {
        'mtm': {
            'tool_switch_default': 5,
            'position_default': 15,
            'mtm_base_seconds': 85
        },
        'as': {
            'h_weights': [0.2, 0.2, 0.2, 0.2, 0.2],
            's_weights': [0.25, 0.25, 0.25, 0.25]
        },
        'threshold': {
            'robot_threshold': 0.6,
            'human_threshold': 0.4
        },
        'cost': {
            'cost_decision_enabled': True,
            'robot_cost_default': 100.0,
            'human_cost_default': 80.0,
            'loss_cost_enabled': True
        },
        'parallel': {
            'parallel_level': 0
        },
        'time_coefficient': 1.0,
        'llm': {
            'temperature': 0.1,
            'max_tokens': 2000
        },
        'rag': {
            'top_k': 30,
            'similarity_threshold': 0.72,
            'retrieval_depth': 2
        }
    }


@router.get('/config')
async def get_config():
    config = load_config()
    return config


@router.put('/config/{category}')
async def update_config_category(category: str, data: Dict[str, Any]):
    config = load_config()

    if category not in config:
        raise HTTPException(status_code=400, detail=f'Invalid category: {category}')

    config[category] = data
    save_config(config)

    return {'code': 0, 'message': 'Config updated successfully'}


@router.get('/config/validate')
async def validate_config():
    config = load_config()
    errors = []

    if config.get('threshold', {}).get('robot_threshold', 0) <= \
       config.get('threshold', {}).get('human_threshold', 0):
        errors.append('robot_threshold must be greater than human_threshold')

    if errors:
        raise HTTPException(status_code=400, detail={'errors': errors})

    return {'code': 0, 'message': 'Config is valid'}


@router.post('/config/reload')
async def reload_config():
    config = load_config()
    return {'code': 0, 'message': 'Config reloaded', 'config': config}
