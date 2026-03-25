# financial_search

**Tier**: retrieval  
**Name**: `financial_search`  

## Description

Retrieves SEC filings and financial news for companies and markets.

## When to Use

Finance, investment, earnings, regulatory filing, market analysis.

## Tools

- SecEdgarTool (filings)
- WebFetchTool filtered to financial domains

## Output Contract

RetrievalOutput — sources with ticker, form_type, fiscal_period, filing_date

**Credibility base**: 1.0 SEC filing; 0.90 earnings transcript; 0.80 financial news

**Min sources for OK status**: 2

## Constraints

- Extract ticker symbol and fiscal period into metadata
