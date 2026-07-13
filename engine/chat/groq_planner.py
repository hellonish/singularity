"""Groq tool-calling planner constrained to registered skill/tool pairs."""
from __future__ import annotations

from engine.chat.tool_loop import ExecutedToolCall, PlannedToolCall
from engine.chat.prompt import build_runtime_system_prompt
from engine.llm.config import LLMRequestConfig
from engine.llm.providers import LLMProvider
from engine.tools.contracts import chat_planner_tool_schemas


class GroqChatToolPlanner:
    def __init__(self, *, provider: LLMProvider, api_key: str, config: LLMRequestConfig) -> None:
        self._provider = provider
        self._api_key = api_key
        self._config = config
        self._schemas, self._bindings = chat_planner_tool_schemas()

    async def plan(
        self,
        *,
        query: str,
        context: str,
        prior_results: tuple[ExecutedToolCall, ...],
    ) -> PlannedToolCall | None:
        if not self._schemas:
            return None
        result_context = "\n\n".join(
            f"{item.skill_id}/{item.tool_name}: {item.result.content[:1200]}"
            for item in prior_results
        )
        tool_call = await self._provider.plan_tool_call(
            api_key=self._api_key,
            config=self._config,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"{build_runtime_system_prompt()}\n\n"
                        "Use a tool only when it materially improves the answer. "
                        "Each function name encodes its approved skill and tool."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Question:\n{query}\n\nLocal reference context:\n{context}\n\n"
                        f"Prior tool results:\n{result_context or '(none)'}"
                    ),
                },
            ],
            tools=self._schemas,
        )
        if tool_call is None:
            return None
        binding = self._bindings.get(tool_call.name)
        if binding is None:
            return None
        raw_query = tool_call.arguments.get("query")
        raw_arguments = tool_call.arguments.get("arguments")
        if not isinstance(raw_query, str) or not isinstance(raw_arguments, dict):
            return None
        return PlannedToolCall(
            skill_id=binding[0],
            tool_name=binding[1],
            query=raw_query,
            arguments=raw_arguments,
        )
