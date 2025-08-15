
from Utils.Config import *


class SubAgent:
    def __init__(self, task, agentName, messageBus):
        self.agentTool = AgentTool()
        self.task = task
        self.agentName = agentName
        self.bus = messageBus
        self.result = None
        self.state = {}
        self.completed = False
        self.subagentTasks = None
        self.delegatedTo = None

    def sendMessage(self, to, content):
        self.bus.send(self.agentName, to, content)

    def receiveMessages(self):
        return self.bus.receive(self.agentName)

    def needsDataFrom(self):
        if not self.subagentTasks or len(self.subagentTasks) <= 1:
            return []
        myTask = self.task
        otherTasks = [
            f"{name}: {task}"
            for name, task in self.subagentTasks.items() if name != self.agentName
        ]
        prompt = (
            f"Your current task is:\n{myTask}\n"
            f"Here are the tasks of your fellow agents:\n" +
            "\n".join(otherTasks) +
            "\n\nList the NAMES of any agents whose task you need to see before completing your own. "
            "Only respond with a comma-separated list of agent names. If none, respond with NONE."
        )
        answer = self.agentTool.run(
            "You are a helpful agent determining your dependencies.",
            prompt
        )
        names = [n.strip() for n in answer.split(",") if n.strip() and n.strip().upper() != "NONE"]
        return names

    def askForHelp(self):
        needed = self.needsDataFrom()
        for agentName in needed:
            self.sendMessage(agentName, f"Can you help me with your result for {self.subagentTasks[agentName]}?")

    def maybeDelegate(self):
        # Only allow delegation if there are at least 3 agents (prevents infinite loops on two)
        if self.subagentTasks and len(self.subagentTasks) > 2 and random.random() < 0.80:
            others = [name for name in self.subagentTasks if name != self.agentName]
            if others:
                chosen = random.choice(others)
                # Prevent delegating back and forth endlessly
                if self.delegatedTo == chosen:
                    return False
                self.delegatedTo = chosen
                self.sendMessage(chosen, f"Please do this task for me: {self.task}")
                self.completed = True
                self.result = f"Delegated to {chosen}"
                return True
        return False

    def runStep(self, verbose=False):
        if not self.completed and not self.maybeDelegate():
            clarified = self.agentTool.run(skillInstructions, self.task)
            if verbose:
                print(f"\n[{self.agentName}] Clarified action: {clarified}")
            actions = graph.getActions(clarified)
            allSkills = graph.getAgentActions()
            results = graph.executeActions(allSkills, actions)
            filtered = [str(r) for r in results if r]
            finalResult = "\n".join(filtered)
            if verbose:
                print(f"Executed actions, got:\n{finalResult}")
            self.result = finalResult or "No action result."
            self.completed = True
            self.sendMessage(None, f"Done with: {self.task}")

    def processMessages(self, verbose=False):
        newMessages = self.receiveMessages()
        for m in newMessages:
            if verbose:
                print(f"\n[{self.agentName}] Message from {m['from']}: {m['content']}")
            if "Please do this task" in m['content']:
                task = m['content'].split("Please do this task for me:", 1)[-1].strip()
                # Prevent circular delegation: If asked to do the task I delegated, just execute.
                if task == self.task:
                    clarified = self.agentTool.run(skillInstructions, task)
                    actions = graph.getActions(clarified)
                    allSkills = graph.getAgentActions()
                    results = graph.executeActions(allSkills, actions)
                    filtered = [str(r) for r in results if r]
                    finalResult = "\n".join(filtered)
                    reply = f"Did your delegated task: {task}\nResult: {finalResult or 'No action result.'}"
                    self.sendMessage(m['from'], reply)
                else:
                    # Actually delegate
                    clarified = self.agentTool.run(skillInstructions, task)
                    actions = graph.getActions(clarified)
                    allSkills = graph.getAgentActions()
                    results = graph.executeActions(allSkills, actions)
                    filtered = [str(r) for r in results if r]
                    finalResult = "\n".join(filtered)
                    reply = f"Did your delegated task: {task}\nResult: {finalResult or 'No action result.'}"
                    self.sendMessage(m['from'], reply)
            elif "Can you help" in m['content']:
                reply = f"\nSure, {m['from']}! Here's my result for {self.task}: {self.result or 'not ready yet!'}"
                self.sendMessage(m['from'], reply)
            elif "Here's" in m['content'] or "Done with" in m['content']:
                self.state[m['from']] = m['content']


