# pdf_deep_extract

**Tier**: retrieval  
**Name**: `pdf_deep_extract`  

## Description

This skill performs a comprehensive, multi-stage extraction of structured and unstructured content from Portable Document Format (PDF) files. It physically downloads the PDF from a provided URL or accesses a local file path, then applies a layered parsing strategy to recover the complete semantic content. The cognitive process involves first attempting to use the primary `pdfplumber` library, which excels at preserving textual layout and extracting tabular data with high fidelity. If this primary method fails due to PDF encryption, corruption, or complex formatting, the skill automatically engages a fallback parser (`PyMuPDF`/`fitz`) that is more robust for basic text extraction from problematic files. The core data transformation involves ingesting a binary PDF stream and outputting a structured object containing: 1) The full textual content, segmented into coherent chunks of approximately 2000 tokens, with each chunk annotated with its source page number; and 2) All detected tabular data, where each table is converted into a two-dimensional list of strings (list[list[str]]), preserving row and column structure. This process transforms an opaque document format into searchable, analyzable text and data suitable for downstream reasoning tasks.

## When to Use

- **Specific Scenarios**:
    1. The primary scenario is when a `node.description` explicitly contains a direct, accessible HTTP/HTTPS URL ending in `.pdf` (e.g., `https://example.com/report.pdf`).
    2. When the description contains an absolute or relative local file path to a PDF document (e.g., `./data/papers/study.pdf` or `/mnt/docs/contract.pdf`).
    3. When upstream planning has identified a need for the detailed contents of a PDF document cited in a user query, such as "Summarize the findings in the PDF at https://arxiv.org/pdf/1234.56789.pdf".
    4. As a foundational retrieval step in a research, analysis, or document review pipeline, where the extracted text and tables will be used for summarization, question answering, or data aggregation.

- **Upstream Dependencies & Expected Input**:
    - This skill is typically a leaf node in the retrieval tier. Its primary and only required upstream input is a node object where the `description` attribute is a string containing **exactly one PDF URL or file path**. It expects no pre-processing; the skill handles the entire download and parsing workflow internally.

- **Edge Cases When NOT to Use It**:
    1. **Non-PDF URLs**: Do not use if the URL points to an HTML webpage, image (`.jpg`, `.png`), Word document (`.docx`), or any other non-PDF file type. The parsers will fail or produce meaningless output.
    2. **Password-Protected/Encrypted PDFs**: The skill cannot bypass standard PDF encryption. If the PDF is secured with a user or owner password, extraction will fail.
    3. **Scanned Image-Only PDFs**: If the PDF contains only scanned images of text without an embedded text layer (i.e., it is not OCR'd), this skill will extract little to no usable text. A dedicated OCR skill is required for such documents.
    4. **Descriptions with Multiple URLs or Ambiguous References**: If the `node.description` contains multiple URLs or a narrative like "look at the PDFs about topic X," this skill is inappropriate. It is designed for a single, explicitly provided PDF source.
    5. **When Only Metadata is Needed**: If the task only requires document metadata (author, title, creation date) and not the full content, a lighter-weight skill should be used.

- **Downstream Nodes That Usually Follow**:
    - The output (`RetrievalOutput` with chunks and tables) is typically passed to:
        1. **Chunk Processing Skills**: Like `chunk_summarize` or `chunk_analyze` for content condensation.
        2. **Retrieval-Augmented Generation (RAG) Skills**: The chunks are ideal for populating a context window for a `generate` skill answering specific questions about the document.
        3. **Table Analysis Skills**: Extracted tables can be sent to skills that interpret or reformat tabular data.
        4. **Multi-Document Synthesis Skills**: If multiple PDFs are processed, their outputs feed into skills that compare or combine information across documents.

## Tools

- PdfReaderTool (pdfplumber primary, PyMuPDF fallback)

## Execution Model

*[Note: This section was not present in the original and is not added, as per instructions to retain only original sections.]*

## Output Contract

RetrievalOutput — chunks with page_number, tables as list[list[str]]

**Credibility base**: Inherits from source; defaults to 0.80

**Min sources for OK status**: 1

## Constraints

- **Input Constraint**: The `node.description` must contain **one and only one** clearly identifiable PDF URL (with `http://`/`https://` and typically a `.pdf` extension) or a valid local system file path to a PDF. The skill will fail if this field is empty, ambiguous, or contains a non-PDF resource locator.
- **Token Limit & Chunking**: The extracted full text **must** be split into chunks of approximately **2000 tokens** (using the planner's tokenizer). Each chunk **must** be annotated with its source `page_number` to maintain provenance. Do not output a single, monolithic text block.
- **Hallucination Prohibition**: The skill **must not** generate, infer, or add any content not explicitly present in the source PDF. It is a strict extractor. If a page is blank or contains only images, the corresponding text chunk should be an empty string or omitted, not filled with descriptive guesses.
- **Scope Limitation**: The skill's scope is **solely** the provided PDF. It must not perform web searches to find related PDFs, interpret external links within the PDF, or fetch additional resources mentioned in the document's bibliography.
- **Error Handling**: If the primary (`pdfplumber`) extraction fails, the fallback (`PyMuPDF`) must be invoked automatically. If both parsers fail, the skill must return a `RetrievalOutput` with an error status and empty chunks/tables, not raise an unhandled exception that crashes the graph.
- **Table Integrity**: Extracted tables should aim for structural fidelity. Merged cells or complex formatting may be simplified. The output contract of `list[list[str]]` must be strictly adhered to; no nested dictionaries or custom objects for tables are permitted.