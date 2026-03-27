# code_search

**Tier**: retrieval  
**Name**: `code_search`  

## Description

The `code_search` skill is a specialized retrieval agent that performs targeted exploration of the GitHub ecosystem to discover software repositories relevant to a user's query. It physically executes a multi-step cognitive process: First, it formulates a search query based on the user's request, typically focusing on repository names, descriptions, and topics. It then interfaces with the GitHub API via the GitHubTool to fetch a list of matching repositories, prioritizing results by a relevance score determined by GitHub's search algorithm. For each top-result repository, the agent extracts a comprehensive set of metadata including the repository name, owner, primary programming language, license type, star count (a key popularity metric), and a brief description. Crucially, it then fetches the repository's primary README file (or a common alternative like README.md) and processes it to create a concise, informative excerpt. This excerpt is intelligently truncated to capture the project's purpose, key features, and installation or usage notes without exceeding practical token limits for downstream processing. The final output is a structured list of these enriched repository objects, transformed from raw API data into a standardized format suitable for analysis and synthesis by subsequent skills in the agent's execution graph.

## When to Use

Use this skill in the following specific scenarios:
*   **Identifying Software Libraries & Frameworks**: When the user asks "What Python libraries exist for machine learning model deployment?" or "Find a React component library for data visualization."
*   **Researching Implementation Patterns & Examples**: When the task is to "Find example repositories showing how to implement OAuth2 with FastAPI" or "Search for codebases that use the repository pattern in Go."
*   **Investigating Technical Stacks & Tools**: For queries like "What tools are used for monitoring microservices?" or "Show me popular projects built with Rust and WebAssembly."
*   **Evaluating Open-Source Project Viability**: When the user needs to assess project activity, as in "Find active repositories related to quantum computing algorithms," where star count and recent commits (implied) are indicators.
*   **Precursor to Deeper Code Analysis**: As an upstream dependency for skills like `code_analyzer` or `code_summarizer`. This skill provides the target repository list and context that those skills need to operate.

**Upstream Dependencies & Expected Input**: This skill is typically a primary retrieval node. It expects a clear, text-based query from the Planner that describes a software concept, tool, library, or pattern. The query should be specific enough to generate meaningful GitHub search results (e.g., "machine learning model deployment" is better than just "deployment").

**When NOT to Use (Edge Cases)**:
*   **For General Web Search**: Do not use for finding non-code information, news articles, or documentation hosted outside of GitHub (e.g., "latest news about React 19").
*   **For Code Snippet Search Within Files**: This skill searches at the repository metadata level, not within individual source code files. For searching specific functions or code snippets *inside* files, a different skill (e.g., a dedicated code-snippet search) is required.
*   **When the Query is Vague or Non-Technical**: Avoid using for queries like "how to learn programming" or "what is AI," which are conceptual and not directly tied to software repositories.
*   **For Private or Internal Repositories**: This skill is configured for public GitHub search. It cannot access private repositories without explicit, scoped credentials which are not typically provided in the standard tool setup.

**Downstream Nodes**: The output of this skill is designed to feed into:
1.  **Synthesis Agents** (e.g., `synthesize_retrieved`): To combine findings from multiple repositories into a coherent summary or comparison.
2.  **Code Analysis Agents**: To provide specific repository targets for deeper technical examination.
3.  **Decision/Recommendation Agents**: To use the curated list (filtered by stars, language, license) to make a tooling recommendation.

## Tools

- GitHubTool (PyGithub; GITHUB_TOKEN optional for higher rate limit)

## Output Contract

RetrievalOutput — repos with stars, language, license, readme_excerpt

**Credibility base**: 0.70 base; up to 0.90 based on star count

**Min sources for OK status**: 2

## Constraints

*   **Search Scope Limitation**: The skill is confined to searching GitHub's public repositories. It cannot search GitLab, Bitbucket, or other source code platforms unless explicitly redirected via a different tool.
*   **Credibility Calculation**: The credibility score for each source is strictly governed by the formula: `credibility = min(0.70 + (stars / 1000) * 0.20, 0.90)`. A repository with 0 stars has a credibility of 0.70. The Planner must not assign or imply credibility outside this calculated range.
*   **Minimum Source Requirement**: The skill's output status is only considered `OK` if it retrieves and processes at least **2** distinct qualifying repositories. A result with only 1 repository should trigger a status indicating insufficient data.
*   **README Processing Limit**: The agent must create a *brief excerpt* from the README, not return the entire document. This is to prevent token overflow in the context window of downstream LLM nodes. The excerpt should focus on the project overview and key points, typically limited to the first 300-500 characters of meaningful content.
*   **Avoid Hallucination of Details**: The agent must only return data explicitly provided by the GitHub API and the README content. It must not infer or generate details about code quality, performance, or security that are not stated in the retrieved text.
*   **Rate Limit Awareness**: While a GITHUB_TOKEN improves limits, the agent's logic should be efficient and avoid unnecessary API calls that could lead to rate-limiting, especially in automated or chain execution scenarios.