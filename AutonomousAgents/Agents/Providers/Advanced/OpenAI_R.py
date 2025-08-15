import os
import json
import random
from dotenv import load_dotenv
from openai import OpenAI

from Utils.ToolSchemas import SkillGraph
from HoloAI import HoloRelay

load_dotenv()

gptClient = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SCHEMA_TYPE = "responses"
ROUNDS = 10

# --- load once, reuse everywhere ---
skillGraph = SkillGraph()
tools, toolFunctions = skillGraph.getJsonTools(SCHEMA_TYPE)

def executeTool(*args, **kwargs):
    return skillGraph.executeTool(*args, **kwargs)


class AgentMessageBus:
    def __init__(self):
        self.ata = HoloRelay()

    def send(self, fromAgent, toAgent, content):
        self.ata.send(fromAgent, toAgent, content)

    def receive(self, agentName, allowedFrom=None):
        return self.ata.receive(agentName, allowedFrom)


class LlmTool:
    def __init__(self, model="gpt-4.1"):
        self.model = model

    def run(self, prompt):
        if isinstance(prompt, str):
            messages = [
                skillGraph.handleJsonFormat("system", "You are a helpful assistant."),
                skillGraph.handleJsonFormat("user", prompt)
            ]
        else:
            messages = prompt
        response = gptClient.responses.create(
            model=self.model,
            input=messages
        )
        return response.output_text.strip()

    def runFunction(self, messages, schemas):
        response = gptClient.responses.create(
            model=self.model,
            input=messages,
            tools=schemas,
        )
        return response


class SubAgent:
    def __init__(self, step, agentName, bus, subagentTasks=None):
        self.step          = step
        self.agentName     = agentName
        self.bus           = bus
        self.toolFunctions = toolFunctions
        self.schemas       = tools
        self.result        = None
        self.completed     = False
        self.state         = {}
        self.subagentTasks = subagentTasks or {}

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
        llm = LlmTool()
        prompt = (
            f"Your current task is:\n{myTask}\n"
            f"Here are the tasks of your fellow agents:\n" +
            "\n".join(otherTasks) +
            "\n\nList the NAMES of any agents whose task you need to see before completing your own. "
            "Only respond with a comma-separated list of agent names. If none, respond with NONE."
        )
        answer = llm.run(prompt)
        names  = [n.strip() for n in answer.split(",") if n.strip() and n.strip().upper() != "NONE"]
        return names

    def askForHelp(self):
        needed = self.needsDataFrom()
        for agentName in needed:
            self.sendMessage(agentName, f"Can you help me with your result for {self.subagentTasks[agentName]['tool']}?")

    def maybeDelegate(self):
        if self.subagentTasks and len(self.subagentTasks) > 1 and random.random() < 0.5:
            others = [name for name in self.subagentTasks if name != self.agentName]
            if others:
                chosen = random.choice(others)
                self.sendMessage(chosen, f"Please do this task for me: {self.step}")
                self.completed = True
                self.result = f"Delegated to {chosen}"
                return True
        return False

    def runStep(self, verbose=False):
        if not self.completed and not self.maybeDelegate():
            llm = LlmTool()
            messages = [
                skillGraph.handleJsonFormat("system", "You are a sub-agent. Complete the assigned step using ONLY the available tools."),
                skillGraph.handleJsonFormat("user", f"Step: {self.step}")
            ]
            response = llm.runFunction(messages, self.schemas)

            functionCalls = []
            functionOutputs = []
            for toolCall in response.output:
                if toolCall.type != "function_call":
                    continue

                functionCalls.append({
                    "type": "function_call",
                    "call_id": toolCall.call_id,
                    "name": toolCall.name,
                    "arguments": toolCall.arguments
                })

                name = toolCall.name
                args = json.loads(toolCall.arguments)
                result = executeTool(name, self.toolFunctions, args)

                functionOutputs.append({
                    "type": "function_call_output",
                    "call_id": toolCall.call_id,
                    "output": str(result)
                })

            messages.extend(functionCalls)
            messages.extend(functionOutputs)
            response2 = llm.runFunction(messages, self.schemas)

            self.result = response2.output_text.strip()
            self.completed = True
            self.sendMessage(None, f"Done with: {self.step}")
            if verbose:
                print(f"\n[{self.agentName}] Completed: {self.step} = {self.result}")

    def processMessages(self, verbose=False):
        newMessages = self.receiveMessages()
        for m in newMessages:
            if verbose:
                print(f"\n[{self.agentName}] Message from {m['from']}: {m['content']}")
            if "Please do this task" in m['content']:
                import ast
                try:
                    delegatedStep = ast.literal_eval(m['content'].split("Please do this task for me:", 1)[-1].strip())
                    toolName = delegatedStep['tool']
                    args = delegatedStep.get('args', {})
                    self.result = executeTool(toolName, self.toolFunctions, args)
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
        self.toolFunctions = toolFunctions
        self.toolSchemas   = tools
        self.bus           = HoloRelay()

    def decomposeSteps(self, userGoal):
        # FIXED: Adjusted for Responses API schema format
        toolList = [
            {
                "name": t["name"],
                "signature": {
                    "description": t.get("description", ""),
                    "parameters": t.get("parameters", {})
                }
            }
            for t in self.toolSchemas
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
        results = []
        subagentTasks = {f"SubAgent-{i+1}": step for i, step in enumerate(steps)}
        subagents = []
        for i, step in enumerate(steps, 1):
            agentName = f"SubAgent-{i}"
            subagent = SubAgent(step, agentName, self.bus, subagentTasks)
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
