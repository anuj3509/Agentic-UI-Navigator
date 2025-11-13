#!/usr/bin/env python3
"""
Guide Generator using Browser Use framework.
More robust browser automation with LLM integration.
"""
import sys
import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from browser_use import Agent, Browser, ChatBrowserUse
from browser_use.agent.views import AgentHistoryList
from typing import Optional
import json
import yaml
import shutil
from datetime import datetime
import time


async def parse_question(question: str) -> dict:
    """Parse natural language question to extract app and task."""
    load_dotenv()
    
    # Use OpenAI directly for parsing (simpler than Browser Use LLM)
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    prompt = f"""Extract the application name and task from this question:

Question: "{question}"

Return a JSON object with:
- app: The application name (lowercase, one word like "linear", "notion", "github", etc.)
- task: The task to perform (action phrase like "create a project", "filter a database", etc.)

Examples:
- "How do I create a project in Linear?" -> {{"app": "linear", "task": "create a project"}}
- "How do I filter a database in Notion?" -> {{"app": "notion", "task": "filter a database"}}
- "How to search issues in GitHub?" -> {{"app": "github", "task": "search issues"}}

Return ONLY the JSON object."""

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    content = response.choices[0].message.content.strip()
    
    # Extract JSON
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()
    
    return json.loads(content)


def get_app_url(app_name: str) -> str:
    """Get the URL for an app from config."""
    config_file = Path("config/apps.yaml")
    if config_file.exists():
        with open(config_file, 'r') as f:
            apps = yaml.safe_load(f)
            if app_name in apps:
                return apps[app_name]['base_url']
    
    # Fallback defaults
    defaults = {
        "youtube": "https://www.youtube.com",
        "github": "https://github.com",
        "linear": "https://linear.app",
        "notion": "https://www.notion.so",
        "stackoverflow": "https://stackoverflow.com",
        "reddit": "https://www.reddit.com",
    }
    return defaults.get(app_name, f"https://{app_name}.com")


def save_to_dataset(app_name: str, task: str, history: AgentHistoryList, screenshots_dir: Path):
    """Save Browser Use results to dataset folder."""
    from src.dataset.builder import DatasetBuilder
    from src.dataset.docs_generator import DocsGenerator
    
    # Create dataset structure
    builder = DatasetBuilder()
    task_name = task.replace(' ', '_').lower()
    
    dataset_path = Path("dataset") / app_name / task_name
    screenshots_path = dataset_path / "screenshots"
    screenshots_path.mkdir(parents=True, exist_ok=True)
    
    # First, try to get screenshots from Browser Use's own storage
    screenshot_files = []
    browser_use_screenshots = []
    
    # Extract screenshot paths from history
    for item in history.history:
        if hasattr(item, 'state') and hasattr(item.state, 'screenshot_path'):
            if item.state.screenshot_path:
                browser_use_screenshots.append(Path(item.state.screenshot_path))
    
    # Copy Browser Use's screenshots if available
    if browser_use_screenshots:
        print(f"📸 Found {len(browser_use_screenshots)} screenshots from Browser Use")
        for i, screenshot_path in enumerate(browser_use_screenshots, start=1):
            if screenshot_path.exists():
                new_filename = f"{i:02d}_step_{i}.png"
                new_path = screenshots_path / new_filename
                shutil.copy2(screenshot_path, new_path)
                screenshot_files.append(str(new_path.relative_to(dataset_path)))
                print(f"   ✓ Copied {screenshot_path.name} -> {new_filename}")
    
    # Also check our custom screenshots directory (fallback)
    elif screenshots_dir and screenshots_dir.exists():
        for i, screenshot_file in enumerate(sorted(screenshots_dir.glob("*.png")), start=1):
            new_filename = f"{i:02d}_{screenshot_file.stem}.png"
            new_path = screenshots_path / new_filename
            shutil.copy2(screenshot_file, new_path)
            screenshot_files.append(str(new_path.relative_to(dataset_path)))
    
    # Create metadata from history
    captured_states = []
    for i, item in enumerate(history.history, start=1):
        state = {
            "step": i,
            "screenshot": screenshot_files[i-1] if i <= len(screenshot_files) else "",
            "description": str(item.state),
            "action_taken": str(item.result.extracted_content if hasattr(item.result, 'extracted_content') else item.result),
            "reasoning": ""
        }
        captured_states.append(state)
    
    # Save metadata
    metadata = {
        "task_name": task_name,
        "task_query": task,
        "app_name": app_name,
        "timestamp": datetime.now().isoformat(),
        "num_states": len(captured_states),
        "states": captured_states,
        "framework": "browser-use"
    }
    
    metadata_path = dataset_path / "metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    # Generate documentation
    docs_gen = DocsGenerator()
    docs_gen.generate_workflow_markdown(str(dataset_path), metadata)
    
    return str(dataset_path)


