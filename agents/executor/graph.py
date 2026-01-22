"""
Executor Agent LangGraph Definition

A tool-using graph that executes steps from a plan.
"""

from typing import Any, TypedDict

from langgraph.graph import StateGraph, END

from runtime.agent_runner import AgentRunner, AgentOutput
from runtime.bedrock_client import BedrockClient, ModelConfig
from runtime.tool_registry import ToolRegistry, ToolMode, get_registry


class ExecutorState(TypedDict):
    """State for the executor graph."""
    plan: dict
    tools: list[dict] | None
    output: AgentOutput | None
    tool_calls: list[dict]
    error: str | None


def create_executor_graph(
    bedrock_client: BedrockClient | None = None,
    model_config: ModelConfig | None = None,
    tool_registry: ToolRegistry | None = None
) -> StateGraph:
    """
    Create the executor agent graph.

    Args:
        bedrock_client: Optional BedrockClient instance
        model_config: Optional model configuration
        tool_registry: Optional tool registry instance

    Returns:
        Compiled StateGraph for the executor agent
    """
    runner = AgentRunner(bedrock_client=bedrock_client)
    registry = tool_registry or get_registry(mode=ToolMode.STUB)

    def execute_node(state: ExecutorState) -> ExecutorState:
        """
        Main execution node that processes the plan.

        Args:
            state: Current graph state with plan

        Returns:
            Updated state with execution output
        """
        try:
            # Get tool schemas for the model
            tools = state.get("tools") or registry.get_tool_schemas()

            # Run the executor agent
            output = runner.run_agent(
                agent_name="executor",
                input_payload=state["plan"],
                tools=tools,
                model_config=model_config
            )

            # Get tool calls made during execution
            tool_calls = registry.get_call_log()

            return {
                **state,
                "output": output,
                "tool_calls": [
                    {
                        "tool_name": call.tool_name,
                        "arguments": call.arguments,
                        "result": call.result,
                        "mode": call.mode.value
                    }
                    for call in tool_calls
                ],
                "error": None
            }
        except Exception as e:
            return {
                **state,
                "output": None,
                "tool_calls": [],
                "error": str(e)
            }

    def should_continue(state: ExecutorState) -> str:
        """
        Determine if execution should continue or end.

        Args:
            state: Current graph state

        Returns:
            Next node name or END
        """
        # Check for errors
        if state.get("error"):
            return END

        # Check if output indicates completion
        output = state.get("output")
        if output and output.parsed_output:
            # Check if there's a refusal
            if output.is_refusal:
                return END

            # Check if all steps are complete
            results = output.parsed_output.get("results", [])
            if results:
                return END

        return END

    # Build the graph
    graph = StateGraph(ExecutorState)

    # Add the execution node
    graph.add_node("execute", execute_node)

    # Set entry point
    graph.set_entry_point("execute")

    # Add conditional edge
    graph.add_conditional_edges(
        "execute",
        should_continue,
        {END: END}
    )

    return graph.compile()


def run_executor(
    plan: dict,
    bedrock_client: BedrockClient | None = None,
    model_config: ModelConfig | None = None,
    tool_registry: ToolRegistry | None = None
) -> ExecutorState:
    """
    Convenience function to run the executor graph.

    Args:
        plan: The plan to execute (from planner output)
        bedrock_client: Optional BedrockClient instance
        model_config: Optional model configuration
        tool_registry: Optional tool registry instance

    Returns:
        Final state with execution output
    """
    registry = tool_registry or get_registry(mode=ToolMode.STUB)
    registry.clear_call_log()

    graph = create_executor_graph(bedrock_client, model_config, registry)
    initial_state: ExecutorState = {
        "plan": plan,
        "tools": None,
        "output": None,
        "tool_calls": [],
        "error": None
    }
    return graph.invoke(initial_state)
