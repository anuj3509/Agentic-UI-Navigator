# Quick Setup Guide

## Installation (2 minutes)

```bash
# 1. Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# 2. Configure API key
echo "OPENAI_API_KEY=sk-your-actual-key-here" > .env
```

## Usage

```bash
python app.py "How do I create a project in Linear?"
```

## How It Works

1. **Parse Question** - LLM extracts app name and task
2. **Open Browser** - Launches browser to target app
3. **Auto-Detect Login** - System detects if login page appears
4. **Manual Login** - Pauses for you to log in, monitors every 3s, auto-resumes when done
5. **AI Navigation** - Browser Use framework navigates automatically
6. **Screenshot Capture** - Captures at each significant step
7. **Dataset Generation** - Saves to `dataset/{app}/{task}/`

### 🔐 Login Detection

The system intelligently detects login pages by:
- ✅ Checking URL patterns (`/login`, `/signin`, `/auth`)
- ✅ Analyzing page titles
- ✅ Detecting password/email input fields
- ✅ Monitoring for page navigation changes

When a login page is detected:
```
======================================================================
🔐 LOGIN REQUIRED
======================================================================

👤 Please log in manually in the browser window
   The system will automatically detect when you're logged in
   (waiting up to 180 seconds)

   ⏳ Still waiting... (15s elapsed)
   ⏳ Still waiting... (30s elapsed)

✓ Login detected! Continuing with navigation...
```

## Output Structure

```
dataset/
  {app}/
    {task}/
      screenshots/
        01_step_01.png
        02_step_02.png
        ...
      metadata.json
      workflow.md
```

## Examples

```bash
# YouTube (no login)
python app.py "How to search for Python tutorials on YouTube?"

# GitHub (requires login)
python app.py "How to star a repository on GitHub?"

# Linear (requires login)
python app.py "How to create a project in Linear?"

# Notion (requires login)
python app.py "How to filter a database in Notion?"
```

## Framework

Uses **Browser Use** - production-ready browser automation framework with:
- ✅ Robust error handling
- ✅ Smart action extraction
- ✅ DOM-based element selection
- ✅ Built-in modal/popup handling
- ✅ Automatic screenshot capture

## API Keys

**Required:**
- `OPENAI_API_KEY` - Your OpenAI API key

**Optional:**
- `BROWSER_USE_API_KEY` - Get $10 free at cloud.browser-use.com for optimized model

## Troubleshooting

**"OPENAI_API_KEY not found"**
```bash
echo "OPENAI_API_KEY=sk-..." > .env
```

**"playwright not found"**
```bash
playwright install chromium
```

**App not configured**
- Add to `config/apps.yaml`

## That's It!

Your system is ready to generate UI guides for any web application! 🚀