async def detect_login_page(page) -> bool:
    """Detect if current page is a login page."""
    try:
        # Get page content
        content = await page.content()
        url = page.url.lower()
        title = await page.title()
        title_lower = title.lower()
        
        # Check URL patterns
        login_url_patterns = ['login', 'signin', 'sign-in', 'auth', 'authenticate', 'sso']
        if any(pattern in url for pattern in login_url_patterns):
            return True
        
        # Check title
        login_title_patterns = ['log in', 'sign in', 'login', 'signin', 'authenticate']
        if any(pattern in title_lower for pattern in login_title_patterns):
            return True
        
        # Check for common login form elements
        login_selectors = [
            'input[type="password"]',
            'input[name*="password"]',
            'input[name*="email"]',
            'input[placeholder*="password" i]',
            'input[placeholder*="email" i]',
            'button:has-text("Log in")',
            'button:has-text("Sign in")',
        ]
        
        for selector in login_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    return True
            except:
                continue
        
        return False
    except Exception as e:
        return False


async def wait_for_manual_login(browser, max_wait_time: int = 180):
    """Wait for user to manually log in, monitoring for page changes."""
    print("\n" + "="*70)
    print("🔐 LOGIN REQUIRED")
    print("="*70)
    print("\n👤 Please log in manually in the browser window")
    print("   The system will automatically detect when you're logged in")
    print(f"   (waiting up to {max_wait_time} seconds)\n")
    
    start_time = time.time()
    check_interval = 3  # Check every 3 seconds
    
    try:
        # Access page through browser context (handle both public and private attrs)
        page = None
        if hasattr(browser, '_context') and browser._context and browser._context.pages:
            page = browser._context.pages[0]
        elif hasattr(browser, 'context') and browser.context and browser.context.pages:
            page = browser.context.pages[0]
        
        if not page:
            print("⚠ Could not access browser page")
            return False
        
        initial_url = page.url
        last_status_time = start_time
        
        while (time.time() - start_time) < max_wait_time:
            await asyncio.sleep(check_interval)
            
            current_url = page.url
            is_still_login = await detect_login_page(page)
            
            # Show periodic status
            elapsed = int(time.time() - start_time)
            if elapsed - (last_status_time - start_time) >= 15:  # Every 15 seconds
                print(f"   ⏳ Still waiting... ({elapsed}s elapsed)")
                last_status_time = time.time()
            
            # Check if user has navigated away from login
            if current_url != initial_url and not is_still_login:
                print("\n✓ Login detected! Continuing with navigation...\n")
                await asyncio.sleep(2)  # Give page time to fully load
                return True
            
            # Also check if login page disappeared (for SPAs)
            if initial_url == current_url and not is_still_login:
                print("\n✓ Login page changed! Continuing with navigation...\n")
                await asyncio.sleep(2)
                return True
        
        # Timeout
        print(f"\n⏱ Timeout after {max_wait_time}s. Continuing anyway...")
        return False
        
    except Exception as e:
        print(f"\n⚠ Error during login wait: {e}")
        return False


