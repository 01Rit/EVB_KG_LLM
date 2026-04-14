import re
from pathlib import Path
from typing import Dict, Any


class PathClassifier:
    SOURCE_PATTERNS = {
        'patent': [r'专利', r'CN\d', r'WO\d', r'\d+发明专利'],
        'standard': [r'国标', r'GBT', r'GB/T', r'\d+-+\d+'],
        'paper': [r'学术论文', r'论文', r'journal', r'IEEE']
    }

    def classify(self, file_path: str) -> Dict[str, Any]:
        path = Path(file_path)
        filename = path.stem

        for source, patterns in self.SOURCE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, file_path, re.IGNORECASE):
                    return {
                        'source': source,
                        'source_type': 'pdf',
                        'file_name': filename,
                        'target_layers': ['L2', 'L3']
                    }

        return {
            'source': 'other',
            'source_type': 'pdf',
            'file_name': filename,
            'target_layers': ['L2', 'L3']
        }

    def get_metadata(self, file_path: str) -> Dict[str, Any]:
        path = Path(file_path)
        return {
            'file_name': path.stem,
            'file_extension': path.suffix,
            'file_size': path.stat().st_size if path.exists() else 0
        }
