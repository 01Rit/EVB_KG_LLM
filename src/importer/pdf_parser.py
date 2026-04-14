import fitz
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class PDFParser:
    def __init__(self, extract_images: bool = False):
        self.extract_images = extract_images

    def parse(self, file_path: str) -> Dict[str, Any]:
        try:
            doc = fitz.open(file_path)
        except Exception as e:
            logger.error(f"Failed to open PDF {file_path}: {e}")
            raise

        text_content = []
        for page_num, page in enumerate(doc):
            text = page.get_text()
            text_content.append({
                'page': page_num + 1,
                'text': text
            })

        doc.close()

        return {
            'file_path': file_path,
            'page_count': len(text_content),
            'pages': text_content,
            'full_text': '\n\n'.join([p['text'] for p in text_content])
        }

    def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        doc = fitz.open(file_path)
        metadata = {
            'title': doc.metadata.get('title', ''),
            'author': doc.metadata.get('author', ''),
            'subject': doc.metadata.get('subject', ''),
            'creator': doc.metadata.get('creator', ''),
            'page_count': len(doc)
        }
        doc.close()
        return metadata

    def extract_images(self, file_path: str) -> List[Dict[str, Any]]:
        if not self.extract_images:
            return []

        images = []
        doc = fitz.open(file_path)

        for page_num, page in enumerate(doc):
            image_list = page.get_images()
            for img_index, img in enumerate(image_list):
                images.append({
                    'page': page_num + 1,
                    'index': img_index,
                    'xref': img[0]
                })

        doc.close()
        return images