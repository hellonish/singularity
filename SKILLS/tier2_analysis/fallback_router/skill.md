# fallback_router

**Tier**: analysis  
**Name**: `fallback_router`  

## Description

The `fallback_router` is a critical, low-level orchestration mechanism that functions as the system's automatic failure recovery and contingency routing layer. It is not a conventional skill that performs data analysis or content generation. Instead, it acts as a dynamic, internal dispatcher that is invoked automatically by the Orchestrator's core logic when a primary, planned skill execution fails. Its sole purpose is to intercept execution errors, assess the failure context, and transparently reroute the task to a predefined, functionally equivalent fallback skill without disrupting the overall plan's data flow or requiring Planner intervention. The skill operates by receiving the original input arguments and the error context from the failed primary skill, selecting the appropriate backup skill from a configured mapping (e.g., `web_search` might fall back to `knowledge_base_search`), and executing it. It then passes the successful result back up the chain, making the failure and recovery process entirely opaque to downstream nodes and the final user. This ensures plan robustness and continuity.

## When to Use

- **Specific Scenarios**: This skill is **NEVER** to be explicitly planned, requested, or referenced as a node in any execution DAG built by the Planner LLM. Its activation is purely automatic and conditional.
- **Automatic Invocation Triggers**:
    1. **Primary Skill Failure**: When any skill node in the execution plan throws an execution error (e.g., tool API failure, timeout, unexpected output format).
    2. **Orchestrator Interception**: The Orchestrator's runtime engine catches the error and triggers the FallbackRouter logic, which then employs this skill.
- **Upstream Dependencies**: It expects the exact same input payload that was sent to the failed primary skill. This includes the original task arguments, context, and any state passed between nodes. It also receives metadata about the failure (error type, skill name) from the Orchestrator.
- **Edge Cases - When NOT to Use It**:
    - **DO NOT** use it as a primary tool for any user request.
    - **DO NOT** call it when a skill returns a valid but suboptimal or incorrect result (this is a logic error, not a runtime failure).
    - **DO NOT** use it if the primary skill's failure is due to invalid input that would also break the fallback skill (e.g., malformed query).
    - **DO NOT** invoke it for skills that have no configured fallback.
- **Downstream Nodes**: The downstream node(s) that were originally waiting on the output of the *primary skill* will receive the output from the *fallback skill* via this router, completely unaware of the switch. The execution DAG proceeds as if the primary skill had succeeded.

## Execution Model

Orchestrator-internal

## Output Contract

Passes through result from the fallback skill.

## Constraints

- **Absolute Planning Exclusion**: The Planner LLM must **NEVER** include `fallback_router` as a node in any execution plan or DAG. It is not a tool in the Planner's repertoire.
- **Internal Mechanism Only**: This skill's existence is documented for system understanding only. The Planner should operate under the assumption that skills will either succeed or fail outright; it should not design plans around fallback mechanisms.
- **No Direct Configuration**: The mapping of primary skills to their fallback counterparts is managed at the Orchestrator/FallbackRouter level and is not adjustable via skill arguments or Planner instructions.
- **Transparency Mandate**: The skill must not modify, annotate, or wrap the fallback skill's output in any way that reveals the recovery process. The output must be indistinguishable from a direct primary skill success.
- **Error Handling Scope**: It is only activated for runtime execution failures of a skill node. It is not used for plan validation errors, constraint violations, or failures in the Planner's own logic.