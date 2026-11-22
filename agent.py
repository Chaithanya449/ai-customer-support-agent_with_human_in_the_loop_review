"""LangGraph customer support agent powered by Groq."""

import os
import sqlite3
import uuid
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from tools import tools


load_dotenv()

llm_with_tools = None

SYSTEM_PROMPT = """You are a friendly, concise customer support agent for a generic e-commerce store.

You can look up orders, explain the return policy, submit return requests, submit refund requests for human review, and check refund request status.

Guidelines:
- Returns may be requested within 7 days of delivery.
- Ask for the numeric order ID when it is missing. Use check_order_status for order questions.
- Use the order lookup results to identify item IDs and ordered quantities. Never invent IDs.
- For a return, make sure the customer has identified the item, quantity, and reason. Use lookup_return_policy to provide valid reason IDs when needed.
- Before submitting a return, summarize the item, quantity, and reason and ask the customer to confirm. Call process_return_request only after they confirm.
- Report the tool result accurately. A created request has status "requested"; it is not an approved return or completed refund.
- If the tool declines a request, explain the reason it returned. Do not claim a refund was issued.
- Refund requests require human review. Use request_refund only when the customer asks to request a refund, and explain that it is pending review.
- Use check_refund_status when the customer asks about a refund or return decision.
- Do not assume a company name or product category. Be polite and keep responses brief.
"""


def assistant(state: MessagesState) -> dict:
    """Respond to the customer, optionally requesting a tool call."""
    global llm_with_tools
    if llm_with_tools is None:
        if not os.getenv("GROQ_API_KEY"):
            raise RuntimeError("GROQ_API_KEY is missing. Add it to the project .env file.")
        from langchain_groq import ChatGroq

        llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0)
        llm_with_tools = llm.bind_tools(tools)
    messages = [SystemMessage(content=SYSTEM_PROMPT), *state["messages"]]
    return {"messages": [llm_with_tools.invoke(messages)]}


builder = StateGraph(MessagesState)
builder.add_node("assistant", assistant)
builder.add_node("tools", ToolNode(tools))
builder.add_edge(START, "assistant")
builder.add_conditional_edges("assistant", tools_condition)
builder.add_conditional_edges("tools", tools_condition)

def build_graph(checkpointer=None):
    """Compile the support workflow, optionally with a checkpointer."""
    return builder.compile(checkpointer=checkpointer)


CHECKPOINT_DB_PATH = str(Path(__file__).resolve().parent / "checkpoints.db")
SESSION_THREAD_ID = str(uuid.uuid4())
checkpoint_connection = sqlite3.connect(
    CHECKPOINT_DB_PATH, check_same_thread=False
)
checkpointer = SqliteSaver(checkpoint_connection)
checkpointer.setup()
graph = build_graph(checkpointer)


def chat(user_message: str, thread_id: str = SESSION_THREAD_ID) -> str:
    """Send a message and resume the conversation with a complete reply."""
    config = {"configurable": {"thread_id": thread_id}}
    payload = {"messages": [HumanMessage(content=user_message)]}
    result = graph.invoke(payload, config)
    return str(result["messages"][-1].content)
if __name__ == "__main__":
    print("Customer support agent ready. Type 'quit' to exit.")
    while True:
        try:
            message = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if message.lower() in {"quit", "exit"}:
            break
        if not message:
            continue
        try:
            print(f"Agent: {chat(message)}")
        except Exception as error:
            if "rate" in str(error).lower() or "429" in str(error):
                print("Agent: The service is busy right now. Please try again shortly.")
            else:
                raise



