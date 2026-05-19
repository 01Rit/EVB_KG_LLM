from typing import List, Dict, Any
import logging
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

SERPER_ENDPOINT = "https://google.serper.dev/search"
REQUEST_TIMEOUT = 15


class WebSearcher:
    """Serper API 联网搜索器（Google 搜索代理）"""

    def __init__(self, api_key: str = "", verify_ssl: bool = True):
        self.api_key = api_key
        self.verify_ssl = verify_ssl

    async def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        搜索 query，返回 top_k 条结果。

        Returns:
            List of dicts with keys: title, url, snippet
        """
        if not self.api_key:
            logger.warning("WebSearcher: SERPER_API_KEY not configured, web search disabled")
            return []

        try:
            resp = requests.post(
                SERPER_ENDPOINT,
                json={"q": query, "gl": "cn", "hl": "zh-cn"},
                headers={
                    "X-API-KEY": self.api_key,
                    "Content-Type": "application/json",
                },
                timeout=REQUEST_TIMEOUT,
                verify=self.verify_ssl,
            )
            resp.raise_for_status()
            data = resp.json()
            organic = data.get("organic", [])

            results = []
            for r in organic[:top_k]:
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("link", ""),
                    "snippet": r.get("snippet", ""),
                })

            logger.info(f"WebSearcher: found {len(results)} results for query={query[:50]}")
            return results

        except requests.Timeout:
            logger.error(f"WebSearcher: request timeout for query={query[:50]}")
            return []
        except requests.RequestException as e:
            logger.error(f"WebSearcher: request failed: {e}")
            return []
        except Exception as e:
            logger.error(f"WebSearcher: unexpected error: {e}")
            return []
