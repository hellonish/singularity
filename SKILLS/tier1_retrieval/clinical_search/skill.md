# clinical_search

**Tier**: retrieval  
**Name**: `clinical_search`  

## Description

Searches PubMed and ClinicalTrials.gov for clinical evidence.

## When to Use

Medical, pharmaceutical, clinical, or public health domains.

## Tools

- PubmedTool
- ClinicalTrialsTool

## Output Contract

RetrievalOutput — sources with trial phase, PMID/NCT, outcomes

**Credibility base**: 0.92 peer-reviewed; 1.0 clinical trial registry

**Min sources for OK status**: 2

## Constraints

- At least one source must be a trial or systematic review for OK status
- Extract clinical_significance metadata
