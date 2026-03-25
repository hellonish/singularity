# social_search

**Tier**: retrieval  
**Name**: `social_search`  

## Description

Collects social media posts for sentiment and public opinion signals.

## When to Use

Brand analysis, public perception, trend detection, market sentiment.

## Tools

- WebFetchTool filtered to social platforms

## Output Contract

RetrievalOutput — posts with sentiment (mixed/positive/negative), platform

**Credibility base**: 0.60

**Min sources for OK status**: 5

## Constraints

- Low credibility — always disclose source type in output
- Never use as sole evidence for factual claims
