# Voice Agent — Real Estate Agency

A voice agent built with [LiveKit Agents](https://docs.livekit.io/agents/) that handles phone/web calls for a real estate agency and answers questions about a property catalog.

## Table of contents

- [Voice Agent — Real Estate Agency](#voice-agent--real-estate-agency)
  - [Table of contents](#table-of-contents)
  - [Architecture](#architecture)
  - [Prerequisites](#prerequisites)
  - [Quickstart (for anyone cloning this repo for the first time)](#quickstart-for-anyone-cloning-this-repo-for-the-first-time)
    - [1. Clone the repository](#1-clone-the-repository)
    - [2. Install dependencies](#2-install-dependencies)
    - [3. Create your LiveKit Cloud account (free)](#3-create-your-livekit-cloud-account-free)
    - [4. Set up your environment variables](#4-set-up-your-environment-variables)
    - [5. Download local models (first time only)](#5-download-local-models-first-time-only)
    - [6. Run the agent](#6-run-the-agent)
    - [7. Test the agent live](#7-test-the-agent-live)
  - [Project structure](#project-structure)
  - [The knowledge base (properties)](#the-knowledge-base-properties)
  - [Deploying to Azure](#deploying-to-azure)
  - [Expected costs](#expected-costs)
  - [Troubleshooting](#troubleshooting)

## Architecture

```
Phone call / browser
        │
        ▼
   LiveKit Cloud (SFU + dispatch)
        │
        ▼
  agent.py (Python worker, always running)
        │
        ├── STT   → LiveKit Inference (Deepgram nova-3)
        ├── LLM   → LiveKit Inference (OpenAI gpt-4.1-mini) + function_tool
        ├── TTS   → LiveKit Inference (Cartesia sonic-3)
        └── Turn detection → LiveKit Inference (cloud model, local fallback)
        │
        ▼
  properties.json (local) or Azure Blob Storage (production)
```

The entire voice pipeline (STT/LLM/TTS/turn detection) runs through **LiveKit Inference**, with no third-party credentials (Google, OpenAI, etc.) required — it's billed against your LiveKit Cloud project.

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) as the package manager
- A [LiveKit Cloud](https://cloud.livekit.io) account (free tier)
- (Optional, production only) An Azure account

## Quickstart (for anyone cloning this repo for the first time)

Follow these steps in order. You don't need any prior LiveKit knowledge.

### 1. Clone the repository

```bash
git clone <this-repo-url>
cd <repo-folder>
```

### 2. Install dependencies

This project uses [uv](https://docs.astral.sh/uv/) as its package manager. If you don't have it yet:

```bash
# Windows (PowerShell)
irm https://astral.sh/uv/install.ps1 | iex

# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then, inside the repo folder:

```bash
uv sync
```

### 3. Create your LiveKit Cloud account (free)

1. Go to **[cloud.livekit.io](https://cloud.livekit.io)** and sign up (you can use your GitHub or Google account).
2. Once in, create a **new project** (it will prompt you automatically the first time).
3. Inside your project, go to **Settings → Keys**.
4. Copy these three values — you'll need them in the next step:
   - `LIVEKIT_URL` (something like `wss://your-project.livekit.cloud`)
   - `LIVEKIT_API_KEY`
   - `LIVEKIT_API_SECRET`

### 4. Set up your environment variables

Copy the template:

```bash
cp .env.example .env
```

Open the `.env` file that was just created and paste in the 3 values you copied from LiveKit in the previous step:

```dotenv
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your_api_key_here
LIVEKIT_API_SECRET=your_api_secret_here
```

⚠️ **The `.env` file is yours only — never commit it or share it.** It's already listed in `.gitignore`. `.env.example` is the only template that goes into the repository, with no real values.

You don't need any other external API key (OpenAI, Google, etc.) — all STT/LLM/TTS runs through LiveKit Inference using those same credentials.

> **Optional:** if you switch the LLM in `agent.py` to a Google model instead of the default `openai/gpt-4.1-mini`, you'll additionally need a `GOOGLE_API_KEY` (see the commented-out line in `.env.example`). Not required for the default setup.

### 5. Download local models (first time only)

```bash
uv run -m livekit.agents download-files
```

This downloads the fallback models (VAD, turn detector) so the agent starts up fast and keeps working even if there's a hiccup connecting to the cloud.

### 6. Run the agent

```bash
uv run agent.py dev
```

Wait until you see a line like this in the terminal:
```
registered worker {"id": "AW_...", "url": "wss://your-project.livekit.cloud", ...}
```
That confirms the agent is running and ready to take test calls. **Keep this terminal open** — if you close it, the agent stops being available.

### 7. Test the agent live

1. Go back to **[cloud.livekit.io](https://cloud.livekit.io)** and open your project.
2. In the sidebar, click **Agents**.
3. Your agent should show up (auto-detected because the worker from step 6 is running). Click it to open the **Console**.
4. Click the blue **Start session** button (top right).
5. Allow the browser to use your microphone if prompted.
6. **Wait about 5 seconds** — the agent takes a moment to connect and greet you. It's not failing, it's just initializing the voice session.
7. Once it greets you, try questions like:
   - "What properties do you have in Madrid?"
   - "I'm looking for an apartment, any city is fine"
   - "Do you have chalets in Ocaña?"
8. You can watch what the agent is doing in real time (transcripts, tool calls, errors) in the **Events** tab of the same Console.

With this, you now have the agent running locally and tested live, no deployment needed yet.

## Project structure

```
.
├── agent.py                     # Agent logic + search tool
├── properties.json              # Property knowledge base (dev/fallback)
├── pyproject.toml / uv.lock     # Dependencies
├── Dockerfile                   # Worker image for production
├── .env.example                 # Environment variable template
├── .github/workflows/deploy.yml # CI/CD: build + deploy to Azure on every push to main
└── README_DEPLOY.md             # Detailed Azure CLI commands
```

## The knowledge base (properties)

`properties.json` contains an array of objects shaped like this:

```json
{
  "id": 1,
  "ciudad": "Madrid",
  "tipo": "piso",
  "habitaciones": 2,
  "precio": 210000,
  "descripcion": "Piso reformado de 2 habitaciones cerca del metro Sol."
}
```

- **Locally**: edit the file directly.
- **In production**: it's uploaded to Azure Blob Storage and the agent automatically re-reads it (60s cache) with no redeploy needed — see `README_DEPLOY.md`, section 3.

## Deploying to Azure

See [`README_DEPLOY.md`](./README_DEPLOY.md) for the full `az cli` commands (creating the resource group, Container Registry, Storage Account, and Container App) and the GitHub secrets setup for the CI/CD pipeline.

Automated flow summary:
```
git push origin main
        │
        ▼
GitHub Actions (.github/workflows/deploy.yml)
        │
        ├── docker build
        ├── push to Azure Container Registry
        └── deploy to Azure Container Apps
```

## Expected costs

| Scenario | Cost |
|---|---|
| Local development (`uv run agent.py dev`) | $0 |
| First 30 days on Azure (welcome credit) | $0 |
| Production on Azure Container Apps (24/7 worker, after the credit month) | ~$10-13 USD/month |

The worker needs `minReplicas ≥ 1` (it can't scale to zero) because it has to stay registered with LiveKit Cloud at all times to receive calls — that's why it doesn't fully fit within Azure's "always free" quota.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `ModuleNotFoundError: livekit.plugins.turn_detector` | Deprecated plugin | Use `from livekit.agents.inference import TurnDetector` |
| `429 RESOURCE_EXHAUSTED` on the LLM | External provider quota exhausted | We use LiveKit Inference, so this no longer applies |
| `LiveKit Inference STT connection timed out` | Cold start / local models not downloaded | Run `uv run -m livekit.agents download-files` before the first launch |
| Console doesn't detect any agent | The local worker isn't running | Verify `uv run agent.py dev` is active in a terminal |
| `az login` → "not subscribed" | Azure free subscription not activated yet | Complete signup at [azure.microsoft.com/free](https://azure.microsoft.com/free) |