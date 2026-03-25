# code_search

**Tier**: retrieval  
**Name**: `code_search`  

## Description

Searches GitHub for repositories and extracts README content.

## When to Use

Software, open-source libraries, implementation patterns, technical stacks.

## Tools

- GitHubTool (PyGithub; GITHUB_TOKEN optional for higher rate limit)

## Output Contract

RetrievalOutput — repos with stars, language, license, readme_excerpt

**Credibility base**: 0.70 base; up to 0.90 based on star count

**Min sources for OK status**: 2

## Constraints

- credibility_base = min(0.70 + stars/1000 * 0.20, 0.90)
