"""
GitHubTool — searches GitHub repositories via PyGithub.

GITHUB_TOKEN env var is optional but strongly recommended (raises rate limit
from 60 → 5,000 req/hr).
credibility_base: 0.70 base + stars boost → max 0.90.
"""
import asyncio
import itertools
import os

from .base import ToolBase, ToolResult

_README_MAX_CHARS = 1500


def _search(query: str, max_results: int) -> list[dict]:
    from github import Github

    token = os.getenv("GITHUB_TOKEN")
    g     = Github(token) if token else Github()

    results = []
    for repo in itertools.islice(g.search_repositories(query, sort="stars"), max_results):
        try:
            readme = repo.get_readme().decoded_content.decode("utf-8", errors="ignore")
            readme = readme[:_README_MAX_CHARS]
        except Exception:
            readme = ""

        # credibility: 0.70 base, up to +0.20 from stars (capped at 0.90)
        stars_boost = min(0.20, (repo.stargazers_count / 1000) * 0.20)
        cred        = round(0.70 + stars_boost, 3)

        results.append({
            "title":       repo.full_name,
            "url":         repo.html_url,
            "readme":      readme,
            "date":        repo.updated_at.strftime("%Y-%m-%d") if repo.updated_at else None,
            "stars":       repo.stargazers_count,
            "language":    repo.language,
            "license":     (repo.license.name if repo.license else None),
            "description": (repo.description or "")[:200],
            "cred":        cred,
        })
    return results


class GitHubTool(ToolBase):
    name = "github"

    async def call(self, query: str, max_results: int = 10, **kwargs) -> ToolResult:
        raw = await asyncio.to_thread(_search, query, max_results)

        if not raw:
            raise ValueError("No GitHub results found")

        sources = [
            {
                "title":            r["title"],
                "url":              r["url"],
                "content":          r["readme"] or r["description"],  # full README — ingested by run_fanout
                "snippet":          (r["readme"] or r["description"])[:300],  # preview only
                "date":             r["date"],
                "source_type":      "code",
                "credibility_base": r["cred"],
                "metadata": {
                    "stars":    r["stars"],
                    "language": r["language"],
                    "license":  r["license"],
                },
            }
            for r in raw
        ]
        avg_cred = sum(s["credibility_base"] for s in sources) / len(sources)
        content  = "\n\n".join(
            f"[{s['title']}] ⭐ {s['metadata']['stars']} | {s['metadata']['language']}\n{s['snippet']}"
            for s in sources[:5]
        )
        return ToolResult(content=content, sources=sources, credibility_base=avg_cred, raw=raw)
