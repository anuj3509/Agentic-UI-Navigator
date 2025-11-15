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
import imagehash
from PIL import Image
import io
import logging

# Reduce Browser Use logging verbosity
logging.getLogger('browser_use').setLevel(logging.WARNING)
logging.getLogger('openai').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)


def load_url_cache() -> dict:
    """Load cached app URLs from file."""
    cache_file = Path("config/url_cache.json")
    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_url_cache(cache: dict):
    """Save app URLs to cache file."""
    cache_file = Path("config/url_cache.json")
    cache_file.parent.mkdir(exist_ok=True)
    with open(cache_file, 'w') as f:
        json.dump(cache, f, indent=2)


async def parse_question(question: str) -> dict:
    """Parse natural language question to extract app, task, URL, and auth requirements."""
    load_dotenv()
    
    # Use OpenAI directly for parsing (simpler than Browser Use LLM)
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # Check if we have a cached URL for this app
    url_cache = load_url_cache()
    
    prompt = f"""Extract the application name, task, URL, and authentication requirements from this question:

Question: "{question}"

Return a JSON object with:
- app: The application name (lowercase, one word like "linear", "notion", "github", etc.)
- task: The task to perform (action phrase like "create a project", "filter a database", etc.)
- url: The main web application URL for this app
- requires_auth: true if the app typically requires login, false otherwise

Examples:
- "How do I create a project in Linear?" -> {{"app": "linear", "task": "create a project", "url": "https://linear.app", "requires_auth": true}}
- "How do I filter a database in Notion?" -> {{"app": "notion", "task": "filter a database", "url": "https://www.notion.so", "requires_auth": true}}
- "How to search issues in GitHub?" -> {{"app": "github", "task": "search issues", "url": "https://github.com", "requires_auth": false}}
- "How to find videos on YouTube?" -> {{"app": "youtube", "task": "find videos", "url": "https://www.youtube.com", "requires_auth": false}}
- "How to create a board in Trello?" -> {{"app": "trello", "task": "create a board", "url": "https://trello.com", "requires_auth": true}}
- "How to search for Python on Stack Overflow?" -> {{"app": "stackoverflow", "task": "search for Python", "url": "https://stackoverflow.com", "requires_auth": false}}

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
    
    parsed = json.loads(content)
    
    # Cache the URL for future use
    app_name = parsed.get('app')
    if app_name and app_name not in url_cache:
        url_cache[app_name] = {
            'url': parsed.get('url'),
            'requires_auth': parsed.get('requires_auth', True)
        }
        save_url_cache(url_cache)
        print(f"💾 Cached URL for {app_name}")
    
    return parsed


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
    
    # Copy Browser Use's screenshots if available, filtering out login pages
    if browser_use_screenshots:
        print(f"📸 Found {len(browser_use_screenshots)} screenshots from Browser Use")
        filtered_screenshots = []
        
        for idx, screenshot_path in enumerate(browser_use_screenshots):
            if screenshot_path.exists():
                # Check if this is a login page by looking at the corresponding history item
                skip_screenshot = False
                if idx < len(history.history):
                    item = history.history[idx]
                    state_str = str(item.state).lower()
                    result_str = str(item.result).lower() if hasattr(item, 'result') else ""
                    
                    # Skip if URL contains login/auth keywords or action mentions login
                    # Be specific: check for login-related content, not generic "wait"
                    if any(keyword in state_str or keyword in result_str 
                           for keyword in ['login', 'sign in', 'signin', 'sign-in', 
                                          '/auth/', 'google.com/signin', 'accounts.google', 
                                          'sso', 'log in', 'authenticate', 'password',
                                          'oauth', 'saml']):
                        skip_screenshot = True
                        print(f"   ⊘ Skipped {screenshot_path.name} (login/auth page)")
                
                if not skip_screenshot:
                    filtered_screenshots.append(screenshot_path)
        
        print(f"📸 Filtered to {len(filtered_screenshots)} task screenshots (removed {len(browser_use_screenshots) - len(filtered_screenshots)} login screenshots)")
        
        for i, screenshot_path in enumerate(filtered_screenshots, start=1):
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
    print("\n" + "="*40)
    print("Agentic UI Guide Generator")
    print("="*40)
    print(f"\nQuestion: {question}\n")
    
    # Parse question (now includes URL discovery!)
    print("🤔 Understanding your question...")
    parsed = await parse_question(question)
    
    app_name = parsed.get('app')
    task = parsed.get('task')
    app_url = parsed.get('url')  # Get URL directly from LLM
    requires_auth = parsed.get('requires_auth', True)
    
    print(f"✓ App detected: {app_name}")
    print(f"✓ Task detected: {task}")
    print(f"✓ URL found: {app_url}")
    if requires_auth:
        print(f"Note:This app may require login\n")
    else:
        print(f"Note: This app typically doesn't require login\n")
    
    # Create temp directory for screenshots
    screenshots_dir = Path(f"temp_browser_use_screenshots_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    screenshots_dir.mkdir(exist_ok=True)
    
    # Create persistent user data directory for browser sessions
    user_data_dir = Path("browser_profile")
    user_data_dir.mkdir(exist_ok=True)
    
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
    
    # Initialize Browser Use components with persistent user data directory
    # This allows the browser to save and reuse login sessions
    browser = Browser(
        headless=False,
        user_data_dir=str(user_data_dir.absolute()),
        highlight_elements=False,  # Disable overlays - they clutter screenshots
        dom_highlight_elements=False,  # Disable DOM element indexing boxes
        paint_order_filtering=False,  # Disable visual filtering
    )
    
    # Browser Use will automatically use OPENAI_API_KEY from .env
    # Passing llm=None makes it use OpenAI GPT-4o by default
    print("⦿‣ Using OpenAI GPT-4o for navigation")
    print("   (Optional: Set BROWSER_USE_API_KEY for optimized ChatBrowserUse model)\n")
    
    # PRE-FLIGHT LOGIN CHECK: For auth-required sites, integrate login check INTO the main agent task
    print(f"‣ Opening {app_url}...")
    login_detected = [False]  # Track if we've shown login prompt
    pre_login_message_shown = [False]  # Track if we showed login message
    
    # For login-required sites, add manual pause
    if requires_auth:
        print("ℹ️  This site requires login.")
        print("   The browser will open and navigate to the login page.")
        print("   After navigation, you'll be prompted to log in.\n")
    
    # Callback to capture screenshots only on significant UI changes
    screenshot_counter = [0]  # Use list to modify in closure
    last_screenshot_hash = [None]  # Track last screenshot to detect changes
    significant_screenshots = []  # Store paths of significant screenshots
    agent_start_time = [None]  # Track when agent starts to skip early screenshots
    
    async def save_step_callback(state, action, step):
        """Save screenshot only when UI state changes significantly."""
        try:
            # Initialize start time on first callback
            if agent_start_time[0] is None:
                agent_start_time[0] = time.time()
            
            # Skip screenshots in the first 5 seconds (page is still loading)
            elapsed = time.time() - agent_start_time[0]
            if elapsed < 5.0:
                print(f"   ⏭️  Skipping screenshot - initial page load (waiting {5.0 - elapsed:.1f}s more)")
                return
            
            # Access the page using Browser Use's browser session
            current_page = None
            session = None
            
            # Get browser session
            if hasattr(browser, '_context'):
                session = browser._context
            elif hasattr(browser, 'context'):
                session = browser.context
            
            if session and hasattr(session, 'pages') and session.pages:
                current_page = session.pages[0]
            
            if not current_page:
                return
            
            # Wait for UI to stabilize after actions
            # 1. Wait for network activity to settle
            try:
                await current_page.wait_for_load_state('networkidle', timeout=3000)
            except:
                pass  # Continue even if timeout
            
            # 2. Wait for animations to complete
            await asyncio.sleep(1.5)
            
            # 3. Aggressively remove ALL Browser Use overlays and highlighting
            try:
                await current_page.evaluate("""
                    () => {
                        // Remove all elements with extremely high z-index (overlays)
                        const allElements = document.querySelectorAll('*');
                        allElements.forEach(el => {
                            const zIndex = window.getComputedStyle(el).zIndex;
                            if (zIndex && parseInt(zIndex) > 999999) {
                                el.remove();
                            }
                        });
                        
                        // Remove elements with Browser Use signatures
                        const browserUseEls = document.querySelectorAll(
                            '[data-browser-use], [data-browser-use-index], [id^="browser-use"], ' +
                            '[class*="browser-use"], [data-highlight], [data-index], ' +
                            'svg[style*="pointer-events: none"]'
                        );
                        browserUseEls.forEach(el => el.remove());
                        
                        // Remove all absolutely positioned divs at the top level with high z-index
                        const topDivs = Array.from(document.body.children).filter(el => {
                            if (el.tagName === 'DIV') {
                                const style = window.getComputedStyle(el);
                                return style.position === 'absolute' || style.position === 'fixed';
                            }
                            return false;
                        });
                        topDivs.forEach(div => {
                            const style = window.getComputedStyle(div);
                            const zIndex = parseInt(style.zIndex);
                            if (zIndex > 1000) {
                                div.remove();
                            }
                        });
                    }
                """)
                # Wait for DOM to update after removing overlays
                await asyncio.sleep(0.5)
            except:
                pass  # Continue even if cleanup fails
            
            # LOGIN DETECTION: Check if this is a login/auth page and handle it
            if requires_auth and not login_detected[0]:
                is_login = await detect_login_page(current_page)
                if is_login:
                    login_detected[0] = True
                    pre_login_message_shown[0] = True
                    
                    print("\n" + "="*70)
                    print("🔐 LOGIN PAGE DETECTED - PAUSING AGENT")
                    print("="*70)
                    print("👤 Please log in manually in the browser window")
                    print("   DO NOT CLOSE THE BROWSER")
                    print("   The system will resume automatically once logged in")
                    print(f"   (You have up to 5 minutes)")
                    print("="*70 + "\n")
                    
                    # Wait for manual login - this pauses everything
                    login_success = await wait_for_manual_login(browser, max_wait_time=300)
                    
                    if login_success:
                        print("\n✓ Login successful! Resuming task execution...\n")
                    else:
                        print("\n⚠️  Login timeout or not confirmed. Attempting to continue anyway...\n")
                    
                    # Don't capture login page screenshots - return early
                    return
            
            # SKIP screenshot capture if we're still on a login/auth page
            current_url = current_page.url.lower()
            if any(pattern in current_url for pattern in ['login', 'signin', 'sign-in', 'auth', 'accounts.google', 'sso']):
                # Skip login pages - don't capture these in the guide
                return
            
            # SKIP screenshot if page is still loading (gray placeholders, no content)
            try:
                # Check if page has actual visible content
                has_content = await current_page.evaluate("""
                    () => {
                        // Check multiple indicators that page has real content
                        const images = document.querySelectorAll('img[src]:not([src=""])');
                        const videos = document.querySelectorAll('video');
                        const links = document.querySelectorAll('a[href]');
                        const buttons = document.querySelectorAll('button');
                        const textContent = document.body.innerText.trim();
                        
                        // Count actually loaded media
                        let loadedMedia = 0;
                        images.forEach(img => {
                            // Check if image is loaded and visible
                            if (img.complete && img.naturalHeight > 50) {
                                loadedMedia++;
                            }
                        });
                        videos.forEach(v => {
                            if (v.readyState >= 2) loadedMedia++;  // HAVE_CURRENT_DATA or better
                        });
                        
                        // Page must have: loaded media, links/buttons, and text
                        return loadedMedia >= 5 && links.length > 20 && 
                               buttons.length > 5 && textContent.length > 1000;
                    }
                """)
                
                if not has_content:
                    # Page is still loading, skip this screenshot
                    print(f"   ⏭️  Skipping screenshot - page still loading")
                    return
            except:
                pass  # If check fails, continue with screenshot
            
            # Take screenshot in memory to check if state changed
            screenshot_bytes = await current_page.screenshot(full_page=True)
            current_image = Image.open(io.BytesIO(screenshot_bytes))
            current_hash = imagehash.average_hash(current_image)
            
            # Check if this is a significant change
            is_significant = False
            if last_screenshot_hash[0] is None:
                # First screenshot is always significant (after login)
                is_significant = True
            else:
                # Calculate hash difference (lower = more similar)
                hash_diff = current_hash - last_screenshot_hash[0]
                # Lower value = more screenshots, Higher value = fewer screenshots
                # Threshold 8 = only major UI changes (new pages, modals, search results)
                if hash_diff > 6:
                    is_significant = True
            
            if is_significant:
                screenshot_counter[0] += 1
                screenshot_path = screenshots_dir / f"step_{screenshot_counter[0]:02d}.png"
                
                # Save the screenshot
                with open(screenshot_path, 'wb') as f:
                    f.write(screenshot_bytes)
                
                significant_screenshots.append(screenshot_path)
                last_screenshot_hash[0] = current_hash
                
                # Extract action description
                action_desc = ""
                if hasattr(action, 'extracted_content'):
                    action_desc = action.extracted_content
                elif hasattr(action, '__str__'):
                    action_desc = str(action)
                
                print(f"📸 Captured state change {screenshot_counter[0]}: {action_desc[:60]}...")
            
        except Exception as e:
            print(f"⚠ Could not process screenshot: {e}")
    
    # Create task description for the agent
    login_instruction = ""
    if requires_auth:
        login_instruction = """
