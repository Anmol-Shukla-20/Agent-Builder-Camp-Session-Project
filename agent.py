import sys
import os
import asyncio
from google.adk import Agent
from google.adk.tools import FunctionTool
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Define the GitHub Card Agent - Optimized to ONLY handle analysis to save quota
github_card_agent = Agent(
    name="github_card_agent",
    model="gemini-flash-lite-latest", # Use lite model for higher quota and stability
    instruction="""You are a GitHub profile analyst. 
Your ONLY job is to analyze the provided GitHub data and return a JSON object with:
- developer_vibe: A 1-sentence personality description.
- top_skills: A list of exactly 3 technical skills.
- fun_fact: A clever observation inferred from their repositories.
- card_theme: The theme requested by the user, or 'white' if none specified.

You DO NOT call other tools. Just process the data and return JSON.""",
)
