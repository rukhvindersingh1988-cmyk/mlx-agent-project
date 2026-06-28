# Swarm Architecture Guide: Agent-to-Agent Negotiation

This guide provides a deep-dive into implementing Agent-to-Agent (A2A) negotiation architectures using three of the most prominent multi-agent frameworks: **LangGraph**, **AutoGen**, and **CrewAI**. 

While all three frameworks allow agents to communicate, their architectural approaches to negotiation differ significantly. A common thread across all production-grade implementations is the reliance on structured outputs (JSON/Pydantic schemas) to enforce a reliable "contract" or protocol between negotiating agents.

---

## 1. LangGraph: State-Driven Graph Architecture

LangGraph models agent interactions as a **stateful graph** (`StateGraph`). In this architecture, negotiation is handled by defining agents as nodes and the negotiation protocol (accept/reject/counter) as conditional edges that route execution based on a shared state.

### Architecture Concept
There is no single "JSON architecture file." Instead, the architecture is defined by the **State Schema** (often a `TypedDict` or Pydantic model) that is passed between nodes.

### The JSON Structure (State Schema)
The shared state acts as the "contract" between the agents. If serialized to JSON, the state at any point in the negotiation might look like this:

```json
{
  "messages": [
    {"role": "user", "content": "I want to buy the server for $100."},
    {"role": "assistant", "content": "{\"proposal\": {\"price\": 120, \"status\": \"counter\"}}"}
  ],
  "status": "in_progress",
  "proposal": {
    "price": 120,
    "terms": "Includes 1 year support",
    "status": "counter"
  },
  "turn_count": 2
}
```

### Implementation Example
Here is how you implement a negotiation loop in LangGraph using Pydantic structured outputs and conditional edges:

```python
from typing import TypedDict, Annotated, List, Literal
import operator
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END

# 1. Define the Structured Output (The JSON Protocol)
class ProposalSchema(BaseModel):
    price: float = Field(description="The proposed price")
    status: Literal["offer", "counter", "accept", "reject"]
    reasoning: str = Field(description="Why this decision was made")

# 2. Define the Shared State
class NegotiationState(TypedDict):
    messages: Annotated[List[dict], operator.add]
    latest_proposal: ProposalSchema
    turn_count: int

# 3. Define the Nodes
def buyer_agent(state: NegotiationState):
    # Logic to evaluate the latest_proposal and generate a new one
    # In practice, you would invoke an LLM here with `with_structured_output(ProposalSchema)`
    new_proposal = ProposalSchema(price=110, status="counter", reasoning="Too expensive.")
    return {
        "messages": [{"role": "buyer", "content": new_proposal.model_dump_json()}],
        "latest_proposal": new_proposal,
        "turn_count": state["turn_count"] + 1
    }

def seller_agent(state: NegotiationState):
    # LLM logic to evaluate the buyer's proposal
    new_proposal = ProposalSchema(price=110, status="accept", reasoning="Acceptable.")
    return {
        "messages": [{"role": "seller", "content": new_proposal.model_dump_json()}],
        "latest_proposal": new_proposal,
        "turn_count": state["turn_count"] + 1
    }

# 4. Define the Edge Logic
def check_negotiation_status(state: NegotiationState) -> Literal["buyer", "seller", "END"]:
    status = state["latest_proposal"].status
    if status in ["accept", "reject"] or state["turn_count"] >= 5:
        return "END"
    
    # Simple turn-taking logic
    last_speaker = state["messages"][-1]["role"]
    return "seller" if last_speaker == "buyer" else "buyer"

# 5. Build the Graph
builder = StateGraph(NegotiationState)
builder.add_node("buyer", buyer_agent)
builder.add_node("seller", seller_agent)

builder.add_conditional_edges("buyer", check_negotiation_status, {"seller": "seller", "END": END})
builder.add_conditional_edges("seller", check_negotiation_status, {"buyer": "buyer", "END": END})
builder.set_entry_point("buyer")

graph = builder.compile()
```

---

## 2. AutoGen: Conversational Orchestration

AutoGen does not use a rigid API pipeline; it treats negotiation as a **multi-turn conversation** between autonomous agents (e.g., `AssistantAgent`). The architecture is defined by the setup of the `GroupChat` or two-agent chat, and the system prompts given to each agent.

### Architecture Concept
Agents "negotiate" by exchanging messages. To make this programmatic rather than just a wall of text, developers enforce **JSON Mode** or **Structured Outputs** within the conversation.

### The JSON Structure (Message Payload)
In AutoGen, the actual message passed from one agent to another during negotiation should follow a strict JSON schema:

```json
{
  "sender": "SellerAgent",
  "message_type": "negotiation_offer",
  "content": {
    "status": "COUNTER",
    "proposed_price": 120.00,
    "currency": "USD",
    "justification": "Market rates for this service have increased."
  },
  "metadata": {
    "round": 3
  }
}
```

