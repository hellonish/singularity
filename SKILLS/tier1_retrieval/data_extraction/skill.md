# data_extraction

**Tier**: retrieval  
**Name**: `data_extraction`  

## Description

The `data_extraction` skill is a specialized data retrieval and transformation operation designed to locate, parse, and convert semi-structured or structured data found within digital documents into a clean, machine-readable format. It physically processes PDF files or HTML web pages, scanning their content to identify data containers such as tables, matrices, lists of figures, and structured statistical enumerations. The cognitive process involves first identifying the document type, then applying the appropriate parsing tool to load the raw content. It subsequently performs pattern recognition to locate candidate table structures—looking for grid-like arrangements, consistent delimiters, `<table>` HTML tags, or textual markers like "Table X:" or numerical columns. Once identified, the skill extracts the raw cell data, applies cleaning transformations to remove extraneous whitespace, newlines, and non-data artifacts, and structures it into a two-dimensional list (rows and columns). This process transforms visual or markup-based data representations into a pure string-based matrix, preserving the logical relationships between headers and data points. The final output is a structured data object ready for quantitative analysis, visualization, or storage, accompanied by precise source attribution.

## When to Use

- **Specific Scenarios**:
    1. When an upstream source (e.g., a research paper, financial report, government PDF, or product webpage) is identified as containing numerical datasets, comparison tables, pricing matrices, schedules, or statistical summaries.
    2. When the user's query explicitly requests numerical analysis, trend calculation, data comparison, or the population of a structured template with figures from a source.
    3. When a previous skill (e.g., `web_search` or `document_retrieval`) has fetched a document and a preliminary scan indicates the presence of tabular data or structured lists that are not easily interpretable as plain text.
    4. As a prerequisite for downstream analytical skills like `data_analysis`, `chart_generation`, or `report_synthesis` that require clean, structured data inputs.

- **Upstream Dependencies & Input Format**:
    - This skill expects upstream nodes to provide **one or more source documents** with clear file paths or HTML content strings. The ideal input is a reference to a PDF file (e.g., "/mnt/data/report.pdf") or a URL/HTML string confirmed to contain tabular data. The skill does NOT perform web fetching; it assumes documents are already retrieved and accessible locally or as provided content.

- **Edge Cases - When NOT to Use**:
    1. **For Unstructured Text Extraction**: Do not use this skill to extract paragraphs, general ideas, or qualitative summaries. Use `text_extraction` or `summarization` skills instead.
    2. **For Simple Number Lookup**: If the required data is a single, explicitly stated number within a sentence (e.g., "The population is 1.4 million"), use a `fact_extraction` or Q&A skill, not full table parsing.
    3. **When Data is Already Structured**: If the upstream data is already in a clean JSON, CSV, or list format, this skill is redundant. Pass that data directly to analysis nodes.
    4. **For Images of Tables**: This skill cannot parse data from tables rendered as images within PDFs or web pages (OCR is not included). It will fail or return empty results.
    5. **When Source is Unavailable or Corrupted**: If the document path is invalid or the HTML is malformed, this skill will error. Ensure upstream retrieval succeeds first.

- **Downstream Nodes**:
    - Typically followed by `data_analysis` (for statistical computation), `chart_generation` (for visualization), `report_writing` (for incorporating figures into narratives), or `data_storage` nodes. The extracted list-of-lists format is the standard input for these subsequent processing steps.

## Tools

- PdfReaderTool
- BeautifulSoup HTML table parser

## Execution Model

The skill executes by first determining the MIME type or structure of the input source. For PDFs, it uses the PdfReaderTool to extract all text and spatial layout information, heuristically reconstructing table boundaries based on text alignment and proximity. For HTML, it uses BeautifulSoup to find all `<table>` elements, then iterates through `<tr>` and `<td>`/`<th>` tags to build the row-column matrix. All cell content is stripped of extra HTML tags and normalized. The output is a list where each sub-list represents a row, and each string within represents a cell's content.

## Output Contract

RetrievalOutput — tables as list[list[str]] with source citation

**Credibility base**: Inherits from source

**Min sources for OK status**: 1

## Constraints

1. **Source Citation Mandatory**: Every extracted table **must** be accompanied by a precise citation of the source document (filename, URL, or provided identifier). The Planner must ensure upstream nodes pass source metadata. The skill will fail if asked to process content without a citable source reference.
2. **No Hallucination of Data**: The skill must extract **only** the data physically present in the source. It must not infer missing values, extrapolate trends, or fill empty cells with assumptions. Empty cells should be represented as empty strings (`""`).
3. **Token/Size Limitations**: Processing extremely large PDFs (100+ pages) or HTML with massive nested tables may hit memory or timeout limits. The Planner should pre-filter documents to relevant pages/sections where possible, or split the task into multiple extractions.
4. **Scope Restriction - No External Fetching**: This skill is a pure parser. It **cannot** fetch documents from the web, databases, or APIs. It operates only on provided file paths or HTML strings. The Planner must chain a retrieval skill (e.g., `web_search`, `document_retrieval`) before this one if sources are not already available.
5. **Structured Data Focus**: It is optimized for clearly delineated tables. Data in paragraph form, bullet lists without consistent columns, or free-form text with embedded numbers will not be parsed correctly. The Planner should verify the source contains genuine table structures before assignment.
6. **Output Format Strictness**: The output will always be a list of lists of strings, even for single-row/column tables. Downstream nodes must be prepared to handle this format. The skill does not convert strings to numerical types; that is the responsibility of analysis nodes.