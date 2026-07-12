import asyncio

from engine.chat.modal_tools import ModalToolExecutor
from engine.tools.contracts import ChatToolInvocation


class FakeModalFunction:
    def __init__(self) -> None:
        self.payload = None
        self.remote = self

    async def aio(self, payload):
        self.payload = payload
        return {"content": "result", "sources": [], "credibility_base": 0.8, "error": None}


def test_modal_executor_forwards_only_validated_tool_payload() -> None:
    function = FakeModalFunction()
    executor = ModalToolExecutor(function_lookup=lambda: function)
    invocation = ChatToolInvocation(
        run_id="run_1",
        skill_id="medical_research",
        tool_name="pubmed",
        query="trial",
        arguments={"max_results": 3},
        timeout_seconds=60,
    )

    result = asyncio.run(executor.execute(invocation))

    assert result.content == "result"
    assert function.payload == {
        "run_id": "run_1",
        "skill_id": "medical_research",
        "tool_name": "pubmed",
        "query": "trial",
        "arguments": {"max_results": 3},
        "effort": "medium",
        "timeout_seconds": 60,
        "profile_limits": {
            "max_agent_tool_steps": 4,
            "max_calls_per_tool_type": 2,
            "timeout_seconds": 60,
        },
    }
    assert "api_key" not in function.payload
    assert "groq" not in function.payload
