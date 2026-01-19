"""
Project management for Installer Creator Pro
"""

import json
import os
import configparser
from datetime import datetime
from typing import List
from .models import ProjectConfig

class ProjectManager:
    """Manages project loading, saving, and recent projects"""
    
    @staticmethod
    def load_project(filepath: str) -> ProjectConfig:
        """Load project from file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return ProjectConfig.from_dict(data)
    
    @staticmethod
    def save_project(filepath: str, project: ProjectConfig):
        """Save project to file"""
        project.modified = datetime.now().isoformat()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(project.to_dict(), f, indent=2, ensure_ascii=False)
    
    @staticmethod
    def load_recent_projects() -> List[str]:
        """Load recent projects from settings"""
        try:
            config = configparser.ConfigParser()
            config.read('settings.ini')
            
            if 'Recent' in config:
                recent = config['Recent'].get('projects', '').split('|')
                return [p for p in recent if p and os.path.exists(p)]
        except:
            pass
        return []
    
    @staticmethod
    def save_recent_projects(projects: List[str]):
        """Save recent projects to settings"""
        try:
            config = configparser.ConfigParser()
            config['Recent'] = {'projects': '|'.join(projects[:10])}
            
            with open('settings.ini', 'w') as f:
                config.write(f)
        except:
            pass