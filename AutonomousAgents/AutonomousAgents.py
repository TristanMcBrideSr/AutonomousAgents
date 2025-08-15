
import logging
import importlib
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.WARNING,
    format="[%(asctime)s] [%(levelname)s] [%(threadName)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

VERBOSE = os.getenv("VERBOSE", "False")

CHOICE_MAP = {
    1: "Basic Agent",
    2: "Advanced Agent",
}

PROCESS_MAP = {
    "Basic Agent":    ("Agents.Basic",    "processInput"),
    "Advanced Agent": ("Agents.Advanced", "processInput"),
}

def selectAgent():
    print("\nAutonomous Agent Demo System\n" + "-" * 30)
    print("Available agent types:")
    for num, desc in CHOICE_MAP.items():
        print(f"  {num}: {desc}")
    print("-" * 30)
    while True:
        try:
            userChoice = input("\nSelect agent by number (default: 1): ").strip()
            if not userChoice:
                userChoice = 1
            else:
                userChoice = int(userChoice)
            choiceStr = CHOICE_MAP[userChoice]
            modulePath, funcName = PROCESS_MAP[choiceStr]
            module = importlib.import_module(modulePath)
            if hasattr(module, "MainAgent"):
                fn = getattr(module.MainAgent(), funcName)
            else:
                fn = getattr(module, funcName)
            print(f"\n[Selected Agent]: {choiceStr}")
            return fn, choiceStr
        except (ValueError, KeyError, ImportError) as e:
            print(f"Invalid choice or import error: {e}")

if __name__ == "__main__":
    processInput, agent = selectAgent()
    print("-" * 30)
    while True:
        userInput = input("Enter your query (or ':switch' to change agent, Enter to exit):\n")
        if userInput.strip() == "":
            print("Goodbye!")
            break
        if userInput.strip().lower() == ":switch":
            processInput, agent = selectAgent()
            print("-" * 30)
            continue
        print(f"\n[User Input]: {userInput}\n")
        try:
            processInput(userInput, VERBOSE)
        except Exception as e:
            logging.exception("Error during processing:")

