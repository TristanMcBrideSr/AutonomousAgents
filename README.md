
---

# AutonomousAgents

**AutonomousAgents** is a modular Python framework for building, managing, and deploying basic or advanced AI agent systems.
It enables orchestration of multiple specialized agents that can be powered by multiple providers (like OpenAI and Google) and perform a wide range of autonomous tasks through a simple interactive console.

---

## Features

* **Multiple Agent Styles:**

  * **Options 1-2:** Switch between basic (No Vendor Lock) and advanced (No Vendor Lock) agents. Set your provider (`openai` or `google` etc..) in the `.env` file.
  * **Options 3-8:** Switch between OpenAI and Google agent implementations interactively.
* **Extensible Skills & Tools:** Easily add or customize agent capabilities.
* **API-Driven Intelligence:** Integrates with multiple providers such as OpenAI and Google for responses.
* **Dynamic Agent Selection:** Change agent types in real time using a terminal prompt.
* **Environment Configuration:** Secure API management using `.env`.

---

## Installation

1. **Clone the repository:**

   ```sh
   git clone https://github.com/TristanMcBrideSr/AutonomousAgents.git
   cd AutonomousAgents
   ```

2. **Install Python dependencies:**

   ```sh
   pip install -r requirements.txt
   ```

3. **Set up your environment variables:**

   * Create a `.env` file in the project root.
   * Add your API keys and configuration as needed (see below).

---

## Quick Start

To launch the interactive agent demo, run:

```sh
python AutonomousAgents/AutonomousAgents.py
```

### You will see:

```
Autonomous Agent Demo System
------------------------------
Available agent types:
  1: Basic Agent
  2: Advanced Agent
------------------------------
Select agent by number (default: 1):
```

* **Options 1 and 2** are vendor-neutral. Set your provider in the `.env` file (e.g., `PROVIDER=openai` or `PROVIDER=google`).
* Enter a number to select an agent type.
* Enter your query for the agent to process.
* Type `:switch` to change agent types at any time.
* Press Enter on an empty line to exit.

#### Example Session

```
Enter your query (or ':switch' to change agent, Enter to exit):
What's the weather in New York?

[User Input]: What's the weather in New York?

<agent's response here>

Enter your query (or ':switch' to change agent, Enter to exit):
:switch
...
```

---

## Project Structure

```
AutonomousAgents/
│
├── Agents/              # Agent orchestration modules
│   ├── Providers/       # Provider-specific agent implementations
│   ├── Advanced.py
│   └── Basic.py
├── Skills/               # Agent skills: date, time, weather, etc.
├── Tools/                # Agent tools: date, time, weather, etc.
├── Utils/                # Utility modules: skill graph, schemas, etc.
├── AutonomousAgents.py   # Interactive agent launcher
└── requirements.txt
```

---

## Environment Variables

Configure your `.env` file with the required keys. For example:

```
GROQ_API_KEY=Please Visit https://groq.com to get an api key
OPENAI_API_KEY=Please Visit https://openai.com to get an api key
GOOGLE_API_KEY=Please Visit https://cloud.google.com to get an api key
ANTHROPIC_API_KEY=Please Visit https://www.anthropic.com to get an api key
XAI_API_KEY=Please Visit https://xaia.ai to get an api key
PROVIDER=openai   # or 'google', 'anthropic', 'groq', 'xai'
```

---

## Requirements

* Python 3.10+
* Install all dependencies in `requirements.txt`:

  ```
  HoloAI
  ```

---

## Extending the Framework

* **Add new skills:** Create new modules in `Skills/` or `Tools/` and they will automatically be registered in the skill graph.
* **Skills are for options 1-2:** Basic and Advanced agents can use any skill in the `Skills/` directory.
* **Tools are for options 3-8:** OpenAI and Google agents can use any tool in the `Tools/` directory.

---

## Contributing

Pull requests are welcome!
For major changes, please open an issue first to discuss your proposal.

---

## License

This project is licensed under the [Apache License, Version 2.0](LICENSE).
Copyright 2025 Tristan McBride Sr.

You may use, modify, and distribute this software under the terms of the license.
Please just give credit to the original authors.

If you like this project, consider supporting it by starring the repository or contributing improvements!

---

**Authors:**
- Tristan McBride Sr.
- Sybil

