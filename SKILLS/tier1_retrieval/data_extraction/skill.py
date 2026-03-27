"""
data_extraction — extracts structured data (tables, statistics) from PDFs or
web pages.  If a PDF URL is present in the node description, uses PdfReaderTool;
otherwise falls back to a web search for data tables.
"""
import re

from tools.pdf_reader import PdfReaderTool
from tools.web_fetch import WebFetchTool
from ..base import BaseRetrievalSkill

_URL_RE  = re.compile(r"https?://\S+\.pdf\b", re.I)
_ANY_URL = re.compile(r"https?://\S+", re.I)


class DataExtractionSkill(BaseRetrievalSkill):
    name   = "data_extraction"
    min_ok = 1

    async def _fetch(self, node, query=None):
        description = query or node.description
        pdf_urls = _URL_RE.findall(description)
        if pdf_urls:
            return await PdfReaderTool().call_with_retry(
                query=description, url=pdf_urls[0].rstrip(".,)")
            )
        # No PDF URL — search web for data tables / statistics
        return await WebFetchTool().call_with_retry(
            f"{query or node.description} data table statistics CSV dataset",
            max_results=self._depth_n(node),
        )