class OrchestratorAgent:
    def __init__(self):
        self.agentTool = AgentTool()
        self.bus = HoloRelay()
        self.subagents = {}

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
        stepsText = self.agentTool.run("You are an expert orchestrator agent.", prompt)
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

        self.subagents = {}
        subagentTasks = {}
        for i, step in enumerate(steps, 1):
            subAgentName = SUB_MINIONS[(i - 1) % len(SUB_MINIONS)]
            self.subagents[subAgentName] = SubAgent(step, subAgentName, messageBus=self.bus)
            subagentTasks[subAgentName] = step

        for agent in self.subagents.values():
            agent.subagentTasks = subagentTasks

        if verbose:
            print(f"\n[{mainAgent}] === Calling sub-agents ===")

        for roundNum in range(ROUNDS):
            for agent in self.subagents.values():
                agent.processMessages(verbose=verbose)
            if roundNum == 0:
                for agent in self.subagents.values():
                    agent.runStep(verbose=verbose)
            if roundNum == 1:
                for agent in self.subagents.values():
                    agent.askForHelp()
            if roundNum >= 2:
                anyMessages = any(agent.receiveMessages() for agent in self.subagents.values())
                if not anyMessages and all(m.completed for m in self.subagents.values()):
                    break

        for agent in self.subagents.values():
            agent.processMessages(verbose=verbose)
            # Only set results to actual output, not delegated message
            agentResult = agent.result
            if agentResult and agentResult.startswith("Delegated to "):
                # Try to resolve the actual result from agent.state
                for val in agent.state.values():
                    if "Result:" in val:
                        agentResult = val.split("Result:")[-1].strip()
            results.append({"step": agent.task, "result": agentResult})

        return results


class MainAgent:
    def __init__(self):
        self.orchestrator = OrchestratorAgent()
        self.agentTool = AgentTool()

    def processInput(self, userGoal, verbose=False):
        def llm(prompt):
            return self.agentTool.run("You are a helpful assistant.", prompt)
        if verbose:
            print("\nProcessing user input...\n")
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
            f"You are a helpful assistant. Answer the user clearly and professionally.\n"
            f"User originally asked: \"{userGoal}\"\n"
            f"Here are the results for that request:\n{resultsSummary}\n"
            "Write your response now."
        )
        print(f"\n[{mainAgent}]\n{answer}")
        return f"[{mainAgent}] {answer}\n"

# # Usage:
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


#==================================================================================================================================
# ----------------- Use the code below if you want to skip the orchestration and just run the sub-agents directly -----------------
#==================================================================================================================================
# ------------------------------------------ SAVES TIME, RESOURCES AND MOST OF ALL MONEY ------------------------------------------
#==================================================================================================================================

# from Utils.Config import *


# class SubAgent:
#     def __init__(self, task, agentName, messageBus):
#         self.agentTool = AgentTool()
#         self.task = task
#         self.agentName = agentName
#         self.bus = messageBus
#         self.result = None
#         self.state = {}
#         self.completed = False
#         self.subagentTasks = None
#         self.delegatedTo = None

#     def sendMessage(self, to, content):
#         self.bus.send(self.agentName, to, content)

#     def receiveMessages(self):
#         return self.bus.receive(self.agentName)

#     def needsDataFrom(self):
#         if not self.subagentTasks or len(self.subagentTasks) <= 1:
#             return []
#         myTask = self.task
#         otherTasks = [
#             f"{name}: {task}"
#             for name, task in self.subagentTasks.items() if name != self.agentName
#         ]
#         prompt = (
#             f"Your current task is:\n{myTask}\n"
#             f"Here are the tasks of your fellow agents:\n" +
#             "\n".join(otherTasks) +
#             "\n\nList the NAMES of any agents whose task you need to see before completing your own. "
#             "Only respond with a comma-separated list of agent names. If none, respond with NONE."
#         )
#         answer = self.agentTool.run(
#             "You are a helpful agent determining your dependencies.",
#             prompt
#         )
#         names = [n.strip() for n in answer.split(",") if n.strip() and n.strip().upper() != "NONE"]
#         return names

#     def askForHelp(self):
#         needed = self.needsDataFrom()
#         for agentName in needed:
#             self.sendMessage(agentName, f"Can you help me with your result for {self.subagentTasks[agentName]}?")

#     def maybeDelegate(self):
#         # Only allow delegation if there are at least 3 agents (prevents infinite loops on two)
#         if self.subagentTasks and len(self.subagentTasks) > 2 and random.random() < 0.80:
#             others = [name for name in self.subagentTasks if name != self.agentName]
#             if others:
#                 chosen = random.choice(others)
#                 # Prevent delegating back and forth endlessly
#                 if self.delegatedTo == chosen:
#                     return False
#                 self.delegatedTo = chosen
#                 self.sendMessage(chosen, f"Please do this task for me: {self.task}")
#                 self.completed = True
#                 self.result = f"Delegated to {chosen}"
#                 return True
#         return False

#     def runStep(self, verbose=False):
#         if not self.completed and not self.maybeDelegate():
#             clarified = self.agentTool.run(skillInstructions, self.task)
#             if verbose:
#                 print(f"\n[{self.agentName}] Clarified action: {clarified}")
#             actions = graph.getActions(clarified)
#             allSkills = graph.getAgentActions()
#             results = graph.executeActions(allSkills, actions)
#             filtered = [str(r) for r in results if r]
#             finalResult = "\n".join(filtered)
#             if verbose:
#                 print(f"Executed actions, got:\n{finalResult}")
#             self.result = finalResult or "No action result."
#             self.completed = True
#             self.sendMessage(None, f"Done with: {self.task}")

