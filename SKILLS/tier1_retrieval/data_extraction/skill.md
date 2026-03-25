# data_extraction

**Tier**: retrieval  
**Name**: `data_extraction`  

## Description

Extracts structured data (tables, numbers) from PDFs or web pages.

## When to Use

When upstream sources contain tables, statistics, or structured data needing extraction for analysis.

## Tools

- PdfReaderTool
- BeautifulSoup HTML table parser

## Output Contract

RetrievalOutput — tables as list[list[str]] with source citation

**Credibility base**: Inherits from source

**Min sources for OK status**: 1

## Constraints

- Must cite the source document the data was extracted from
