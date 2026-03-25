# pdf_deep_extract

**Tier**: retrieval  
**Name**: `pdf_deep_extract`  

## Description

Downloads and extracts full text + tables from a PDF at a given URL.

## When to Use

When node.description contains a direct URL to a PDF document.

## Tools

- PdfReaderTool (pdfplumber primary, PyMuPDF fallback)

## Output Contract

RetrievalOutput — chunks with page_number, tables as list[list[str]]

**Credibility base**: Inherits from source; defaults to 0.80

**Min sources for OK status**: 1

## Constraints

- Node description must contain a PDF URL or local path
- Split into 2000-token chunks with page numbers