### Implementation Example
AutoGen relies on defining the "mindset" (System Prompt) and ensuring the agents output parseable JSON.

```python
import autogen
from pydantic import BaseModel
import json

llm_config = {"model": "gpt-4-turbo", "api_key": "YOUR_API_KEY"}

# 1. Define the Agents
buyer = autogen.AssistantAgent(
    name="BuyerAgent",
    system_message="""You are a buyer. You have a maximum budget of $150. 
    You must ONLY respond with a JSON object matching this schema:
    {"price": float, "status": "offer"|"counter"|"accept"|"reject", "reason": "str"}""",
    llm_config=llm_config,
)

seller = autogen.AssistantAgent(
    name="SellerAgent",
    system_message="""You are a seller. Your floor price is $100. 
    You must ONLY respond with a JSON object matching this schema:
    {"price": float, "status": "offer"|"counter"|"accept"|"reject", "reason": "str"}""",
    llm_config=llm_config,
)

# 2. Define Termination Condition based on JSON output
def is_termination_msg(content):
    if not content: return False
    try:
        data = json.loads(content.get("content", "{}"))
        return data.get("status") in ["accept", "reject"]
    except:
        return False

user_proxy = autogen.UserProxyAgent(
    name="UserProxy",
    human_input_mode="NEVER",
    is_termination_msg=is_termination_msg,
    max_consecutive_auto_reply=10
)

# 3. Initiate Negotiation
user_proxy.initiate_chat(
    seller,
    message=json.dumps({"price": 90, "status": "offer", "reason": "Initial lowball offer."})
)
```

---

## 3. CrewAI: Task Delegation & Hierarchical Orchestration

CrewAI approaches negotiation differently, relying primarily on **Task Delegation** and **Hierarchical Processes**. Instead of a peer-to-peer chat, a `Manager` agent often orchestrates the negotiation by assigning tasks to different agents until a consensus is reached. 

For cross-system negotiation, CrewAI also features an **A2A Protocol** (HTTP+JSON).

### Architecture Concept
You configure agents and tasks in `YAML` or `JSONC` files. The negotiation is handled by defining an `expected_output` (Pydantic model) for the negotiation tasks, ensuring the data returned to the Manager is structured.

### The JSON Structure (Agent/Task Definition & Output)
CrewAI allows defining agents in a configuration file (often `agents.jsonc` or `agents.yaml`):

```jsonc
// agents.jsonc
{
  "buyer_agent": {
    "role": "Procurement Lead",
    "goal": "Secure the lowest possible price under $150.",
    "backstory": "Experienced negotiator...",
    "allow_delegation": false
  }
}
```

The structured output of a negotiation task:
```json
{
  "final_agreed_price": 115.00,
  "terms_accepted": true,
  "parties_involved": ["buyer_agent", "seller_agent"]
}
```

### Implementation Example
Using CrewAI's hierarchical process with Pydantic for structured negotiation results.

```python
from crewai import Agent, Task, Crew, Process
from pydantic import BaseModel, Field

# 1. Define the Pydantic Model for the Contract
class NegotiationResult(BaseModel):
    agreed_price: float = Field(description="The final agreed price")
    terms: str = Field(description="The terms of the agreement")
    status: str = Field(description="'success' or 'failed'")

# 2. Define the Agents
buyer = Agent(
    role='Buyer',
    goal='Negotiate the best price for the software below $100.',
    backstory='You are stingy and always push for discounts.',
    verbose=True
)

seller = Agent(
    role='Seller',
    goal='Sell the software for at least $120.',
    backstory='You are a premium seller, you don\'t like dropping prices.',
    verbose=True
)

manager = Agent(
    role='Negotiation Manager',
    goal='Facilitate the negotiation between the buyer and seller and output the final agreement.',
    backstory='You act as the mediator.',
    verbose=True
)

# 3. Define the Negotiation Task
negotiation_task = Task(
    description='Facilitate a negotiation for a software license. The buyer wants it under $100, the seller wants over $120. Have them debate until an agreement is reached or negotiations break down.',
    expected_output='A structured JSON object detailing the final agreement.',
    output_pydantic=NegotiationResult,
    agent=manager # The manager handles the orchestration
)

# 4. Assemble the Crew
crew = Crew(
    agents=[buyer, seller],
    tasks=[negotiation_task],
    process=Process.hierarchical,
    manager_agent=manager
)

# Start the negotiation
result = crew.kickoff()
print(result.json())
```

## Summary of Best Practices for A2A Negotiation
1. **Never rely on raw text:** Agents will hallucinate or change formats. Always use **Pydantic** models or `with_structured_output` to force agents to negotiate using a strict JSON schema.
2. **Prevent Infinite Loops:** Always include a `turn_count` or `max_consecutive_auto_reply` counter. Two stubborn LLMs can negotiate endlessly.
3. **Clear State:** Define a "Status" field (`offer`, `counter`, `accept`, `reject`) in your JSON schema so the orchestration layer knows exactly when to terminate the loop.
