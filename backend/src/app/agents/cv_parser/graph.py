from functools import partial

from langchain_core.language_models import BaseChatModel
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agents.cv_parser.nodes import extract_structured, extract_text
from app.agents.cv_parser.state import CVParserState


def build_graph(llm: BaseChatModel) -> CompiledStateGraph[CVParserState]:
    graph = StateGraph(CVParserState)

    graph.add_node(
        "extract_text",
        extract_text,
    )

    graph.add_node(
        "extract_structured",
        partial(extract_structured, llm=llm),
    )

    graph.add_edge(START, "extract_text")
    graph.add_edge("extract_text", "extract_structured")
    graph.add_edge("extract_structured", END)

    return graph.compile()
