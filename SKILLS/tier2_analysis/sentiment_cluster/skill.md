# sentiment_cluster

**Tier**: analysis  
**Name**: `sentiment_cluster`  

## Description

Clusters social/forum sources by sentiment and topic.

## When to Use

After social_search or forum_search when opinion landscape mapping is needed.

## Execution Model

LLM-based

**Prompt file**: `prompts/sentiment_cluster.md`

## Output Contract

AnalysisOutput — clusters: [{label, sentiment, representative_posts, size}]
