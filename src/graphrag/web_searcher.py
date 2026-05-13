from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class WebSearcher:
    """
    DuckDuckGo 联网搜索器。
    为自然语言查询补充实时网络信息。
    """

    def __init__(self):
        self._ddgs = None  # 延迟初始化

    @property
    def ddgs(self):
        if self._ddgs is None:
            try:
                from duckduckgo_search import DDGS
                self._ddgs = DDGS()
            except ImportError:
                logger.warning("duckduckgo-search not installed, web search disabled")
                return None
        return self._ddgs

    async def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        搜索 query，返回 top_k 条结果。

        Returns:
            List of dicts with keys: title, url, snippet
        """
        if self.ddgs is None:
            logger.debug("WebSearcher: DDGS not available, returning empty")
            return []

        try:
            results = []
            for r in self.ddgs.text(query, max_results=top_k):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                })
            logger.info(f"WebSearcher: found {len(results)} results for query={query[:50]}")
            return results
        except Exception as e:
            logger.error(f"WebSearcher search failed: {e}")
            return []

    def search_sync(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """同步版本的 search（供非 async 上下文使用）"""
        if self.ddgs is None:
            return []

        try:
            results = []
            for r in self.ddgs.text(query, max_results=top_k):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                })
            return results
        except Exception as e:
            logger.error(f"WebSearcher search_sync failed: {e}")
            return []
