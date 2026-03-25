# dataset_search

**Tier**: retrieval  
**Name**: `dataset_search`  

## Description

Searches HuggingFace Hub for public datasets.

## When to Use

Data science, ML benchmarking, empirical research needing raw data.

## Tools

- DatasetHubTool (HuggingFace Hub API)

## Output Contract

RetrievalOutput — datasets with task_categories, size, license, downloads

**Credibility base**: 0.80; 0.90 if from institutional author

**Min sources for OK status**: 2

## Constraints

- Extract task_categories, language, size_categories into metadata