async def generate_guide(question: str):
    """Generate UI guide using Browser Use framework."""
    print("\n" + "="*70)
    print("AI UI Guide Generator (Browser Use)")
    print("="*70)
    print(f"\nQuestion: {question}\n")
    
    # Parse question
    print("🤔 Understanding your question...")
    parsed = await parse_question(question)
    
    app_name = parsed.get('app')
    task = parsed.get('task')
    
    print(f"✓ App detected: {app_name}")
    print(f"✓ Task detected: {task}\n")
    
    # Get app URL
    app_url = get_app_url(app_name)
    
    # Create temp directory for screenshots
    screenshots_dir = Path(f"temp_browser_use_screenshots_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    screenshots_dir.mkdir(exist_ok=True)
    
    # Create enhanced task description
    enhanced_task = f"""Navigate to {app_url} and {task}.

Instructions:
1. Go to {app_url}
2. {task.capitalize()}
3. If you encounter a modal, popup, or dialog - close it first before proceeding
4. Capture the key states during this process
5. Once the task is demonstrated (not necessarily completed end-to-end), stop

The goal is to SHOW how to do this task, not necessarily execute every sub-step."""
    
    print("="*70)
    print(f"Generating guide: How to {task} in {app_name.title()}")
    print("="*70 + "\n")
    
    # Initialize Browser Use components
    browser = Browser()
    
    # Browser Use will automatically use OPENAI_API_KEY from .env
    # Passing llm=None makes it use OpenAI GPT-4o by default
    print("ℹ️  Using OpenAI GPT-4o for navigation")
    print("   (Optional: Set BROWSER_USE_API_KEY for optimized ChatBrowserUse model)\n")
    
    # First, navigate to the app to check if login is needed
    print(f"🌐 Opening {app_url}...")
    
    # Browser Use automatically creates session when agent runs
    # We'll check for login in the initial actions instead
    login_detected = [False]  # Track if we've shown login prompt
    
    # Callback to capture screenshots
    screenshot_counter = [0]  # Use list to modify in closure
    
    async def save_step_callback(state, action, step):
        """Save screenshot at each step and check for login pages."""
        screenshot_counter[0] += 1
        try:
            # Browser Use stores the context in browser._context (private attr)
            # Access the page through the browser session
            if hasattr(browser, '_context') and browser._context and browser._context.pages:
                current_page = browser._context.pages[0]
            elif hasattr(browser, 'context') and browser.context and browser.context.pages:
                current_page = browser.context.pages[0]
            else:
                print(f"⚠ Could not access browser page for screenshot {screenshot_counter[0]}")
                return
            
            # Check if we hit a login page during navigation
            if not login_detected[0]:
                is_login = await detect_login_page(current_page)
                if is_login:
                    login_detected[0] = True
                    # Pause agent execution and wait for manual login
                    await wait_for_manual_login(browser, max_wait_time=180)
            
            screenshot_path = screenshots_dir / f"step_{screenshot_counter[0]:02d}.png"
            await current_page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"📸 Captured screenshot {screenshot_counter[0]}")
        except Exception as e:
            print(f"⚠ Could not capture screenshot: {e}")
    
    # Modify the task to handle login gracefully
    modified_task = f"""Navigate to {app_url} and {task}.

Instructions:
1. Go to {app_url}
2. If you see a login page, STOP immediately and use the 'done' action with success=False and explain that login is required
3. If already logged in or no login needed, proceed to {task}
4. If you encounter a modal, popup, or dialog - close it first before proceeding
5. Capture the key states during this process
6. Once the task is demonstrated (not necessarily completed end-to-end), stop

The goal is to SHOW how to do this task, not necessarily execute every sub-step."""
    
    # Create agent with callback
    agent = Agent(
        task=modified_task,
        llm=None,  # Will use OpenAI from OPENAI_API_KEY env var
        browser=browser,
        register_new_step_callback=save_step_callback,
    )
    
    try:
        # Run the agent
        print("🤖 Agent starting navigation...\n")
        history = await agent.run()
        
        # Save to dataset
        print("\n📁 Saving to dataset...")
        dataset_path = save_to_dataset(app_name, task, history, screenshots_dir)
        
        print("\n" + "="*70)
        print("✓ GUIDE GENERATED SUCCESSFULLY!")
        print("="*70)
        print(f"\nTask: {task}")
        print(f"App: {app_name}")
        print(f"\nLocation: {dataset_path}/")
        print(f"Screenshots: {dataset_path}/screenshots/")
        print(f"Guide: {dataset_path}/workflow.md")
        print(f"Metadata: {dataset_path}/metadata.json")
        print(f"\nTotal steps captured: {len(history.history)}")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup temp screenshots
        try:
            if screenshots_dir.exists():
                shutil.rmtree(screenshots_dir)
        except:
            pass


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python app.py \"Your question here\"")
        print("\nExamples:")
        print('  python app.py "How do I create a project in Linear?"')
        print('  python app.py "How do I filter a database in Notion?"')
        print('  python app.py "How to star a repository in GitHub?"')
        print('  python app.py "How to search for videos on YouTube?"')
        sys.exit(1)
    
    # Check for OpenAI API key
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not found in .env file")
        print("Please create a .env file with: OPENAI_API_KEY=sk-...")
        sys.exit(1)
    
    question = sys.argv[1]
    
    try:
        await generate_guide(question)
    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

