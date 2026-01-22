"""
Planner Agent LangGraph Definition

A single-node graph that takes a task and produces a structured plan.
"""

from typing import Any, TypedDict

from langgraph.graph import StateGraph, END

from runtime.agent_runner import AgentRunner, AgentOutput
from runtime.bedrock_client import BedrockClient, ModelConfig


class PlannerState(TypedDict):
    """State for the planner graph."""
    input_task: str
    output: AgentOutput | None
    error: str | None


def create_planner_graph(
    bedrock_client: BedrockClient | None = None,
    model_config: ModelConfig | None = None
) -> StateGraph:
    """
    Create the planner agent graph.

    Args:
        bedrock_client: Optional BedrockClient instance
        model_config: Optional model configuration

    Returns:
        Compiled StateGraph for the planner agent
    """
    runner = AgentRunner(bedrock_client=bedrock_client)

    def plan_node(state: PlannerState) -> PlannerState:
        """
        Main planning node that processes the input task.

        Args:
            state: Current graph state with input_task

        Returns:
            Updated state with planning output
        """
        try:
            output = runner.run_agent(
                agent_name="planner",
                input_payload=state["input_task"],
                model_config=model_config
            )
            return {
                **state,
                "output": output,
                "error": None
            }
        except Exception as e:
            return {
                **state,
                "output": None,
                "error": str(e)
            }

    # Build the graph
    graph = StateGraph(PlannerState)

    # Add the single planning node
    graph.add_node("plan", plan_node)

    # Set entry point
    graph.set_entry_point("plan")

    # Connect to end
    graph.add_edge("plan", END)

    return graph.compile()


def run_planner(
    task: str,
    bedrock_client: BedrockClient | None = None,
    model_config: ModelConfig | None = None
) -> PlannerState:
    """
    Convenience function to run the planner graph.

    Args:
        task: The task to plan
        bedrock_client: Optional BedrockClient instance
        model_config: Optional model configuration

    Returns:
        Final state with planning output
    """
    graph = create_planner_graph(bedrock_client, model_config)
    initial_state: PlannerState = {
        "input_task": task,
        "output": None,
        "error": None
    }
    return graph.invoke(initial_state)
