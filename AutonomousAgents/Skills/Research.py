
import inspect
import logging
import os
import threading
from dotenv import load_dotenv
from openai import OpenAI
from google import genai
from google.genai import types
from HoloLink import HoloLink

logger = logging.getLogger(__name__)



load_dotenv()

class Research:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(Research, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        if hasattr(self, 'initialized'):
            return
        self._initComponents()
        self.initialized = True

    def _initComponents(self):
        self.holoLink = HoloLink()
        self.provider  = os.getenv("PROVIDER", "openai")
        self.gptClient = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.genClient = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.actionMap = {
            "research": self._research
        }

    def researchSkill(self, action: str, *args):
        """
        Description: "Research a topic using web search capabilities."
        Additional Information: "Uses web search capabilities to gather information on a given topic based on the provided instructions."
        """
        self.holoLink.calledActions(self, locals())
        name = inspect.currentframe().f_code.co_name
        return self.holoLink.executeSkill('system', name, self.actionMap, action, *args)

    def _research(self, instructions: str):
        if self.provider == "openai":
            return self._research_openai(instructions)
        elif self.provider == "google":
            return self._research_google(instructions)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def _research_openai(self, instructions: str):
        return self.gptClient.responses.create(
            model="gpt-4.1-mini",
            tools=[{"type": "web_search_preview"}],
            input=instructions
        ).output_text

    def _research_google(self, instructions: str):
        return self.genClient.models.generate_content(
            model="gemini-2.0-flash",
            contents=[types.Content(role="user", parts=[types.Part.from_text(text=instructions)])],
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                response_mime_type="text/plain"
            )
        ).text
