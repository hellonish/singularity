"""
pdf_deep_extract — fetches and chunks a PDF from the URL embedded in the
node description (or any URL present in the description text).
"""
import re

from tools.pdf_reader import PdfReaderTool
from ..base import BaseRetrievalSkill

_URL_RE = re.compile(r"https?://\S+", re.I)


class PdfDeepExtractSkill(BaseRetrievalSkill):
    name   = "pdf_deep_extract"
    min_ok = 1

    async def _fetch(self, node, query=None):
        description = query or node.description
        urls = _URL_RE.findall(description)
        url  = urls[0].rstrip(".,)") if urls else None
        return await PdfReaderTool().call_with_retry(
            query=description, url=url
        )
