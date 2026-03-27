# dataset_search

**Tier**: retrieval  
**Name**: `dataset_search`  

## Description

The `dataset_search` skill is a specialized retrieval operation that physically queries the HuggingFace Hub's public dataset repository via its official API. Its primary cognitive process involves translating a user's natural language data request into structured search parameters, executing a targeted query against a massive, indexed corpus of machine learning datasets, and then performing a multi-stage filtering and enrichment process on the results. The skill does not download or analyze the actual dataset files; it performs metadata discovery and aggregation.

The specific data transformations it applies are:
1.  **Query Formulation**: It takes a user's intent (e.g., "sentiment analysis data in English") and formulates an effective search query, potentially using keywords, tags, or filters supported by the API.
2.  **API Interaction**: It calls the `DatasetHubTool`, which interfaces with the HuggingFace Hub, to retrieve a list of dataset objects matching the query. Each object contains a rich set of metadata fields.
3.  **Metadata Extraction & Structuring**: It parses the raw API response and systematically extracts the following critical fields for each dataset result:
    *   **`task_categories`**: The primary machine learning tasks the dataset is designed for (e.g., `text-classification`, `question-answering`, `image-generation`). This is extracted from the dataset's tags or `task_categories` metadata.
    *   **`language`**: The linguistic content of the dataset (e.g., `en`, `multilingual`, `fr`), extracted from the `language` or `languages` metadata field.
    *   **`size_categories`**: A categorical indicator of the dataset's volume (e.g., `n<1K`, `10K<n<100K`, `1M<n<10M`), extracted from the `size_categories` metadata.
    *   Additional standardized fields: `dataset_name`, `author`, `downloads`, `license`, and a `description` snippet.
4.  **Result Ranking & Pruning**: It typically ranks results by relevance (often influenced by download count or Hub's internal scoring) and prunes any results missing the core extracted metadata, ensuring output quality.
5.  **Output Formatting**: It packages the enriched and filtered list of dataset metadata objects into the standardized `RetrievalOutput` format, ready for downstream analysis or selection.

## When to Use

Use this skill as the first step in any pipeline that requires identifying and evaluating publicly available datasets for machine learning or data science work.

**Specific Scenarios:**
*   **Model Development Scoping**: "I want to build a model for named entity recognition. What datasets are available?"
*   **Benchmarking Research**: "Find all text summarization datasets larger than 10k samples to compare model performance."
*   **Educational or Prototyping**: "I need a small, simple image classification dataset for a tutorial."
*   **Data Source Investigation**: "What are the most popular multilingual datasets for speech recognition?"
*   **Literature Review Support**: "Find datasets used in recent papers on commonsense reasoning."

**Upstream Dependencies & Expected Input:**
This skill is typically a **root node** in an execution DAG. It requires a clear **search query or data need description** from the user or planner. The input is natural language text specifying:
*   **Domain/Task**: (e.g., "sentiment analysis", "object detection").
*   **Key Attributes**: (e.g., "in French", "medical", "large-scale").
*   **Optional Constraints**: (e.g., "with a permissive license", "from a research institution").

It does **not** require pre-retrieved documents or data. The input is the search intent itself.

**Edge Cases - When NOT to Use This Skill:**
*   **For Private/Internal Data**: Do not use if the user needs to search a company's internal database or a private Google Drive.
*   **For Non-Dataset Artifacts**: Do not use to search for pre-trained *models*, Spaces, or papers on the HuggingFace Hub. Use `model_search` or a general web search skill instead.
*   **When Specific Dataset is Named**: If the user explicitly says "Get the GLUE benchmark dataset," a more direct `dataset_info` or `dataset_load` skill may be more appropriate.
*   **For Real-Time/Streaming Data**: This skill retrieves metadata for static, archived datasets, not live data feeds or APIs.

**Downstream Nodes That Usually Follow:**
1.  **`dataset_info`**: To get detailed configuration and subset information for a dataset shortlisted from these search results.
2.  **`dataset_load`**: To actually download and sample a specific dataset identified here.
3.  **`analysis` or `evaluation` Skills**: To analyze the metadata (e.g., "compare licenses and sizes of the top 5 results").
4.  **`planner` or `decider`**: To present options to the user for selection before proceeding.

## Tools

- DatasetHubTool (HuggingFace Hub API)

## Output Contract

RetrievalOutput — datasets with task_categories, size, license, downloads

**Credibility base**: 0.80; 0.90 if from institutional author

**Min sources for OK status**: 2

## Constraints

*   **Scope Limitation**: This skill **must only** search the HuggingFace Hub for datasets. It must not attempt to query other repositories like Kaggle, Google Dataset Search, or academic portals unless explicitly chained with another skill.
*   **Metadata Extraction Imperative**: You **must** explicitly extract and populate the `task_categories`, `language`, and `size_categories` fields for each dataset in the output metadata. Do not return datasets where these core fields are completely missing or unparsable.
*   **No Hallucination of Data**: The skill retrieves *metadata only*. The output must not contain fabricated statistics, descriptions, or attributes not present in the Hub API response. If a field is absent from the API, it should be `null` or an empty string in the output.
*   **Result Limit Awareness**: The underlying API may have pagination or rate limits. The skill should aim to return a manageable, high-quality set of results (e.g., 10-20 most relevant) rather than attempting to fetch every possible match.
*   **Credibility Application**: Apply the credibility score precisely: a base of `0.80` for all results, increasing to `0.90` **only if** the dataset's `author` field clearly indicates a recognized institution (e.g., "google-research", "facebook", "stanford-nlp"). Do not guess or infer institutional status.
*   **Minimum Sources**: The skill's status should only be considered `OK` if it successfully retrieves and processes metadata for **at least 2 distinct datasets**. If only one or zero datasets are found, the status must reflect a partial or failed retrieval.