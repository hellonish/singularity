# gov_search

**Tier**: retrieval  
**Name**: `gov_search`  

## Description

Retrieves content exclusively from government (.gov) domains.

## When to Use

Policy, regulation, official statistics, public health guidance.

## Tools

- WebFetchTool with site:*.gov DuckDuckGo filter

## Output Contract

RetrievalOutput — sources with department, publication_date

**Credibility base**: 0.95

**Min sources for OK status**: 2

## Constraints

- Must filter strictly to .gov/.gov.* domains
