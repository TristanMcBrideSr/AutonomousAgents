import random
import os
from dotenv import load_dotenv
from datetime import datetime
from Utils.Names import MAIN_MINIONS, SUB_MINIONS
from Utils.SkillGraph import SkillGraph
# from HoloAI import HoloRelay

# from openai import OpenAI
# from google import genai
# from google.genai import types

from HoloAI import (HoloAI, HoloRelay)

load_dotenv()
# gptClient = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
# genClient = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Set These Environment Variables in your .env file or system environment variables
# PROVIDER=openai or google (default is openai)
# OPENAI_API_KEY=your_openai_api_key
# GEMINI_API_KEY=your_google_api_key
##-------------------------------------- NOTE --------------------------------------
# HoloAI supports OpenAI, Google, xAI, Anthropic, Groq.
# Make sure to add your api keys for the Provider(s) in the .env file or set them in your environment variables that you want to use.
# Add Provider models to the modelMap in AgentTool class.

graph = SkillGraph()
skillInstructions = graph.skillInstructions()
ROUNDS = 10


class AgentTool:
    def __init__(self):
        self.holoAI = HoloAI()
        self.provider = os.getenv("PROVIDER", "openai")
        self.modelMap = {
            "openai": "gpt-4.1-mini",
            "google": "gemini-2.5-flash",
        }

    def run(self, systemMsg, userMsg):
        try:
            return self.holoAI.Agent(
                task='response',
                model=self.modelMap[self.provider],
                system=systemMsg,
                input=userMsg
            )
        except KeyError:
            raise ValueError("Invalid LLM provider. Use 'openai' or 'google'.")


class AgentMessageBus:
    def __init__(self):
        self.holoRelay = HoloRelay()

    def send(self, fromAgent, toAgent, content):
        self.holoRelay.send(fromAgent, toAgent, content)

    def receive(self, agentName, allowedFrom=None):
        return self.holoRelay.receive(agentName, allowedFrom)


# class AgentTool:
#     def __init__(self):
#         self.holoai = HoloAI()
#         self.provider    = os.getenv("PROVIDER", "openai")
#         self.providerMap = {
#             "openai": self.runOpenai,
#             "google": self.runGoogle,
#         }

#     def run(self, systemMsg, userMsg):
#         try:
#             return self.providerMap[self.provider](systemMsg, userMsg)
#         except KeyError:
#             raise ValueError("Invalid LLM provider. Use 'openai' or 'google'.")

#     def runOpenai(self, systemMsg, userMsg):
#         # prompt = [
#         #     graph.handleJsonFormat("system", systemMsg),
#         #     graph.handleJsonFormat("user", userMsg)
#         # ]
#         # return gptClient.chat.completions.create(
#         #     model="gpt-4.1-mini",
#         #     messages=prompt,
#         # ).choices[0].message.content
#         return self.holoai.Response(
#             model="gpt-4.1-mini",
#             system=systemMsg,
#             input=userMsg,
#         )

#     def runGoogle(self, systemMsg, userMsg):
#         # system = [graph.handleTypedFormat("system", systemMsg)]
#         # model = "gemini-2.5-flash"
#         # contents = []
#         # contents.append(graph.handleTypedFormat("user", userMsg))

#         # generateContentConfig = types.GenerateContentConfig(
#         #     response_mime_type="text/plain",
#         #     system_instruction=system,
#         # )
#         # return genClient.models.generate_content(
#         #     model=model,
#         #     contents=contents,
#         #     config=generateContentConfig,
#         # ).text
#         return self.holoai.Response(
#             model="gemini-2.5-flash",
#             system=systemMsg,
#             input=userMsg,
#         )
