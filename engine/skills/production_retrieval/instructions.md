# Production retrieval

Invoke retrieval only from the authenticated API service. Derive user and resource scope from server-side identity and relational ownership checks. Never accept authorization filters from the model or request body. Fail closed when ownership metadata is missing and never expose this capability to the local ephemeral CLI.
