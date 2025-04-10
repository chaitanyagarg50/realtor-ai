from typing import Dict, Any
from langchain_core.messages import AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import json
from langchain_core.pydantic_v1 import BaseModel
from src.util.state import State

load_dotenv()

# Create a ChatOpenAI instance
model = ChatOpenAI(model="gpt-4o-mini")

class SearchCriteriaObject(BaseModel):
    city: str | None = None
    state: str | None = None
    min_bedroom: int | None = None
    min_bathroom: int | None = None
    max_price: float | None = None
    min_price: float | None = None

# Use JSON mode for structured output
structured_llm = model.with_structured_output(SearchCriteriaObject, method="json_mode")

SYSTEM_MESSAGE = """
You are an AI assistant for a real estate search application. Your task is to interpret user queries about property searches and generate a JSON object representing the search criteria. The criteria should follow this structure:

{
    "city": Optional[str],
    "state": Optional[str],
    "min_bedroom": Optional[int],
    "min_bathroom": Optional[int],
    "max_price": Optional[float],
    "min_price": Optional[float]
}

Guidelines:
1. If the user's query indicates a new search (e.g., asking about a different location), create a new search criteria object, discarding any previous criteria.
2. If the query is a follow-up or modification to a previous search, update the existing criteria by adding new information or modifying existing fields.
3. Use singular forms for 'bedroom' and 'bathroom' in the JSON output.
4. For bedroom and bathroom counts, use the 'min_' prefix to indicate "at least" this many.
5. Infer the state if a well-known city is mentioned (e.g., "New York" implies "New York" state).
6. If a price range is mentioned, use 'min_price' and 'max_price' accordingly.
7. Only include fields in the JSON that are explicitly mentioned or can be reasonably inferred from the user's query.
8. The entire response should be a valid JSON object matching the SearchCriteriaObject structure.

Respond with only the JSON object, no additional text.
"""

def search_criteria_agent(state: State) -> Dict[str, Any]:
    last_tool_call = state["messages"][-1].tool_calls[0]
    tool_call_id = last_tool_call["id"]
    user_query = last_tool_call["args"]["request"]

    current_criteria = state.get("search_criteria", {})
    messages = [
        {"role": "system", "content": SYSTEM_MESSAGE},
        {"role": "user", "content": f"Current Criteria: {json.dumps(current_criteria, indent=2)}"},
        {"role": "user", "content": f"User Query: {user_query}"},
    ]

    try:
        response = structured_llm.invoke(messages)
        new_search_criteria = response.dict(exclude_none=True)
    except Exception as e:
        return {
            "search_criteria": current_criteria,
            "messages": [
                ToolMessage(content="Entering search criteria agent", tool_call_id=tool_call_id),
                AIMessage(content=f"Failed to parse search criteria. Error: {e}"),
            ],
        }

    response_message = "I've updated your search criteria based on your request. Here's what I understood:\n"
    for key, value in new_search_criteria.items():
        if value is not None:
            response_message += f"- {key.replace('_', ' ').capitalize()}: {value}\n"

    return {
        "search_criteria": new_search_criteria,
        "messages": [
            ToolMessage(content="Entering search criteria agent.", tool_call_id=tool_call_id),
            AIMessage(content=response_message),
        ],
    }