# academic_search

**Tier**: retrieval  
**Name**: `academic_search`  

## Description

Searches arXiv and Semantic Scholar for peer-reviewed and preprint papers.

## When to Use

Science, technology, medicine, or any topic where academic evidence is expected.

## Tools

- ArxivTool
- SemanticScholarTool (both queried in parallel, deduplicated by title)

## Output Contract

RetrievalOutput — papers with title, authors, abstract, year, url

**Credibility base**: 0.88 preprint; 0.95 published journal article

**Min sources for OK status**: 2

## Constraints

- Always apply recency filter
- Deduplicate by title prefix (first 50 chars)
