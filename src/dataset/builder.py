"""
Dataset builder for organizing and saving workflow data.
"""
import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import shutil


class DatasetBuilder:
    """Builds organized datasets from captured workflows."""
    
    def __init__(self, base_dir: str = "dataset"):
        """
        Initialize dataset builder.
        
        Args:
            base_dir: Base directory for dataset
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
    
    def save_workflow(
        self,
        app_name: str,
        task_name: str,
        task_query: str,
        captured_states: List[Dict[str, Any]],
        temp_screenshots_dir: str = "temp_screenshots"
    ) -> str:
        """
        Save a complete workflow to the dataset.
        
        Args:
            app_name: Name of the application
            task_name: Name of the task
            task_query: Original task query
            captured_states: List of captured states with metadata
            temp_screenshots_dir: Directory containing temporary screenshots
            
        Returns:
            Path to the created task directory
        """
        # Create directory structure
        app_dir = self.base_dir / app_name.lower()
        task_dir = app_dir / task_name
        screenshots_dir = task_dir / "screenshots"
        
        screenshots_dir.mkdir(exist_ok=True, parents=True)
        
        # Copy and rename screenshots
        temp_dir = Path(temp_screenshots_dir)
        screenshot_mapping = {}
        
        for i, state in enumerate(captured_states, start=1):
            old_path = Path(state['screenshot'])
            if old_path.exists():
                # Create clean filename
                description_slug = state.get('description', 'state').replace(' ', '_').lower()
                description_slug = ''.join(c for c in description_slug if c.isalnum() or c == '_')[:50]
                new_filename = f"{i:02d}_{description_slug}.png"
                new_path = screenshots_dir / new_filename
                
                # Copy file
                shutil.copy2(old_path, new_path)
                screenshot_mapping[str(old_path)] = str(new_path)
                
                # Update state with new path
                state['screenshot'] = str(new_path.relative_to(task_dir))
        
        # Create metadata
        metadata = {
            "task_name": task_name,
            "task_query": task_query,
            "app_name": app_name,
            "timestamp": datetime.now().isoformat(),
            "num_states": len(captured_states),
            "states": captured_states
        }
        
        # Save metadata JSON
        metadata_path = task_dir / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"✓ Saved workflow to: {task_dir}")
        print(f"  - {len(captured_states)} states")
        print(f"  - {len(screenshot_mapping)} screenshots")
        
        return str(task_dir)
    
    def get_all_workflows(self) -> List[Dict[str, Any]]:
        """
        Get metadata for all workflows in the dataset.
        
        Returns:
            List of workflow metadata dictionaries
        """
        workflows = []
        
        for app_dir in self.base_dir.iterdir():
            if not app_dir.is_dir():
                continue
            
            for task_dir in app_dir.iterdir():
                if not task_dir.is_dir():
                    continue
                
                metadata_path = task_dir / "metadata.json"
                if metadata_path.exists():
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                        metadata['path'] = str(task_dir.relative_to(self.base_dir))
                        workflows.append(metadata)
        
        return workflows
    
    def generate_dataset_summary(self) -> Dict[str, Any]:
        """
        Generate a summary of the entire dataset.
        
        Returns:
            Dictionary with dataset statistics
        """
        workflows = self.get_all_workflows()
        
        # Group by app
        apps = {}
        for workflow in workflows:
            app_name = workflow['app_name']
            if app_name not in apps:
                apps[app_name] = []
            apps[app_name].append(workflow)
        
        # Calculate statistics
        total_states = sum(w['num_states'] for w in workflows)
        
        summary = {
            "total_workflows": len(workflows),
            "total_states_captured": total_states,
            "apps": {},
            "generated_at": datetime.now().isoformat()
        }
        
        for app_name, app_workflows in apps.items():
            summary['apps'][app_name] = {
                "num_workflows": len(app_workflows),
                "total_states": sum(w['num_states'] for w in app_workflows),
                "workflows": [
                    {
                        "task_name": w['task_name'],
                        "task_query": w['task_query'],
                        "num_states": w['num_states'],
                        "path": w['path']
                    }
                    for w in app_workflows
                ]
            }
        
        return summary
    
    def save_dataset_summary(self) -> str:
        """
        Save dataset summary to README.
        
        Returns:
            Path to the saved summary file
        """
        summary = self.generate_dataset_summary()
        
        # Save JSON version
        summary_json_path = self.base_dir / "summary.json"
        with open(summary_json_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"✓ Saved dataset summary to: {summary_json_path}")
        return str(summary_json_path)

