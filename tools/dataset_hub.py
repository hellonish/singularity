"""
DatasetHubTool — searches HuggingFace Hub for datasets.

Uses `huggingface_hub` Python SDK (free, no auth required for public datasets).
credibility_base: 0.90 if author is an institution, 0.80 otherwise.
"""
import asyncio

from .base import ToolBase, ToolResult

# Known institutional authors on HuggingFace
_INSTITUTIONS = {
    "google", "microsoft", "facebook", "meta", "openai", "anthropic",
    "allenai", "huggingface", "stanfordnlp", "deepmind", "nvidia",
    "amazon", "apple", "ibm", "EleutherAI", "bigscience", "ai2",
}


def _search(query: str, limit: int) -> list[dict]:
    from huggingface_hub import list_datasets

    results = []
    for ds in list_datasets(search=query, limit=limit):
        results.append({
            "id":            ds.id,
            "author":        ds.author or "",
            "description":   (getattr(ds, "description", None) or "")[:400],
            "tags":          list(ds.tags or [])[:10],
            "downloads":     getattr(ds, "downloads", 0) or 0,
            "last_modified": str(ds.last_modified)[:10] if ds.last_modified else None,
            "url":           f"https://huggingface.co/datasets/{ds.id}",
        })
    return results


class DatasetHubTool(ToolBase):
    name = "dataset_hub"

    async def call(self, query: str, max_results: int = 10, **kwargs) -> ToolResult:
        raw = await asyncio.to_thread(_search, query, max_results)

        if not raw:
            raise ValueError("No HuggingFace datasets found")

        sources = []
        for ds in raw:
            is_institution = any(
                inst in ds["author"].lower() for inst in _INSTITUTIONS
            )
            sources.append({
                "title":            ds["id"],
                "url":              ds["url"],
                "snippet":          ds["description"],
                "date":             ds["last_modified"],
                "source_type":      "dataset",
                "credibility_base": 0.90 if is_institution else 0.80,
                "metadata": {
                    "author":    ds["author"],
                    "tags":      ds["tags"],
                    "downloads": ds["downloads"],
                },
            })

        avg_cred = sum(s["credibility_base"] for s in sources) / len(sources)
        content  = "\n\n".join(
            f"[{s['title']}] by {s['metadata']['author']} ({s['metadata']['downloads']} downloads)\n{s['snippet']}"
            for s in sources[:5]
        )
        return ToolResult(content=content, sources=sources, credibility_base=avg_cred, raw=raw)
