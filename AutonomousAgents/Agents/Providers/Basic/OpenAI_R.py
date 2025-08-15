import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from Utils.SkillGraph import SkillGraph

load_dotenv()

gptClient = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
SCHEMA_TYPE = "responses"

# Load tool schemas and functions together (Responses API format)
skillGraph = SkillGraph()
tools, toolFunctions = skillGraph.getJsonTools(SCHEMA_TYPE)

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
    def __init__(self, step):
        self.step          = step
        self.toolFunctions = toolFunctions
        self.schemas       = tools

    def run(self):
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

            name   = toolCall.name
            args   = json.loads(toolCall.arguments)
            result = skillGraph.executeTool(name, self.toolFunctions, args)

            functionOutputs.append({
                "type": "function_call_output",
                "call_id": toolCall.call_id,
                "output": str(result)
            })

        messages.extend(functionCalls)
        messages.extend(functionOutputs)

        response2 = llm.runFunction(messages, self.schemas)
        return response2.output_text.strip()

def runStepText(prompt):
    llm = LlmTool()
    return llm.run(prompt)
SubAgent.runStepText = runStepText

class OrchestratorAgent:
    def __init__(self):
        self.toolFunctions = toolFunctions
        self.toolSchemas   = tools

    def decomposeSteps(self, userGoal):
        toolList = [
            {
                "name": schema["name"],
                "signature": {
                    "description": schema.get("description", ""),
                    "parameters": schema.get("parameters", {})
                }
            }
            for schema in self.toolSchemas
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
        for i, step in enumerate(steps, 1):
            toolName = step['tool']
            args = step.get('args', {})
            if verbose:
                print(f"\n[Orchestrator] Creating SubAgent #{i}")
                print(f"  Step: {toolName}({args})")
            subagent = SubAgent(f"{toolName}({args})")
            result = subagent.run()
            results.append({
                "step": f"{toolName}({args})",
                "result": result
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
