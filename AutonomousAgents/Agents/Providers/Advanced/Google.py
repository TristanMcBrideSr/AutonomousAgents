import os
import json
import random
from dotenv import load_dotenv
from google import genai
from google.genai import types

from Utils.SkillGraph import SkillGraph
from HoloAI import HoloRelay

load_dotenv()

apiKey    = os.getenv("GEMINI_API_KEY")
genClient = genai.Client(api_key=apiKey)

# Load typed tools + callable function registry once, reuse everywhere
skillGraph = SkillGraph()
tools, toolFunctions = skillGraph.getTypedTools()

ROUNDS = 10


class AgentMessageBus:
    def __init__(self):
        self.ata = HoloRelay()

    def send(self, fromAgent, toAgent, content):
        self.ata.send(fromAgent, toAgent, content)

    def receive(self, agentName, allowedFrom=None):
        return self.ata.receive(agentName, allowedFrom)


class LlmTool:
    def __init__(self, model="gemini-2.5-flash"):
        self.model = model

    def run(self, prompt):
        # Build typed "contents" with SkillGraph's formatter
        contents = [skillGraph.handleTypedFormat("user", prompt)]
        config = types.GenerateContentConfig(response_mime_type="text/plain")
        response = genClient.models.generate_content(
            model=self.model,
            contents=contents,
            config=config,
        )
        return response.text


def makeResponsePayload(funcName, result):
    if isinstance(result, dict):
        return result
    return {funcName: result}


class SubAgent:
    def __init__(self, step, agentName, bus, subagentTasks=None):
        self.step           = step
        self.agentName      = agentName
        self.bus            = bus
        self.toolFunctions  = toolFunctions   # shared registry
        self.agentTool      = LlmTool()
        self.result         = None
        self.state          = {}
        self.completed      = False
        self.subagentTasks  = subagentTasks or {}

    def sendMessage(self, to, content):
        self.bus.send(self.agentName, to, content)

    def receiveMessages(self):
        return self.bus.receive(self.agentName)

    def needsDataFrom(self):
        if not self.subagentTasks or len(self.subagentTasks) <= 1:
            return []
        myTask = self.step
        otherTasks = [
            f"{name}: {task['tool']}" for name, task in self.subagentTasks.items() if name != self.agentName
        ]
        prompt = (
            f"Your current task is:\n{myTask}\n"
            f"Here are the tasks of your fellow agents:\n" +
            "\n".join(otherTasks) +
            "\n\nList the NAMES of any agents whose task you need to see before completing your own. "
            "Only respond with a comma-separated list of agent names. If none, respond with NONE."
        )
        answer = self.agentTool.run(
            "You are a helpful agent determining your dependencies.\n\n" + prompt
        )
        names = [n.strip() for n in answer.split(",") if n.strip() and n.strip().upper() != "NONE"]
        return names

    def askForHelp(self):
        needed = self.needsDataFrom()
        for agentName in needed:
            self.sendMessage(agentName, f"Can you help me with your result for {self.subagentTasks[agentName]['tool']}?")

    def maybeDelegate(self):
        if self.subagentTasks and len(self.subagentTasks) > 1 and random.random() < 0.8:
            others = [name for name in self.subagentTasks if name != self.agentName]
            if others:
                chosen = random.choice(others)
                self.sendMessage(chosen, f"Please do this task for me: {self.step}")
                self.completed = True
                self.result    = f"Delegated to {chosen}"
                return True
        return False

    def runStep(self, verbose=False):
        if not self.completed and not self.maybeDelegate():
            toolName = self.step['tool']
            args     = self.step.get('args', {})
            # Execute directly via SkillGraph registry
            self.result    = skillGraph.executeTool(toolName, self.toolFunctions, args)
            self.completed = True
            self.sendMessage(None, f"Done with: {toolName}({args})")
            if verbose:
                print(f"\n[{self.agentName}] Completed: {toolName}({args}) = {self.result}")

    def processMessages(self, verbose=False):
        newMessages = self.receiveMessages()
        for m in newMessages:
            if verbose:
                print(f"\n[{self.agentName}] Message from {m['from']}: {m['content']}")
            if "Please do this task" in m['content']:
                import ast
                try:
                    delegatedStep = ast.literal_eval(m['content'].split("Please do this task for me:", 1)[-1].strip())
                    self.step     = delegatedStep
                    toolName      = delegatedStep['tool']
                    args          = delegatedStep.get('args', {})
                    self.result   = skillGraph.executeTool(toolName, self.toolFunctions, args)
                    self.completed = True
                    reply = f"Did your delegated task: {delegatedStep}\nResult: {self.result}"
                except Exception as e:
                    reply = f"Error running delegated task: {e}"
                    self.result = reply
                    self.completed = True
                self.sendMessage(m['from'], reply)
            elif "Can you help" in m['content']:
                reply = f"Sure, {m['from']}! Here's my result for {self.step['tool']}: {self.result or 'not ready yet!'}"
                self.sendMessage(m['from'], reply)
            elif "Here's" in m['content']:
                self.state[m['from']] = m['content']
            elif "Done with" in m['content']:
                self.state[m['from']] = m['content']


