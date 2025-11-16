# Agentic UI Navigator

AI-powered browser automation that generates step-by-step visual guides for any web application.

## Quick Start

### 1. Install Dependencies

```bash
# Backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend
npm install --legacy-peer-deps
cd ..
```

### 2. Configure

```bash
# Add your OpenAI API key
echo "OPENAI_API_KEY=sk-your-key-here" > .env
```

### 3. Run

Open two terminals:

**Terminal 1 - Backend:**
```bash
source venv/bin/activate
python server.py
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

Open http://localhost:3000 in your browser.

## Usage

Type your question in the chat interface:
- "How do I search for videos on YouTube?"
- "How to star a repository in GitHub?"
- "How do I create a project in Linear?"

The system will:
1. Navigate to the application
2. Perform the task automatically
3. Capture screenshots at each step
4. Generate a workflow guide in `dataset/{app}/{task}/`

## Architecture

- **Backend**: FastAPI server (`server.py`) on port 8000
- **Frontend**: Next.js app on port 3000
- **Communication**: REST API + WebSocket for real-time updates
- **Automation**: Browser Use framework with GPT-4o vision

## Output

Generated guides are saved to `dataset/{app}/{task}/` containing:
- Screenshots of each step
- Workflow markdown documentation
- Metadata JSON file

## Viewing Backend Logs

To see what the agent is doing in real-time (browser automation, screenshots, etc.):

```bash
# If backend is running in background, check the terminal where you started it
# OR restart it in foreground to see live logs:

source venv/bin/activate
python server.py
```

The logs will show:
- Parsing queries
- Browser navigation steps
- Screenshot captures
- Agent decisions
- Task completion status

## Requirements

- Python 3.8+
- Node.js 18+
- OpenAI API key
