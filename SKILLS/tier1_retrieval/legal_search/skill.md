# legal_search

**Tier**: retrieval  
**Name**: `legal_search`  

## Description

Searches CourtListener for case law and legal opinions.

## When to Use

Legal research, regulatory analysis, compliance, policy domains.

## Tools

- CourtListenerTool

## Output Contract

RetrievalOutput — cases with citation, court, date_filed, jurisdiction

**Credibility base**: 0.95

**Min sources for OK status**: 1

## Constraints

- HARD RULE: if 'jurisdiction_relevance' in acceptance axes, filter to correct jurisdiction only
- If 0 sources remain after jurisdiction filter → FAILED; do NOT fall back to web for legal conclusions
