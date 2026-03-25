# multimedia_search

**Tier**: retrieval  
**Name**: `multimedia_search`  

## Description

The `multimedia_search` skill is a specialized retrieval agent that performs targeted web searches to locate and retrieve publicly accessible multimedia files, excluding YouTube-hosted videos. It physically executes a query across the open web, utilizing a tool configured with specific filters to prioritize image files (e.g., .jpg, .png, .gif, .webp), audio files (e.g., .mp3, .wav, .ogg), and video files from platforms other than YouTube (e.g., .mp4, .mov, direct video links from services like Vimeo, Dailymotion, or institutional archives). The cognitive process involves parsing the user's request or the Planner's objective into a set of concrete, optimized search queries designed to surface media assets. It then processes the raw search results, applying a data transformation that extracts, validates, and structures each potential media item into a standardized schema. This includes classifying the media type, capturing the direct source URL, and assessing the contextual relevance of the find to the original query. The agent focuses on evidence gathering, aiming to return a collection of media references that serve as visual or auditory proof, support analysis, or provide material for further inspection.

## When to Use

Use this skill in the following specific scenarios:
*   **Visual Evidence for Claims**: When a claim or statement requires photographic, diagrammatic, or screenshot evidence (e.g., "find a picture of the newly unveiled monument," "show me the damage from the recent storm").
*   **Media Analysis & Verification**: As a first step in analyzing the provenance, editing, or context of a piece of media. For instance, to find other instances of an image online to check for manipulation or to locate the original source of an audio clip.
*   **Copyright & Licensing Research**: To identify the availability and usage contexts of specific images, audio tracks, or videos across the web, aiding in understanding public domain status or common licensing.
*   **Content Curation & Reference Gathering**: For assembling a set of reference images, audio samples, or video examples on a given topic for creative, educational, or planning purposes (e.g., "find architectural styles of Pacific Northwest libraries," "gather examples of 1920s jazz recordings").
*   **Non-YouTube Video Discovery**: When the need is for instructional, promotional, archival, or news video content hosted on platforms like Vimeo, educational sites, or news outlets that are not YouTube.

**Upstream Dependencies & Expected Input**:
This skill typically requires a clear, concise search objective or query string from an upstream planning node. The ideal input is a well-formed natural language query that specifies:
1.  The **subject matter** (e.g., "Mars rover Perseverance").
2.  The desired **media type** if specific ("images," "audio recordings," "video").
3.  Any relevant **context, timeframe, or distinguishing features** ("latest images from February 2024," "logo of the company," "audio of the bird call").

**Edge Cases - When NOT to Use**:
*   **For Textual Information**: Do not use this skill to answer factual, historical, or explanatory questions that are best answered with text. Use a `web_search` or similar text-retrieval skill instead.
*   **For YouTube Videos Exclusively**: If the request explicitly asks for "YouTube videos" or content known to be primarily hosted on YouTube, use a dedicated `youtube_search` skill if available.
*   **For Highly Abstract or Non-Visual Concepts**: Avoid using it for queries like "the meaning of life" or "theories of quantum gravity" which are unlikely to yield meaningful direct media results.
*   **When Internal Database Access is Needed**: This skill searches the public web. Do not use it to retrieve media from a private, internal database or a secured digital asset management system.

**Downstream Nodes**:
The retrieved media items are typically passed to:
1.  **Analysis Agents**: Skills that perform image description (`describe_image`), audio transcription, or deep media forensic analysis.
2.  **Synthesis/Reporting Agents**: Nodes that compile evidence into a report, presentation, or summary, embedding or referencing the sourced media.
3.  **Download/Processing Agents**: Skills tasked with physically downloading the media files for local processing, editing, or archiving.

## Constraints

*   **Platform Exclusion**: The search tool is explicitly configured to **filter out YouTube.com results**. It will not return links to YouTube videos. The Planner must never assume YouTube content will be retrieved by this skill.
*   **Source Credibility & Verification**: This skill retrieves URLs but does **not** perform deep authenticity verification, copyright clearance, or content safety analysis. The credibility score (0.65) reflects the inherent uncertainty of unvetted web sources. Downstream tasks requiring verified content must implement additional checks.
*   **No Content Generation or Hallucination**: The agent must only return media items found in the search results. It is strictly forbidden to invent or describe media that it did not actually locate. Output must be grounded in the retrieved data.
*   **Token & Result Limits**: The underlying tool may have inherent limits on the number of search results processed or the total descriptive text returned. The Planner should not expect exhaustive retrieval for extremely broad queries (e.g., "all pictures of cats").
*   **Scope Limitation**: The skill operates within the functionality of its provided `WebFetchTool`. It cannot interact with search APIs beyond its configuration, cannot bypass paywalls, and cannot access private or login-protected media repositories.
*   **Minimum Sources Requirement**: For the result to have an "OK" status, the skill must successfully retrieve and validate at least **2 distinct media source URLs**. The Planner should consider results with only one source as less reliable.

## Tools

- WebFetchTool with multimedia-specific filters

## Output Contract

RetrievalOutput — media items with media_type, source_url

**Credibility base**: 0.65

**Min sources for OK status**: 2