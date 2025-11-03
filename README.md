# MindBridge – NVIDIA x AWS Edition

Agentic mental-health triage and therapist matching, powered by NVIDIA Nemotron on AWS.

This hackathon version of MindBridge deploys two NVIDIA NIM services (reasoning + embeddings) on Amazon SageMaker JumpStart and connects the FastAPI + React application to those endpoints.

## 🧱 Architecture Snapshot
- **Backend**: FastAPI (`voice_api.py`) orchestrating LangGraph agents (intake, crisis, resource, habits)
- **Frontend**: React 19, Vite, Tailwind – real-time chat with stage badges, scheduling, and habit support
- **Models**:
  - `nvidia-nemotron-nano-8b-nim` for agent reasoning
  - `nvidia-llama3-2-nv-embedqa-1b-v2-nim` for retrieval embeddings (therapist/resource search)
- **AWS Services**: SageMaker endpoints for both NIMs, optional S3/FAISS store for embedding vectors

## 🚀 Quick Start

### 1. Clone & set up
```bash
git clone https://github.com/SAMK-online/MindBrid-NvidiaxAWS.git
cd MindBrid-NvidiaxAWS

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Provision NVIDIA NIM endpoints on SageMaker
Inside the hackathon’s Vocareum lab (or any AWS environment with the provided credits):

```bash
export AWS_ACCESS_KEY_ID="<from Vocareum>"
export AWS_SECRET_ACCESS_KEY="<from Vocareum>"
export AWS_SESSION_TOKEN="<from Vocareum>"
export AWS_DEFAULT_REGION="us-east-1"
export SAGEMAKER_EXECUTION_ROLE="arn:aws:iam::112571254920:role/voclabs"

python deploy_nim_sagemaker.py
cat nim_endpoints.json
```

The script deploys both endpoints and writes `nim_endpoints.json`. Copy the endpoint names and URLs.

### 3. Configure the application

Create `.env` in the project root:
```env
AWS_REGION=us-east-1
NIM_LLM_ENDPOINT=<endpoint-name-from-json>
NIM_EMBED_ENDPOINT=<embedding-endpoint-name>
AWS_ACCESS_KEY_ID=<optional if using local AWS CLI profile>
AWS_SECRET_ACCESS_KEY=<optional>
AWS_SESSION_TOKEN=<optional>
TAVILY_API_KEY=<optional fallback search>
ELEVENLABS_API_KEY=<optional voice synth>
```

For the React app (`ui/.env`):
```env
VITE_API_URL=http://localhost:8000
```

### 4. Run MindBridge locally
```bash
# backend
uvicorn voice_api:app --reload --port 8000

# frontend
cd ui
npm install
npm run dev
```
Open http://localhost:5173 to start the conversation loop. The agents now call the SageMaker-hosted NIM endpoints.

### 5. Optional: Build Retrieval Store
Use the embedding endpoint to index therapist bios/resource snippets. Store vectors in FAISS or pgvector and expose them through the Resource Agent (see `agents/resource_agent.py`) before falling back to Tavily search.

## 📁 Project Layout
```
agents/        # Base, intake, crisis, resource, habit, coordinator agents
api/index.py   # Vercel adapter for the FastAPI app
models/        # User, therapist, habit schemas + mock data helpers
workflows/     # LangGraph orchestration from intake → crisis → resource
voice_api.py   # FastAPI entrypoint for voice + chat applications
ui/            # React frontend with voice recorder & dashboard
deploy_nim_sagemaker.py # SageMaker JumpStart deployment script
```

## ✅ Submission Notes
- Significant updates: AWS SageMaker deployment flow, Retrieval Embedding NIM integration scaffold, updated documentation (Nov 2025).
- Third-party services: Tavily (web search) and ElevenLabs (voice) remain optional and require API keys.
- Demo deliverables: include `nim_endpoints.json`, SageMaker console screenshots, and a screencast of the AWS-backed conversation flow.

Questions? Ping `samk` on Discord or open an issue in this repo. Good luck in the hackathon! 💚
