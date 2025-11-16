"""
Documentation generator for creating markdown documentation.
"""
import json
from pathlib import Path
from typing import Dict, Any, List


class DocsGenerator:
    """Generates markdown documentation for datasets."""
    
    def __init__(self, dataset_dir: str = "dataset"):
        """
        Initialize docs generator.
        
        Args:
            dataset_dir: Base dataset directory
        """
        self.dataset_dir = Path(dataset_dir)
    
    def _generate_step_title(self, step_num: int, action: str, description: str) -> str:
        """Generate a clean, descriptive title for a step."""
        # Try to extract meaningful action from the action string
        action_lower = action.lower()
        
        # Common patterns to create meaningful titles
        if 'click' in action_lower:
            if 'search' in action_lower or 'input' in action_lower:
                return "Enter Search Query"
            elif 'button' in action_lower:
                return "Click Action Button"
            elif 'link' in action_lower:
                return "Navigate to Page"
            else:
                return "Click Element"
        elif 'type' in action_lower or 'input' in action_lower:
            return "Enter Information"
        elif 'go to' in action_lower or 'navigate' in action_lower:
            return "Navigate to Page"
        elif 'scroll' in action_lower:
            return "Scroll Page"
        elif 'wait' in action_lower:
            return "Wait for Page Load"
        elif 'search' in action_lower:
            return "Search"
        elif 'open' in action_lower:
            return "Open Application"
        elif 'result' in action_lower or 'display' in action_lower:
            return "View Results"
        elif 'complete' in action_lower or 'done' in action_lower:
            return "Task Completed"
        else:
            # Fall back to a generic but numbered title
            return f"Step {step_num}"
    
    def _clean_action_description(self, action: str) -> str:
        """Extract clean, human-readable description from action string."""
        if not action:
            return ""
        
        # Check if it's an ActionResult verbose output
        if action.startswith('[ActionResult('):
            # Try to extract just the extracted_content or long_term_memory
            import re
            
            # Try to find extracted_content
            match = re.search(r"extracted_content='([^']*)'", action)
            if match:
                content = match.group(1)
                # Skip if it's an error or too verbose
                if content and not content.startswith('Error:') and len(content) < 150:
                    return content
            
            # Try to find long_term_memory
            match = re.search(r"long_term_memory='([^']*)'", action)
            if match:
                content = match.group(1)
                if content and not content.startswith('Error:') and len(content) < 150:
                    return content
            
            # If we can't extract anything useful, return empty
            return ""
        
        # If it's already clean text, return it
        if len(action) < 200 and '[' not in action and '(' not in action:
            return action
        
        return ""
    
    def generate_workflow_markdown(
        self,
        task_dir: str,
        metadata: Dict[str, Any]
    ) -> str:
        """
        Generate markdown documentation for a single workflow.
        
        Args:
            task_dir: Path to the task directory
            metadata: Workflow metadata
            
        Returns:
            Path to the generated markdown file
        """
        task_path = Path(task_dir)
        
        # Start markdown content - Create a clean, professional title
        task_title = metadata['task_query'].strip()
        if not task_title.endswith('?'):
            task_title = metadata['task_name'].replace('_', ' ').title()
        
        md_content = f"""# {task_title}

**Application:** {metadata['app_name'].title()}

---

## Overview

This guide demonstrates **{task_title.lower()}** through {metadata['num_states']} step-by-step screenshots.

## Steps

"""
        
        # Add each state with descriptive titles
        for state in metadata['states']:
            step_num = state['step']
            description = state.get('description', 'UI State')
            action = state.get('action_taken', '')
            screenshot_rel = state.get('screenshot', '')
            
            # Generate a clean step title from the action
            step_title = self._generate_step_title(step_num, action, description)
            
            md_content += f"### {step_num}. {step_title}\n\n"
            
            # Add screenshot
            if screenshot_rel:
                md_content += f"![{step_title}]({screenshot_rel})\n\n"
            
            # Extract clean action description (remove ActionResult verbose output)
            clean_action = self._clean_action_description(action)
            if clean_action and len(clean_action) > 5:
                md_content += f"_{clean_action}_\n\n"
            
            md_content += "---\n\n"
        
        # Add metadata footer
        md_content += f"""## Metadata

- **Captured:** {metadata.get('timestamp', 'N/A')}
- **Total States:** {metadata['num_states']}
- **App:** {metadata['app_name']}

"""
        
        # Save markdown file
        md_path = task_path / "workflow.md"
        with open(md_path, 'w') as f:
            f.write(md_content)
        
        print(f"✓ Generated workflow documentation: {md_path}")
        return str(md_path)
    
    def generate_dataset_readme(self) -> str:
        """
        Generate main README for the dataset.
        
        Returns:
            Path to the generated README
        """
        # Load summary
        summary_path = self.dataset_dir / "summary.json"
        if not summary_path.exists():
            print("No summary.json found, generating basic README")
            summary = {
                "total_workflows": 0,
                "total_states_captured": 0,
                "apps": {}
            }
        else:
            with open(summary_path, 'r') as f:
                summary = json.load(f)
        
        # Generate README content
        md_content = f"""# AI UI Navigator Dataset

This dataset contains captured UI workflows for various web applications, demonstrating how to perform common tasks.

## Overview

- **Total Workflows:** {summary['total_workflows']}
- **Total UI States Captured:** {summary['total_states_captured']}
- **Applications:** {len(summary['apps'])}

## Dataset Structure

Each workflow is organized as follows:

```
dataset/
├── {app_name}/
│   ├── {task_name}/
│   │   ├── screenshots/
│   │   │   ├── 01_state_description.png
│   │   │   ├── 02_state_description.png
│   │   │   └── ...
│   │   ├── metadata.json
│   │   └── workflow.md
```

## Applications and Workflows

"""
        
        # Add each app
        for app_name, app_data in summary.get('apps', {}).items():
            md_content += f"### {app_name.title()}\n\n"
            md_content += f"**Total Workflows:** {app_data['num_workflows']}\n\n"
            md_content += f"**Total States:** {app_data['total_states']}\n\n"
            
            md_content += "#### Workflows:\n\n"
            
            for workflow in app_data['workflows']:
                task_name = workflow['task_name'].replace('_', ' ').title()
                task_query = workflow['task_query']
                num_states = workflow['num_states']
                path = workflow['path']
                
                md_content += f"- **{task_name}**\n"
                md_content += f"  - Query: _{task_query}_\n"
                md_content += f"  - States Captured: {num_states}\n"
                md_content += f"  - [View Workflow]({path}/workflow.md)\n\n"
            
            md_content += "\n"
        
        # Add explanation section
        md_content += """## About This Dataset

This dataset was generated by an AI agent that:

1. Receives natural language task queries (e.g., "How do I create a project?")
2. Uses GPT-4V to analyze screenshots and make navigation decisions
3. Automatically navigates the web application
4. Captures screenshots at each significant UI state
5. Generates documentation for each workflow

The goal is to demonstrate UI workflows that include non-URL states like modals, dropdowns, and forms that traditional URL-based scraping would miss.

## Dataset Usage

Each workflow includes:

- **screenshots/**: Numbered screenshots showing each UI state
- **metadata.json**: Structured data about each step
- **workflow.md**: Human-readable documentation with embedded images

## Methodology

The system uses:

- **Playwright** for browser automation
- **GPT-4V** for visual reasoning and action decisions
- **Image hashing** for state change detection
- **Vision-guided navigation** for generalizability across apps

This approach prioritizes generalizability over hardcoded selectors, making it adaptable to new applications and tasks.
"""
        
        # Save README
        readme_path = self.dataset_dir / "README.md"
        with open(readme_path, 'w') as f:
            f.write(md_content)
        
        print(f"✓ Generated dataset README: {readme_path}")
        return str(readme_path)
    
    def generate_all_docs(self):
        """Generate all documentation for the dataset."""
        print("\nGenerating documentation...")
        
        # Generate workflow docs for each task
        for app_dir in self.dataset_dir.iterdir():
            if not app_dir.is_dir() or app_dir.name.startswith('.'):
                continue
            
            for task_dir in app_dir.iterdir():
                if not task_dir.is_dir():
                    continue
                
                metadata_path = task_dir / "metadata.json"
                if metadata_path.exists():
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                    
                    self.generate_workflow_markdown(str(task_dir), metadata)
        
        # Generate main README
        self.generate_dataset_readme()
        
        print("✓ Documentation generation complete")

