
from Utils.Config import *

class SubAgent:
    def __init__(self, task, agentName):
        self.agentTool = AgentTool()
        self.task      = task
        self.agentName = agentName

    def run(self, verbose=False):
        clarified = self.agentTool.run(skillInstructions, self.task)
        if verbose:
            print(f"[{self.agentName}] Clarified action: {clarified}")
        actions = graph.getActions(clarified)
        allSkills = graph.getAgentActions()
        results = graph.executeActions(allSkills, actions)
        filtered = [str(r) for r in results if r]
        finalResult = "\n".join(filtered)
        if verbose:
            print(f"Executed actions, got:\n{finalResult}")
        return finalResult or "No action result."

class OrchestratorAgent:
    def __init__(self):
        self.agentTool = AgentTool()

    def decomposeSteps(self, userGoal):
        availableActions = graph.getAgentActions()
        prompt = (
            "Given the following available actions:\n"
            f"{', '.join(availableActions)}\n"
            "If the goal can be answered directly without calling any of these actions, say 'NO ACTIONS NEEDED'.\n"
            "Otherwise, break down the goal into the MINIMUM number of direct function calls, each matching exactly one of the available actions. "
            "If an action can't be matched directly, SKIP that step. "
            "Do NOT include high-level or abstract instructions. "
            "Just output a bullet list, one per function call, e.g.:\n"
            "- get_temperature(47.6588, -117.4260)\n"
            f"Goal: {userGoal}"
        )
        stepsText = self.agentTool.run("You are an expert orchestrator assistant.", prompt)
        steps = [line.lstrip("-1234567890. ").strip() for line in stepsText.splitlines() if line.strip()]
        return steps

    def run(self, mainAgent, userGoal, verbose=False):
        steps = self.decomposeSteps(userGoal)
        results = []
        stepsClean = [s.lower().strip() for s in steps]
        if not steps or any("no action" in s for s in stepsClean):
            if verbose:
                print(f"\n[{mainAgent}] No sub-agents needed! Answering directly.")
            answer = self.agentTool.run(
                "You are a helpful assistant who answers questions directly if no tools/actions are required.",
                f"Answer this question: \"{userGoal}\""
            )
            return [{"step": "direct_answer", "result": answer}]
        for i, step in enumerate(steps, 1):
            subAgentName = SUB_MINIONS[(i - 1) % len(SUB_MINIONS)]
            if verbose:
                print(f"\n[{mainAgent}] Executing sub-agent\n[{subAgentName}] for task: {step}")
            subAgent = SubAgent(step, subAgentName)
            result = subAgent.run(verbose=verbose)
            results.append({"step": step, "result": result})
        return results

class MainAgent:
    def __init__(self):
        self.orchestrator = OrchestratorAgent()
        self.agentTool    = AgentTool()

    def processInput(self, userGoal, verbose=False):
        def llm(prompt):
            return self.agentTool.run("You are a helpful assistant.", prompt)
        if verbose:
            print(f"\nProcessing request...\n")
        prompt = (
            "You are a helpful assistant. Restate the following user goal as a single clear task.\n"
            f"User Goal: {userGoal}"
        )
        clarifiedGoal = llm(prompt)
        mainAgent = MAIN_MINIONS[random.randint(0, len(MAIN_MINIONS) - 1)]
        if verbose:
            print(f"[{mainAgent}]: {clarifiedGoal}")
        results = self.orchestrator.run(mainAgent, clarifiedGoal, verbose=verbose)
        resultsSummary = "\n".join(
            f"{r['step']}: {r['result']}" for r in results
        )
        answer = llm(
            f"You are a helpful assistant. Please answer the user clearly and professionally.\n"
            f"User originally asked: \"{userGoal}\"\n"
            f"Here are the results for that request:\n{resultsSummary}\n"
            "Write your response now."
        )
        print(f"\n[{mainAgent}]\n{answer}")
        return f"[{mainAgent}] {answer}\n"

# # Usage:
# if __name__ == "__main__":
#     # use a while loop to keep the agent running
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


#==================================================================================================================================
# ----------------- Use the code below if you want to skip the orchestration and just run the sub-agents directly -----------------
#==================================================================================================================================
# ------------------------------------------ SAVES TIME, RESOURCES AND MOST OF ALL MONEY ------------------------------------------
#==================================================================================================================================

