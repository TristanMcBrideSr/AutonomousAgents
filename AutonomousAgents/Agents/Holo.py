
from Utils.Config import *

CREATOR_NAME     = "Tristan McBride Sr."
AGENT_NAME       = "Holo Agent"

class MainAgent:
    def __init__(self):
        self.holoAI = HoloAI()
        self.agentTool = AgentTool()
        self.provider = os.getenv("PROVIDER", "openai")
        self.modelMap = {
            "openai": "gpt-4.1-mini",
            "google": "gemini-2.5-flash",
        }
        self.memories   = []

    def currentTime(self):
        return datetime.now().strftime("%I:%M %p")

    def currentDate(self):
        return datetime.now().strftime("%B %d, %Y")

    def addMemory(self, user, response, maxTurns=10):
        self.memories.append(f"user:{user}")
        self.memories.append(f"assistant:{response}")
        if len(self.memories) > maxTurns * 2:
            self.memories = self.memories[-maxTurns*2:]

    def configSystem(self, mainAgent) -> str:
        system = (f"You are a helpful AI agent named {mainAgent} created by {CREATOR_NAME}. You are designed to assist with various tasks\n"
                  "and provide information based on user queries. Your responses should be clear, concise, and informative.\n"
                  "You can also analyze images and provide insights based on their content.")
        instructions =  f"The current date and time is {self.currentDate()} {self.currentTime()}."
        return system, instructions

    def processInput(self, userGoal, verbose=False):
        mainAgent = AGENT_NAME # = MAIN_MINIONS[random.randint(0, len(MAIN_MINIONS) - 1)]
        system, instructions = self.configSystem(mainAgent)
        msgs = self.holoAI.formatConversation(self.memories, userGoal)
        skills = graph.getAgentSkills()
        actions = graph.getAgentActions()
        answer = self.holoAI.HoloAgent(
            model=self.modelMap[self.provider],
            system=system,
            instructions=instructions,
            input=msgs,
            skills=skills, 
            actions=actions
        )
        if answer:
            self.addMemory(userGoal, answer)
        print(f"\n[{mainAgent}]\n{answer}")
        return f"[{mainAgent}] {answer}\n"


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