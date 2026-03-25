# standards_search

**Tier**: retrieval  
**Name**: `standards_search`  

## Description

Fetches technical standards from NIST, ISO, IEEE and similar bodies.

## When to Use

Engineering, cybersecurity, compliance, technical specifications.

## Tools

- StandardsFetchTool (NIST CSF, IEEE Xplore free tier)

## Output Contract

RetrievalOutput — standards with standard_number, version, issuing_body

**Credibility base**: 1.0

**Min sources for OK status**: 1

## Constraints

- Extract standard_number, version, issuing_body into metadata
