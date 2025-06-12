import nest_asyncio
nest_asyncio.apply()

import os
from agents import Agent, AsyncOpenAI, OpenAIChatCompletionsModel, Runner
from agents import set_default_openai_api, set_default_openai_client, set_tracing_disabled
from dotenv import load_dotenv
import chainlit as cl

load_dotenv()

gemini_api_key = os.getenv("GEMINI_API_KEY")
if not gemini_api_key:
    raise ValueError("GEMINI_API_KEY is not set. Please set it in .env file at E:\\chatbot\\.env")

external_client = AsyncOpenAI(
    api_key=gemini_api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

model = OpenAIChatCompletionsModel(
    model="gemini-2.0-flash",
    openai_client=external_client
)

set_default_openai_client(client=external_client, use_for_tracing=False)
set_default_openai_api("chat_completions")
set_tracing_disabled(disabled=True)

agent = Agent(
    name="SimpleChatbot",
    instructions="You are a helpful conversational assistant.",
    model=model,
    tools=[]
)

@cl.on_message
async def main(message: cl.Message):
    user_input = message.content
    # Use Runner to run the agent
    result = await Runner.run(agent, user_input)
    # Send the agent's response back to the Chainlit UI
    await cl.Message(content=result.final_output).send()

@cl.on_chat_start
async def on_chat_start():
    await cl.Message(content="Hello! I'm your chatbot.").send()

if __name__ == "__main__":
    import asyncio
    asyncio.run(cl.run())