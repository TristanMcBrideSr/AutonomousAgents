
import json
import re
import inspect
import os
import threading
import logging
from dotenv import load_dotenv
from pathlib import Path
from google.genai import types
from HoloAI import HoloLink

load_dotenv()

logger = logging.getLogger(__name__)


class SkillGraph:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(SkillGraph, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if getattr(self, 'initialized', False):
            return
        self._initComponents()
        self.initialized = True

    def _initComponents(self):
        self.holoLink         = HoloLink()
        self.baseSkillsDir    = self.getDir('Skills')
        self.showCapabilities = os.getenv('SHOW_CAPABILITIES', 'False') == 'True'
        self.showMetaData     = os.getenv('SHOW_METADATA', 'False') == 'True'
        self.loadAllComponents()
        if self.showCapabilities:
            self.getAgentCapabilities()
        if self.showMetaData:
            self.getMetaData()

    def getDir(self, *paths):
        return self.holoLink.getDir(*paths)

    def loadAllComponents(self):
        """
        Load all components from the specified directories.
        This method loads skills and tools from the 'Skills' directory.
        It also loads custom tools for the agent.
        """
        self.agentSkills = []
        self.agentTools  = []

        self.holoLink.loadComponents(
            paths=[
                ['Skills'],
                ['Tools']
            ],
            components=[
                self.agentSkills,
                self.agentTools
            ],
            reloadable=[
                False,
                False,
            ]
        )

    def getAgentActions(self):
        """
        Get self actions based on the skills available.
        This method combines dynamic, static, and restricted self skills.
        """
        skills = (
            self.agentSkills
        )
        return self.holoLink.getComponents(skills)

    def reloadSkills(self):
        """
        Reload all skills and print any new skills added.
        """
        original = self.getMetaData()
        self.holoLink.reloadSkills()
        new = self.getMetaData()
        for skill in new:
            if skill not in original:
                print(f"I've added the new skill {skill['className']} That {skill['description']}.\n")

    def getMetaData(self):
        """Get metadata for all skills."""
        metaData = (
                self.agentSkills
        )
        return self.holoLink.getMetaData(metaData, self.showMetaData)

    # ----- Skills -----
    def getAgentCapabilities(self):
        """
        Get the capabilities of the agent based on its skills.
        This method retrieves the capabilities of the agent's skills and returns them in a structured format.
        """
        description = False
        capabitites = (
            self.agentSkills
        )
        return self.holoLink.getCapabilities(capabitites, self.showCapabilities, description)

    def checkActions(self, action: str) -> str:
        """
        Check if the given action is valid based on the agent's skills.
        Returns a string indicating whether the action is valid or not.
        """
        return self.holoLink.actionParser.checkActions(action)

    def getActions(self, action: str) -> list:
        """
        Get a list of actions based on the given action string.
        This method uses the skills manager's action parser to retrieve actions that match the given string.
        If the action is not found, it returns an empty list.
        """
        return self.holoLink.actionParser.getActions(action)

    def executeAction(self, actions, action):
        """
        Execute a single action based on the provided actions and action string.
        You must create your own for loop if you want to execute multiple actions.
        """
        return self.holoLink.actionParser.executeAction(actions, action)

    def executeActions(self, actions, action):
        """
        Execute both single and multiple actions based on the provided actions and action string.
        The for loop is handled internally, so you can pass a single action or a list of actions.
        """
        return self.holoLink.actionParser.executeActions(actions, action)

    def skillInstructions(self):
        """
        Get skill instructions for the agent based on its capabilities.
        """
        return self.holoLink.skillInstructions(self.getAgentCapabilities())


    # ----- Tools -----
    def executeTool(self, name, tools, args, threshold=80, retry=True):
        """
        Execute a tool with the given name, tools, and arguments.
        If the tool is not found, it will return an error message.
        If the tool execution fails, it will retry based on the retry parameter.
        """
        return self.holoLink.actionParser.executeTool(name, tools, args, threshold, retry)

    def getTools(self):
        """
        Get all tools available for the agent.
        """
        tools = (
            self.agentTools
        )
        return self.holoLink.getTools(tools)

    def extractJson(self, text):
        """
        Extract the first JSON array or object from a string, even if wrapped in markdown or extra commentary.
        """
        return self.holoLink.extractJson(text)

    def getJsonSchema(self, func, schemaType):
        """
        Build a json schema for a function based on its signature and docstring metadata.
        The schemaType can be either 'chat_completions' or 'responses'.
        Compatible with the OpenAI API and similar services that use JSON schemas.
        Returns a dictionary representing the schema.
        """
        return self.holoLink.getJsonSchema(func, schemaType)

    def getTypedSchema(self, func):
        """
        Build a typed schema for a function based on its signature and docstring metadata.
        Compatible with the Google API.
        Returns a dictionary representing the schema.
        """
        return self.holoLink.getTypedSchema(func)

    
    def getJsonTools(self, schemaType="responses"):
        """
        Get all tools available for the agent in a JSON schema format.
        This method retrieves the tools and converts them to a format compatible with OpenAI APIs.
        The schemaType can be either 'chat_completions' or 'responses'.
        Returns a dictionary representing the tools in JSON schema format.
        """
        toolList = self.getTools()
        return self.holoLink.getJsonTools(toolList, schemaType)

    def getTypedTools(self):
        """
        Get all tools available for the agent in a typed format.
        This method retrieves the tools and converts them to a format compatible with Google GenAI APIs.
        Returns a dictionary representing the tools in typed format.
        """
        toolList = self.getTools()
        return self.holoLink.getTypedTools(toolList)


    # ----- Can be used with both skills and tools -----
    def isStructured(self, *args):
        """
        Check if any of the arguments is a list of dictionaries.
        This indicates structured input (multi-message format).
        """
        return self.holoLink.isStructured(*args)

    def handleTypedFormat(self, role: str = "user", content: str = ""):
        """
        Format content for Google GenAI APIs.
        """
        return self.holoLink.handleTypedFormat(role, content)

    def handleJsonFormat(self, role: str = "user", content: str = ""):
        """
        Format content for OpenAI APIs and similar JSON-based APIs.
        """
        return self.holoLink.handleJsonFormat(role, content)

    def formatTypedExamples(self, items):
        """
        Handle roles for Google GenAI APIs, converting items to Gemini Content/Part types.
        Accepts a list of (role, value) tuples, where value can be:
            - str: will be wrapped using handleTypedFormat
            - dict: wrapped as Content with role, value as text
            - list of dicts: each dict converted to Content with role, dict as text
        Returns a flat list of Content objects.
        """
        return self.holoLink.formatTypedExamples(items)

    def formatJsonExamples(self, items):
        """
        Handle roles for OpenAI APIs, converting items to JSON message format.
        Accepts a list of (role, value) tuples, where value can be:
            - str: will be wrapped using handleJsonFormat
            - dict: added as-is
            - list of dicts: each dict is added individually
        Returns a flat list of message dicts.
        """
        return self.holoLink.formatJsonExamples(items)

    def formatExamples(self, items, formatFunc):
        """
        Ultra-robust handler for message formatting.
        Accepts string, dict, list of any mix, any nested depth.
        Silently ignores None. Converts numbers and bools to strings.
        """
        return self.holoLink.formatExamples(items, formatFunc)

    def handleTypedExamples(self, items):
        """
        Handle roles for Google GenAI APIs, converting items to Gemini Content/Part types.
        Accepts a list of (role, value) tuples, where value can be:
            - str: will be wrapped using handleTypedFormat
            - dict: wrapped as Content with role, value as text
            - list of dicts: each dict converted to Content with role, dict as text
        Returns a flat list of Content objects.
        """
        return self.holoLink.handleTypedExamples(items)

    def handleJsonExamples(self, items):
        """
        Handle roles for OpenAI APIs, converting items to JSON message format.
        Accepts a list of (role, value) tuples, where value can be:
            - str: will be wrapped using handleJsonFormat
            - dict: added as-is
            - list of dicts: each dict is added individually
        Returns a flat list of message dicts.
        """
        return self.holoLink.handleJsonExamples(items)

    def handleExamples(self, items, formatFunc):
        """
        Ultra-robust handler for message formatting.
        Accepts string, dict, list of any mix, any nested depth.
        Silently ignores None. Converts numbers and bools to strings.
        """
        return self.holoLink.handleExamples(items, formatFunc)

    def buildGoogleSafetySettings(self, harassment="BLOCK_NONE", hateSpeech="BLOCK_NONE", sexuallyExplicit="BLOCK_NONE", dangerousContent="BLOCK_NONE"):
        """
        Construct a list of Google GenAI SafetySetting objects.
        """
        return self.holoLink.buildGoogleSafetySettings(harassment, hateSpeech, sexuallyExplicit, dangerousContent)