#     def processMessages(self, verbose=False):
#         newMessages = self.receiveMessages()
#         for m in newMessages:
#             if verbose:
#                 print(f"\n[{self.agentName}] Message from {m['from']}: {m['content']}")
#             if "Please do this task" in m['content']:
#                 task = m['content'].split("Please do this task for me:", 1)[-1].strip()
#                 # Prevent circular delegation: If asked to do the task I delegated, just execute.
#                 if task == self.task:
#                     clarified = self.agentTool.run(skillInstructions, task)
#                     actions = graph.getActions(clarified)
#                     allSkills = graph.getAgentActions()
#                     results = graph.executeActions(allSkills, actions)
#                     filtered = [str(r) for r in results if r]
#                     finalResult = "\n".join(filtered)
#                     reply = f"Did your delegated task: {task}\nResult: {finalResult or 'No action result.'}"
#                     self.sendMessage(m['from'], reply)
#                 else:
#                     # Actually delegate
#                     clarified = self.agentTool.run(skillInstructions, task)
#                     actions = graph.getActions(clarified)
#                     allSkills = graph.getAgentActions()
#                     results = graph.executeActions(allSkills, actions)
#                     filtered = [str(r) for r in results if r]
#                     finalResult = "\n".join(filtered)
#                     reply = f"Did your delegated task: {task}\nResult: {finalResult or 'No action result.'}"
#                     self.sendMessage(m['from'], reply)
#             elif "Can you help" in m['content']:
#                 reply = f"\nSure, {m['from']}! Here's my result for {self.task}: {self.result or 'not ready yet!'}"
#                 self.sendMessage(m['from'], reply)
#             elif "Here's" in m['content'] or "Done with" in m['content']:
#                 self.state[m['from']] = m['content']


# class MainAgent:
#     def __init__(self):
#         self.agentTool = AgentTool()
#         self.bus = HoloRelay()
#         self.ROUNDS = ROUNDS

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
#         stepsText = self.agentTool.run("You are an expert orchestrator agent.", prompt)
#         steps = [line.lstrip("-1234567890. ").strip() for line in stepsText.splitlines() if line.strip()]
#         return steps

#     def processInput(self, userGoal, verbose=False):
#         def llm(prompt):
#             return self.agentTool.run("You are a helpful assistant.", prompt)
#         if verbose:
#             print("\nProcessing user input...\n")
#         prompt = (
#             "You are a helpful assistant. Restate the following user goal as a single clear task.\n"
#             f"User Goal: {userGoal}"
#         )
#         clarifiedGoal = llm(prompt)
#         mainAgent = MAIN_MINIONS[random.randint(0, len(MAIN_MINIONS) - 1)]
#         if verbose:
#             print(f"[{mainAgent}]: {clarifiedGoal}")

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

#         # == Start agentic message bus orchestration ==
#         subagents = {}
#         subagentTasks = {}
#         for i, step in enumerate(steps, 1):
#             subAgentName = SUB_MINIONS[(i - 1) % len(SUB_MINIONS)]
#             subagents[subAgentName] = SubAgent(step, subAgentName, messageBus=self.bus)
#             subagentTasks[subAgentName] = step

#         for agent in subagents.values():
#             agent.subagentTasks = subagentTasks

#         if verbose:
#             print(f"\n[{mainAgent}] === Calling sub-agents ===")

#         for roundNum in range(self.ROUNDS):
#             for agent in subagents.values():
#                 agent.processMessages(verbose=verbose)
#             if roundNum == 0:
#                 for agent in subagents.values():
#                     agent.runStep(verbose=verbose)
#             if roundNum == 1:
#                 for agent in subagents.values():
#                     agent.askForHelp()
#             if roundNum >= 2:
#                 anyMessages = any(agent.receiveMessages() for agent in subagents.values())
#                 if not anyMessages and all(m.completed for m in subagents.values()):
#                     break

#         for agent in subagents.values():
#             agent.processMessages(verbose=verbose)
#             agentResult = agent.result
#             if agentResult and agentResult.startswith("Delegated to "):
#                 for val in agent.state.values():
#                     if "Result:" in val:
#                         agentResult = val.split("Result:")[-1].strip()
#             results.append({"step": agent.task, "result": agentResult})

#         # == Summarize and answer ==
#         resultsSummary = "\n".join(
#             f"{r['step']}: {r['result']}" for r in results
#         )
#         answer = llm(
#             f"You are a helpful assistant. Answer the user clearly and professionally.\n"
#             f"User originally asked: \"{userGoal}\"\n"
#             f"Here are the results for that request:\n{resultsSummary}\n"
#             "Write your response now."
#         )
#         print(f"\n[{mainAgent}]\n{answer}")
#         return f"[{mainAgent}] {answer}\n"



# # Usage:
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


