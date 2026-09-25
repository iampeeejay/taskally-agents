"""
Agent Forge — Base Agent Template
Build new agents by extending this or using it as a blueprint.
"""
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

load_dotenv()

class TaskAllyAgent:
    """Base class for all Task-ally AI agents."""
    
    def __init__(self, name: str, system_prompt: str, model: str = "openai/gpt-4o"):
        self.name = name
        self.system_prompt = system_prompt
        self.llm = ChatOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
            model=model,
        )
    
    def run(self, user_input: str) -> str:
        """Process user input and return agent response."""
        response = self.llm.invoke([
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=user_input),
        ])
        return response.content

    def chat(self):
        """Interactive chat loop."""
        print(f"\n{'='*50}")
        print(f"  {self.name} — Ready")
        print(f"{'='*50}")
        while True:
            user_input = input("\nYou: ").strip()
            if user_input.lower() in ("exit", "quit"):
                print(f"\n{self.name}: Goodbye!")
                break
            response = self.run(user_input)
            print(f"\n{self.name}: {response}")


if __name__ == "__main__":
    # Example: A simple customer support agent
    agent = TaskAllyAgent(
        name="Task-ally Support Agent",
        system_prompt="You are a helpful customer support agent for Task-ally Global Services. "
                      "Answer questions about our AI agent services, pricing, and capabilities."
    )
    agent.chat()