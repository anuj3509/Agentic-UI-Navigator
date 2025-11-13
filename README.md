# AI UI Guide Generator

Ask "How do I do X in Y app?" and the AI generates a step-by-step visual guide by actually doing it in the browser.

## Setup (2 minutes)

```bash
# 1. Install
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# 2. Add your OpenAI key (only this is required!)
echo "OPENAI_API_KEY=sk-your-key-here" > .env
```

## Usage

**Just ask a question:**

```bash
python app.py "How do I create a project in Linear?"
```

**What happens:**
1. AI understands your question (extracts app + task)
2. Opens browser to the app
3. **Detects if login is required** - pauses and waits for you to log in
4. **Automatically continues** when login is complete
5. AI navigates and completes the task
6. Captures screenshots at each UI state
7. Generates guide with screenshots in `dataset/` folder

**More examples:**
```bash
python app.py "How do I filter a database in Notion?"
python app.py "How to search issues in GitHub?"
python app.py "How to find videos on YouTube?"
```

**🔐 Secure Login:**
- System **automatically detects** login pages
- Pauses and shows: "🔐 LOGIN REQUIRED - Please log in manually"
- Monitors every 3 seconds for login completion
- **Auto-resumes** when you're logged in
- No passwords stored locally!

## Output

Guides are saved to: `dataset/{app}/{task}/`

Each guide includes:
- `screenshots/` - Step-by-step screenshots
- `metadata.json` - Task details, states, actions
- `README.md` - Auto-generated markdown guide

Example:
```
dataset/linear/create_a_project/
  screenshots/
    01_projects_page.png
    02_create_button_clicked.png
    03_modal_opened.png
    04_form_filled.png
    05_project_created.png
  metadata.json
  README.md
```

## Pre-configured Sites

**No login needed:**
- youtube, reddit, wikipedia, stackoverflow

**Need login (manual login in browser - no credentials needed!):**
- github, notion, linear, linkedin, slack, gmail, trello, asana, jira, figma

The browser will open and **continuously monitor** until you log in. Much more secure than storing passwords!

## Examples

**Browse Reddit:**
```
> open reddit
> do find top posts on r/programming
```

**GitHub:**
```
> open github
> do browse trending repositories
> do star the first one
```

**YouTube:**
```
> open youtube
> do search for cats
> do play the first video
```

## How It Works

**Natural Language Understanding → No Hardcoded Commands**

1. **You give ANY natural language command** - "Create a project", "Find issues about bugs", "Search for Python"
2. **LLM breaks down the task** - Converts your goal into logical steps
3. **Vision agent analyzes screenshot** - GPT-4o "sees" the current UI state
4. **Agent decides next action** - Figures out what to click/type based on what it sees
5. **Browser executes action** - Clicks, types, scrolls, etc.
6. **State detection** - Captures screenshots when UI changes significantly
7. **Repeat until complete** - Continues until task is done

**Key Features:**
- ✅ **No hardcoded scripts** - Agent figures out navigation from screenshots
- ✅ **Works with any app** - Just add URL to config
- ✅ **Natural language input** - Any command, any task
- ✅ **Smart state capture** - Only saves meaningful UI changes

All workflows are saved to `dataset/` folder with screenshots and metadata.

## Files

- `app.py` - Main application (Browser Use framework)
- `config/apps.yaml` - Website definitions
- `config/tasks.yaml` - Example tasks
- `.env` - Your OpenAI API key

## Troubleshooting

**"App not found"**
- Add it to `config/apps.yaml`

**"Login failed"**
- Check credentials in `.env`
- Format: `APPNAME_EMAIL` and `APPNAME_PASSWORD`

**Browser doesn't open**
- Don't use headless mode: just run `python cli.py` normally

**Task fails**
- Be more specific: "click the search button" not "search"
- Try simpler tasks first

## That's It

No complicated setup. No hardcoded scripts. Just add a website to the config and start using it.

Questions? The code is simple - just read `cli.py` and `src/apps/universal_app.py`.
