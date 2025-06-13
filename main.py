import nest_asyncio
nest_asyncio.apply()

import os
import re
import time
from typing import Optional
from agents import Agent, AsyncOpenAI, OpenAIChatCompletionsModel, Runner, function_tool
from agents import set_default_openai_api, set_default_openai_client, set_tracing_disabled
from dotenv import load_dotenv
import chainlit as cl
import google.auth
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import base64
from email.mime.text import MIMEText




load_dotenv()

# Gmail API setup
SCOPES = ['https://www.googleapis.com/auth/gmail.send', 'https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_service():
    """Get Gmail service with proper authentication."""
    creds = None
    # The file token.json stores the user's access and refresh tokens
    if os.path.exists('token.json'):
        creds = google.auth.load_credentials_from_file('token.json')[0]
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(google.auth.transport.requests.Request())
        else:
            # Load credentials from the credentials.json file
            if not os.path.exists('credentials.json'):
                raise FileNotFoundError(
                    "credentials.json not found. Please download it from Google Cloud Console "
                    "and place it in the project root directory."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    return build('gmail', 'v1', credentials=creds)

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

# Gmail API setup
SCOPES = ['https://www.googleapis.com/auth/gmail.send', 'https://www.googleapis.com/auth/gmail.readonly']
def get_gmail_service():
    creds = None
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)
    return build('gmail', 'v1', credentials=creds)

@function_tool
def send_email(to: str, subject: str, body: str) -> str:
    print(f"[DEBUG] Sending email to {to} with subject '{subject}'")
    service = get_gmail_service()
    message = MIMEText(body)
    message['to'] = to
    message['subject'] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    service.users().messages().send(userId='me', body={'raw': raw}).execute()
    return f"Email sent successfully to {to} with subject '{subject}'."

@function_tool
def read_emails(max_results: int = 5) -> str:
    print(f"[DEBUG] Reading up to {max_results} emails")
    service = get_gmail_service()
    results = service.users().messages().list(userId='me', maxResults=max_results).execute()
    messages = results.get('messages', [])
    if not messages:
        return "No emails found."
    
    email_summaries = []
    for message in messages:
        msg = service.users().messages().get(userId='me', id=message['id'], format='metadata').execute()
        headers = msg['payload']['headers']
        subject = next((header['value'] for header in headers if header['name'] == 'Subject'), 'No Subject')
        from_email = next((header['value'] for header in headers if header['name'] == 'From'), 'Unknown Sender')
        email_summaries.append(f"From: {from_email}, Subject: {subject}")
    return "\n".join(email_summaries)

# Create the email automation agent
agent = Agent(
    name="EmailAutomationAssistant",
    instructions="You are a helpful assistant that automates email tasks. You can send emails or read recent emails from the user's inbox. Use the send_email tool to send emails with a recipient, subject, and body. Use the read_emails tool to fetch recent emails (default 5). Parse user instructions to decide which tool to use.",
    model=model,
    tools=[send_email, read_emails]
)

@cl.on_message
async def main(message: cl.Message):
    user_input = message.content
    result = await Runner.run(agent, user_input)
    await cl.Message(content=result.final_output).send()

@cl.on_chat_start
async def on_chat_start():
    await cl.Message(content="Hello! I'm your email automation assistant. I can send emails or read your recent emails. Try saying 'Send an email to example@gmail.com' or 'Read my last 3 emails.'").send()

if __name__ == "__main__":
    import asyncio
    asyncio.run(cl.run())







# agent = Agent(
#     name="SimpleChatbot",
#     instructions="You are a helpful conversational assistant.",
#     model=model,
#     tools=[]
# )

# @cl.on_message
# async def main(message: cl.Message):
#     user_input = message.content
#     # Use Runner to run the agent
#     result = await Runner.run(agent, user_input)
#     # Send the agent's response back to the Chainlit UI
#     await cl.Message(content=result.final_output).send()

# @cl.on_chat_start
# async def on_chat_start():
#     await cl.Message(content="Hello! I'm your chatbot.").send()

# if __name__ == "__main__":
#     import asyncio
#     asyncio.run(cl.run())