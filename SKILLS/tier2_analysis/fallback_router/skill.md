# fallback_router

**Tier**: analysis  
**Name**: `fallback_router`  

## Description

Internal skill used by the orchestrator's FallbackRouter. Not called by the Planner.

## When to Use

Never planned explicitly. Used internally when primary skill fails.

## Execution Model

Orchestrator-internal

## Output Contract

Passes through result from the fallback skill.

## Constraints

- Do NOT include in plan nodes