IMPORTANT - LOGIN HANDLING:
- If you see a login page, WAIT and do nothing (the system will pause for manual login)
- After seeing a login page, just wait for the page to change
- DO NOT attempt to fill in login credentials
"""
    
    modified_task = f"""Navigate to {app_url} and {task}.

CRITICAL INSTRUCTIONS:
1. Go to {app_url} (if not already there)
2. Close any blocking modals, popups, or dialogs FIRST before proceeding
3. Perform the task: {task}
4. Be DECISIVE - once you've demonstrated the key steps, STOP immediately
5. DO NOT repeat the same action more than twice
6. If an action fails, try a different approach immediately{login_instruction}

COMPLETION CRITERIA - You are NOT done until:
- For "search" tasks: 
  * Type the search query into the search box
  * Press Enter key (preferred) OR click the Search button
  * WAIT for the URL to change and results page to load
  * VERIFY you can see actual search results (videos/items matching your query)
  * The page should look COMPLETELY DIFFERENT from the homepage
- For "create" tasks: Form is filled AND submit/create button is visible in viewport (don't click it)
- For "filter" tasks: Filters are applied and results shown
- For "find" tasks: The target content is visible
- For "join/navigate" tasks: Successfully reached the destination

CRITICAL FOR SEARCH TASKS:
- After typing the query, you MUST press Enter or click Search
- If you only typed but didn't submit, the task is INCOMPLETE
- Search results will show on a NEW page with matching videos/content
- The homepage feed is NOT search results - you need to submit the search
- DO NOT mark as done until you see the results page

The goal is to DEMONSTRATE the workflow efficiently, not to complete every minor detail."""
    
    # For auth sites: Open browser first, then pause for manual login
    if requires_auth:
        print("\n" + "="*70)
        print("🔐 IMPORTANT: THIS SITE REQUIRES MANUAL LOGIN")
        print("="*70)
        print("Opening browser now...")
        print("="*70 + "\n")
        
        # Start the browser and navigate to the URL
        await browser.start()
        print(f"🌐 Navigating to {app_url}...")
        await browser.navigate_to(app_url)
        await asyncio.sleep(3)  # Let page load
        
        print("\n" + "="*70)
        print("✅ Browser is now open!")
        print("\nOn FIRST RUN:")
        print(f"  1. Log in to {app_url} in the Chromium browser window above")
        print("  2. Complete the login process (including 2FA if needed)")
        print("  3. Come back here and press ENTER to start the agent")
        print("\nOn SUBSEQUENT RUNS:")
        print("  - Your login session will be automatically saved")
        print("  - Just press ENTER to continue (no need to log in again)")
        print("\n💡 Tip: The browser profile is saved in ./browser_profile/")
        print("   Delete this folder if you want to clear saved sessions.")
        print("="*70 + "\n")
        
        # Block until user is ready
        await asyncio.get_event_loop().run_in_executor(None, input, "Press ENTER when you're logged in and ready to continue...")
        print("\n✓ Starting agent...\n")
        await asyncio.sleep(1)
    
    # Step counter for clean logging
    step_counter = [0]
    
    # Create a cleaner step callback for user-friendly output
    async def clean_step_logger(state, action, step):
        """Log only essential step information in a clean format."""
        step_counter[0] = step
        
        # Extract action type and target
        action_str = str(action)
        if 'click' in action_str.lower():
            print(f"  Step {step}: 🖱️  Clicking element...")
        elif 'input' in action_str.lower() or 'type' in action_str.lower():
            print(f"  Step {step}: ⌨️  Typing text...")
        elif 'navigate' in action_str.lower():
            print(f"  Step {step}: 🌐 Navigating...")
        elif 'wait' in action_str.lower():
            print(f"  Step {step}: ⏳ Waiting...")
        elif 'done' in action_str.lower():
            print(f"  Step {step}: ✅ Task completed!")
        else:
            print(f"  Step {step}: 🔧 {action_str[:50]}...")
        
        # Call the screenshot callback
        await save_step_callback(state, action, step)
    
    # Create agent with callback
    agent = Agent(
        task=modified_task,
        llm=None,  # Will use OpenAI from OPENAI_API_KEY env var
        browser=browser,
        register_new_step_callback=clean_step_logger,
    )
    
    try:
        # Run the agent
        print("‣‣ Agent working on task:\n")
        history = await agent.run()
        print()
        
        # Capture MULTIPLE final screenshots to ensure we get the completed state
        print("\n📸 Capturing final state screenshots...")
        try:
            if hasattr(browser, '_context') and browser._context and browser._context.pages:
                current_page = browser._context.pages[0]
                
                # Wait for any final animations/loading to complete
                await asyncio.sleep(2.0)
                
                # Try to wait for network idle
                try:
                    await current_page.wait_for_load_state('networkidle', timeout=3000)
                except:
                    pass
                
                # Capture first final screenshot
                screenshot_bytes = await current_page.screenshot(full_page=True)
                current_image = Image.open(io.BytesIO(screenshot_bytes))
                current_hash = imagehash.average_hash(current_image)
                
                # Check if final state is different from last captured
                if last_screenshot_hash[0] is None or (current_hash - last_screenshot_hash[0]) > 5:
                    screenshot_counter[0] += 1
                    screenshot_path = screenshots_dir / f"step_{screenshot_counter[0]:02d}.png"
                    with open(screenshot_path, 'wb') as f:
                        f.write(screenshot_bytes)
                    print(f"   ✓ Captured final state {screenshot_counter[0]}")
                    last_screenshot_hash[0] = current_hash
                
                # Wait a bit more and capture another final screenshot
                # (in case search results or final content is still loading)
                await asyncio.sleep(3.0)
                screenshot_bytes_2 = await current_page.screenshot(full_page=True)
                current_image_2 = Image.open(io.BytesIO(screenshot_bytes_2))
                current_hash_2 = imagehash.average_hash(current_image_2)
                
                # Check if this second screenshot is different
                if (current_hash_2 - current_hash) > 5:
                    screenshot_counter[0] += 1
                    screenshot_path_2 = screenshots_dir / f"step_{screenshot_counter[0]:02d}.png"
                    with open(screenshot_path_2, 'wb') as f:
                        f.write(screenshot_bytes_2)
                    print(f"   ✓ Captured additional final state {screenshot_counter[0]}")
                    
        except Exception as e:
            print(f"   ⚠ Could not capture final state: {e}")
        
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

