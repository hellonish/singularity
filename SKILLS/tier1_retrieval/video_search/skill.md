# video_search

**Tier**: retrieval  
**Name**: `video_search`  

## Description

Finds YouTube videos and extracts transcripts for text analysis.

## When to Use

Conference talks, tutorials, expert interviews, documentary evidence.

## Tools

- WebFetchTool (site:youtube.com DuckDuckGo)
- YouTubeTranscriptTool

## Output Contract

RetrievalOutput — videos with channel, duration, transcript_excerpt

**Credibility base**: 0.65 general; 0.80 academic/conference channel

**Min sources for OK status**: 2

## Constraints

- Must extract transcript; skip if transcript unavailable
