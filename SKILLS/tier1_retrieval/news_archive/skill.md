# news_archive

**Tier**: retrieval  
**Name**: `news_archive`  

## Description

Retrieves recent news articles from authoritative outlets.

## When to Use

Current events, breaking news, press releases, media coverage.

## Tools

- WebFetchTool filtered to reuters.com, apnews.com, bbc.com, ft.com, wsj.com

## Output Contract

RetrievalOutput — articles with headline, author, publication, date

**Credibility base**: 0.80

**Min sources for OK status**: 3

## Constraints

- Always apply recency filter
- Extract author and publication into metadata