# from Utils.Config import *


# class SubAgent:
#     def __init__(self, task, agentName):
#         self.agentTool = AgentTool()
#         self.task      = task
#         self.agentName = agentName

#     def run(self, verbose=False):
#         clarified = self.agentTool.run(skillInstructions, self.task)
#         if verbose:
#             print(f"[{self.agentName}] Clarified action: {clarified}")
#         actions = graph.getActions(clarified)
#         allSkills = graph.getAgentActions()
#         results = graph.executeActions(allSkills, actions)
#         filtered = [str(r) for r in results if r]
#         finalResult = "\n".join(filtered)
#         if verbose:
#             print(f"Executed actions, got:\n{finalResult}")
#         return finalResult or "No action result."

# class MainAgent:
#     def __init__(self):
#         self.agentTool = AgentTool()

#     def decomposeSteps(self, userGoal):
#         availableActions = graph.getAgentActions()
#         prompt = (
#             "Given the following available actions:\n"
#             f"{', '.join(availableActions)}\n"
#             "If the goal can be answered directly without calling any of these actions, say 'NO ACTIONS NEEDED'.\n"
#             "Otherwise, break down the goal into the MINIMUM number of direct function calls, each matching exactly one of the available actions. "
#             "If an action can't be matched directly, SKIP that step. "
#             "Do NOT include high-level or abstract instructions. "
#             "Just output a bullet list, one per function call, e.g.:\n"
#             "- get_temperature(47.6588, -117.4260)\n"
#             f"Goal: {userGoal}"
#         )
#         stepsText = self.agentTool.run("You are an expert orchestrator assistant.", prompt)
#         steps = [line.lstrip("-1234567890. ").strip() for line in stepsText.splitlines() if line.strip()]
#         return steps

#     def processInput(self, userGoal, verbose=False):
#         def llm(prompt):
#             return self.agentTool.run("You are a helpful assistant.", prompt)
#         if verbose:
#             print(f"\nProcessing request...\n")
#         prompt = (
#             "You are a helpful assistant. Restate the following user goal as a single clear task.\n"
#             f"User Goal: {userGoal}"
#         )
#         clarifiedGoal = llm(prompt)
#         mainAgent = MAIN_MINIONS[random.randint(0, len(MAIN_MINIONS) - 1)]
#         if verbose:
#             print(f"[{mainAgent}]: {clarifiedGoal}")

#         # Orchestration inlined here
#         steps = self.decomposeSteps(clarifiedGoal)
#         results = []
#         stepsClean = [s.lower().strip() for s in steps]
#         if not steps or any("no action" in s for s in stepsClean):
#             if verbose:
#                 print(f"\n[{mainAgent}] No sub-agents needed! Answering directly.")
#             answer = self.agentTool.run(
#                 "You are a helpful assistant who answers questions directly if no tools/actions are required.",
#                 f"Answer this question: \"{userGoal}\""
#             )
#             print(f"\n[{mainAgent}]\n{answer}")
#             return f"[{mainAgent}] {answer}\n"
#         for i, step in enumerate(steps, 1):
#             subAgentName = SUB_MINIONS[(i - 1) % len(SUB_MINIONS)]
#             if verbose:
#                 print(f"\n[{mainAgent}] Executing sub-agent\n[{subAgentName}] for task: {step}")
#             subAgent = SubAgent(step, subAgentName)
#             result = subAgent.run(verbose=verbose)
#             results.append({"step": step, "result": result})
#         resultsSummary = "\n".join(
#             f"{r['step']}: {r['result']}" for r in results
#         )
#         answer = llm(
#             f"You are a helpful assistant. Please answer the user clearly and professionally.\n"
#             f"User originally asked: \"{userGoal}\"\n"
#             f"Here are the results for that request:\n{resultsSummary}\n"
#             "Write your response now."
#         )
#         print(f"\n[{mainAgent}]\n{answer}")
#         return f"[{mainAgent}] {answer}\n"


# # # Usage:
# if __name__ == "__main__":
#     # use a while loop to keep the agent running
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