def runStepText(prompt):
    llm = LlmTool()
    return llm.run(prompt)


class OrchestratorAgent:
    def __init__(self):
        self.toolFunctions = toolFunctions   # shared registry
        self.bus           = HoloRelay()

    def decomposeSteps(self, userGoal):
        # For planning, expose concise tool info based on callable registry (docstrings)
        toolList = [
            {"name": name, "signature": (f.__doc__ or "")}
            for name, f in self.toolFunctions.items()
        ]
        prompt = (
            "Given the following tools:\n"
            f"{json.dumps(toolList, indent=2)}\n"
            "Break down this goal into the smallest possible sequence of function calls using ONLY these tools.\n"
            "For each step, provide a dict with 'tool' (tool name) and 'args' (args dict).\n"
            "Only output a valid JSON array of objects, nothing else. No markdown, no explanation.\n"
            f"Goal: {userGoal}"
        )
        planJson = runStepText(prompt)
        try:
            plan = skillGraph.extractJson(planJson)
        except Exception:
            print("Failed to parse plan:", planJson)
            raise
        return plan

    def run(self, userGoal, verbose=False):
        steps = self.decomposeSteps(userGoal)
        subagentTasks = {f"SubAgent-{i+1}": step for i, step in enumerate(steps)}
        subagents = []
        for i, step in enumerate(steps, 1):
            agentName = f"SubAgent-{i}"
            subagent  = SubAgent(step, agentName, self.bus, subagentTasks)
            subagents.append(subagent)

        for roundNum in range(ROUNDS):
            for agent in subagents:
                agent.processMessages(verbose=verbose)
            if roundNum == 0:
                for agent in subagents:
                    agent.runStep(verbose=verbose)
            if roundNum == 1:
                for agent in subagents:
                    agent.askForHelp()
            if roundNum >= 2:
                anyMessages = any(agent.receiveMessages() for agent in subagents)
                if not anyMessages and all(a.completed for a in subagents):
                    break

        results = []
        for agent in subagents:
            agent.processMessages(verbose=verbose)
            results.append({
                "step": f"{agent.step['tool']}({agent.step.get('args', {})})",
                "result": agent.result
            })
        return results


class MainAgent:
    def __init__(self):
        self.orchestrator = OrchestratorAgent()

    def processInput(self, userGoal, verbose=False):
        task = runStepText(
            "You are a helpful assistant that takes user goals and redefines it and passes it to the orchestrator agent.\n"
            f"User Goal: {userGoal}"
        )
        if verbose:
            print(f"\n[Orchestrator Task]: {task}\n")
        results = self.orchestrator.run(task, verbose)
        resultsSummary = "\n".join(
            f"{r['step']}: {r['result']}" for r in results
        )
        prompt = (
            f"User originally asked: \"{userGoal}\"\n"
            "Here are the tool results for that request:\n"
            f"{resultsSummary}\n"
            "Write a clear, natural language answer for the user that references the original request directly."
        )
        answer = runStepText(prompt)
        if verbose:
            print(f"\n[Final Response]:\n{answer}\n")
        else:
            print(f"{answer}\n")
        return answer

# if __name__ == "__main__":
#     mainAgent = MainAgent()
#     while True:
#         userGoal = input("\nEnter your goal (or 'exit' to quit): ").strip()
#         if userGoal.lower() == 'exit':
#             print("Exiting the agent.")
#             break
#         if not userGoal:
#             print("Please enter a valid goal.")
#             continue
#         mainAgent.processInput(userGoal, verbose=True)
