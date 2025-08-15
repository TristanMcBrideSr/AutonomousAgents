
import os
from dotenv import load_dotenv

from HoloLink import ArgumentParser

from openai import OpenAI
from google import genai
from google.genai import types

argParser = ArgumentParser()
load_dotenv()
gptClient = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
genClient = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

def research(instructions: str):
    """
    Description: "Research a topic using web search capabilities."
    Additional Information: "This function uses web search capabilities to gather information on a given topic based on the provided instructions."
    """
    provider = os.getenv("PROVIDER", "openai")
    argParser.printArgs(__name__, locals())
    if provider == "openai":
        return _research_openai(instructions)
    elif provider == "google":
        return _research_google(instructions)
    else:
        raise ValueError(f"Unsupported provider: {provider}")

def _research_openai(instructions: str):
    return gptClient.responses.create(model="gpt-4.1-mini", tools=[{ "type": "web_search_preview" }], input=instructions).output_text

def _research_google(instructions: str):
    return genClient.models.generate_content(model="gemini-2.0-flash", contents=[types.Content(role="user", parts=[types.Part.from_text(text=instructions)])],
                config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())], response_mime_type="text/plain")).text

