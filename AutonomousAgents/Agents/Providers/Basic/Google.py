import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types

from Utils.SkillGraph import SkillGraph

# Load environment
load_dotenv()
apiKey = os.getenv("GOOGLE_API_KEY")
genClient = genai.Client(api_key=apiKey)

# Load tools + callable functions from SkillGraph
skillGraph = SkillGraph()
tools, toolFunctions = skillGraph.getTypedTools()

class LlmTool:
    def __init__(self, model="gemini-2.5-flash"):
        self.model = model

    def run(self, prompt):
        contents = [skillGraph.handleTypedFormat("user", prompt)]
        config = types.GenerateContentConfig(response_mime_type="text/plain")
        response = genClient.models.generate_content(
            model=self.model,
            contents=contents,
            config=config,
        )
        return response.text


def runStepText(prompt):
    return LlmTool().run(prompt)


class SubAgent:
    def __init__(self, step):
        self.step = step
        self.toolFunctions = toolFunctions  # shared registry

    def run(self):
        toolName = self.step['tool']
        args = self.step.get('args', {})
        return skillGraph.executeTool(toolName, self.toolFunctions, args)


class OrchestratorAgent:
    def __init__(self):
        self.toolFunctions = toolFunctions

    def decomposeSteps(self, userGoal):
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
        results = []
        for i, step in enumerate(steps, 1):
            if verbose:
                print(f"\n[Orchestrator] Creating SubAgent #{i}")
                print(f"  Step: {step['tool']}({step.get('args', {})})")
            subagent = SubAgent(step)
            result = subagent.run()
            results.append({
                "step": f"{step['tool']}({step.get('args', {})})",
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
