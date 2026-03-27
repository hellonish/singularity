# video_search

**Tier**: retrieval  
**Name**: `video_search`  

## Description

The `video_search` skill is a specialized retrieval agent designed to locate relevant YouTube video content and extract its textual transcript for downstream analysis. It physically performs a two-stage process: first, it executes a targeted web search to discover YouTube videos matching a query, and second, it programmatically accesses and parses the transcript data from the identified video URLs.

The cognitive process begins with query formulation. The agent interprets the user's information need and constructs a precise search string, typically appending `site:youtube.com` to restrict results to the YouTube domain. It then uses a WebFetchTool (configured with DuckDuckGo) to retrieve a list of video results, including metadata such as title, URL, channel name, and video duration.

Upon obtaining video URLs, the agent initiates the core data transformation. It iterates through the result list, invoking the YouTubeTranscriptTool for each viable video. This tool makes an HTTP request to YouTube's transcript endpoint or uses a dedicated API/library to fetch available subtitle tracks. The raw transcript text—a time-coded sequence of dialogue or narration—is extracted, cleaned, and concatenated into a contiguous block of plain text.

The final output assembly involves synthesizing the retrieved metadata with the extracted text. For each successfully processed video, the agent creates a structured object containing the channel name, video duration, and a `transcript_excerpt`. This excerpt is typically the first 500-800 characters of the transcript, serving as a representative sample for the Planner to assess relevance. The agent filters out any videos where the transcript is unavailable, private, or in a non-retrievable format, ensuring only content with analyzable text is forwarded.

## When to Use

Use this skill in scenarios where the information need is best answered by spoken content, presentations, or visual demonstrations that are hosted on YouTube. It is particularly effective for:

*   **Conference Talks & Academic Lectures:** Retrieving cutting-edge research presentations, keynote speeches, or panel discussions from channels like TED, university channels, or conference archives (e.g., NeurIPS, Google Developers).
*   **Technical Tutorials & How-To Guides:** Finding step-by-step instructional content on software development, hardware projects, or creative skills.
*   **Expert Interviews & Documentary Evidence:** Sourcing firsthand accounts, expert analysis, or investigative journalism presented in video format.
*   **Verifying Claims or Quotes:** When a claim is attributed to a spoken statement in a public video, this skill can retrieve the exact transcript for verification.
*   **Gathering Diverse Perspectives:** Collecting video transcripts from multiple creators on a debated topic to analyze differing viewpoints.

**Upstream Dependencies & Expected Input:**
This skill is typically invoked by the Planner with a specific, well-formed search query. The ideal input is a clear information objective (e.g., "Find videos explaining quantum entanglement for beginners" or "Search for the 2023 Apple WWDC keynote announcements"). It expects the query to be sufficiently narrow to yield relevant YouTube content but broad enough to return multiple results. It does not require pre-processed text; it operates on the raw query.

**Edge Cases - When NOT to Use:**
*   **For Static Text or Code Retrieval:** Do not use this skill to find written articles, documentation, or code repositories. Use `web_search` or `github_search` instead.
*   **When Audio/Visual Analysis is Required:** This skill extracts only the transcript text. It cannot analyze visual frames, audio tones, background music, or speaker emotions. For that, a dedicated video/audio analysis skill is needed.
*   **For Highly Time-Sensitive News:** YouTube transcripts for very recent events (within hours) may not be available or auto-generated, leading to retrieval failure.
*   **If the Query is About YouTube's Platform Mechanics:** For questions about YouTube's algorithm, policies, or user statistics, a general web search is more appropriate.
*   **When the User Explicitly Requests "No Video Sources":** Respect user constraints on source media type.

**Downstream Nodes:**
The output of this skill is a `RetrievalOutput` containing structured video data. This output is typically fed into:
1.  **Analysis Agents (Tier 2 - Comprehension):** Skills like `summarize`, `analyze_sentiment`, or `extract_claims` that process the transcript text.
2.  **Synthesis Agents (Tier 3 - Planning):** Skills that compare information across multiple source types (e.g., comparing a video transcript to a blog post).
3.  **Answer Formulation:** The final answer agent that incorporates quotes or evidence from the video transcripts into a cohesive response.

## Tools

- WebFetchTool (site:youtube.com DuckDuckGo)
- YouTubeTranscriptTool

## Output Contract

RetrievalOutput — videos with channel, duration, transcript_excerpt

**Credibility base**: 0.65 general; 0.80 academic/conference channel

**Min sources for OK status**: 2

## Constraints

*   **Transcript Availability is Mandatory:** The skill must attempt to extract a transcript for every video. If a transcript is unavailable (e.g., disabled by uploader, auto-generated captions not ready, video is music-only), that video must be **skipped entirely** and not included in the output count. Do not return video entries without a `transcript_excerpt`.
*   **Source Minimum for Viability:** The skill must retrieve and successfully process transcripts from **at least 2 distinct videos** to achieve an "OK" status. If only one or zero videos yield transcripts, the output status should reflect a partial or failed retrieval.
*   **Avoid Hallucination of Content:** Under no circumstances should the agent infer, guess, or generate simulated transcript text. If the transcript tool returns an error or empty result, the video is invalid. The agent must not paraphrase the video title or description as if it were the transcript.
*   **Limit Scope to Transcript Extraction:** The agent's role is retrieval and text extraction only. It must not begin analyzing, summarizing, or interpreting the content of the transcripts. That is the role of downstream comprehension skills.
*   **Query Focus:** The web search must remain tightly focused on the provided query. Do not append unrelated exploratory terms or shift the search to find "similar" but off-topic videos.
*   **Result Limit:** Be judicious in the number of initial search results fetched (e.g., 5-8) to manage processing time, as each requires a subsequent transcript fetch attempt. Prioritize results from the first search page.
*   **Credibility Application:** Apply the credibility score accurately based on the publishing channel. Academic institutions, recognized conference series, and established educational channels should receive the 0.80 base. General creator channels, vlogs, and unverified accounts receive the 0.65 base. Do not arbitrarily inflate credibility scores.