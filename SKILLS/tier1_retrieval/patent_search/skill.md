# patent_search

**Tier**: retrieval  
**Name**: `patent_search`  

## Description

Searches patent databases for prior art and IP information.

## When to Use

IP research, technology landscape, prior art analysis.

## Tools

- WebFetchTool filtered to patents.google.com, espacenet.epo.org

## Output Contract

RetrievalOutput — patents with patent_number, assignee, filing_date, abstract

**Credibility base**: 0.95

**Min sources for OK status**: 2

## Constraints

- Extract patent_number and assignee into metadata
