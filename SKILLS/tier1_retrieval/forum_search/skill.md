# forum_search

**Tier**: retrieval  
**Name**: `forum_search`  

## Description

Retrieves community discussions from Stack Overflow, Reddit, HN, and domain forums.

## When to Use

Practitioner insights, community consensus, real-world problem/solution patterns.

## Tools

- WebFetchTool filtered to stackoverflow.com, reddit.com, news.ycombinator.com

## Output Contract

RetrievalOutput — posts with vote_count, is_accepted_answer, forum_name

**Credibility base**: 0.60 general; 0.70 Stack Overflow accepted answer

**Min sources for OK status**: 3

## Constraints

- Accepted answers on SO score 0.70
- Extract vote_count into metadata
