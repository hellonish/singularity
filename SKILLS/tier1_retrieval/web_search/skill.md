# web_search

**Tier**: retrieval  
**Name**: `web_search`  

## Description

Fetches publicly accessible web pages relevant to the query.

## When to Use

General information retrieval when no specialised database applies. Use as fallback when other retrieval skills fail.

## Tools

- WebFetchTool (DuckDuckGo primary, Tavily fallback)

## Output Contract

RetrievalOutput — sources list with url, snippet, credibility_base

**Credibility base**: 0.75 general web; 0.85 for .gov/.edu domains

**Min sources for OK status**: 3

## Constraints

- No jurisdiction filter
- Apply recency filter if 'recency' in acceptance axes
