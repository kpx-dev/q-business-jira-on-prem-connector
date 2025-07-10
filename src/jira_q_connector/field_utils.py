"""
Field processing utilities for Jira data extraction
"""
import logging
import re
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

logger = logging.getLogger(__name__)


class FieldExtractor:
    """Utility class for extracting and processing Jira field values"""
    
    @staticmethod
    def safe_get_name(obj: Dict[str, Any]) -> str:
        """Safely extract name from an object"""
        if not obj or not isinstance(obj, dict):
            return ""
        return obj.get('name', obj.get('displayName', ''))
    
    @staticmethod
    def safe_get_email(obj: Dict[str, Any]) -> str:
        """Safely extract email from a user object"""
        if not obj or not isinstance(obj, dict):
            return ""
        return obj.get('emailAddress', obj.get('email', ''))
    
    @staticmethod
    def safe_get_description(obj: Dict[str, Any]) -> str:
        """Safely extract description from an object"""
        if not obj or not isinstance(obj, dict):
            return ""
        return obj.get('description', '')
    
    @staticmethod
    def extract_array_names(items: List[Dict[str, Any]]) -> List[str]:
        """Extract names from an array of objects"""
        if not items or not isinstance(items, list):
            return []
        
        names = []
        for item in items:
            if isinstance(item, dict):
                name = FieldExtractor.safe_get_name(item)
                if name:
                    names.append(name)
            elif isinstance(item, str):
                names.append(item)
        
        return names
    
    @staticmethod
    def extract_custom_field_value(field_value: Any) -> Optional[str]:
        """Extract a meaningful value from any custom field type"""
        if field_value is None:
            return None
        
        if isinstance(field_value, dict):
            # Try common value fields
            for key in ['value', 'name', 'displayName']:
                if key in field_value and field_value[key]:
                    return str(field_value[key])
            return None
        
        elif isinstance(field_value, list) and field_value:
            # Extract from array
            values = []
            for item in field_value:
                if isinstance(item, dict):
                    value = FieldExtractor.extract_custom_field_value(item)
                    if value:
                        values.append(value)
                elif isinstance(item, str):
                    values.append(item)
            return ', '.join(values) if values else None
        
        elif isinstance(field_value, (str, int, float)):
            value_str = str(field_value).strip()
            return value_str if value_str else None
        
        return None
    
    @staticmethod
    def extract_sprint_names(sprint_field: Any) -> List[str]:
        """Extract sprint names from Jira sprint field"""
        if not sprint_field:
            return []
        
        sprint_names = []
        
        if isinstance(sprint_field, list):
            for sprint in sprint_field:
                if isinstance(sprint, str):
                    # Extract sprint name from string format
                    match = re.search(r'name=([^,\]]+)', sprint)
                    if match:
                        sprint_names.append(match.group(1))
                    else:
                        sprint_names.append(sprint)
                elif isinstance(sprint, dict) and sprint.get('name'):
                    sprint_names.append(sprint['name'])
        
        elif isinstance(sprint_field, str):
            sprint_names.append(sprint_field)
        
        return sprint_names
    
    @staticmethod
    def format_time_estimate(seconds: Optional[int]) -> str:
        """Format time estimate in seconds to human readable format"""
        if not seconds or not isinstance(seconds, int):
            return ""
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m"
        else:
            return f"{seconds}s"
    
    @staticmethod
    def create_attribute(name: str, value: Any, is_date: bool = False) -> Optional[Dict[str, Any]]:
        """Create a Q Business document attribute"""
        if value is None:
            return None
        
        attr = {'name': name}
        
        if is_date and isinstance(value, (str, datetime)):
            if isinstance(value, str):
                attr['value'] = {'dateValue': value}
            else:
                attr['value'] = {'dateValue': value.isoformat()}
        elif isinstance(value, bool):
            attr['value'] = {'stringValue': 'true' if value else 'false'}
        elif isinstance(value, (int, float)):
            attr['value'] = {'longValue': int(value)}
        elif isinstance(value, list):
            if value:  # Only add non-empty lists
                attr['value'] = {'stringListValue': [str(v) for v in value]}
        else:
            value_str = str(value).strip()
            if value_str:  # Only add non-empty strings
                attr['value'] = {'stringValue': value_str}
        
        return attr if 'value' in attr else None


class ContentBuilder:
    """Utility class for building document content"""
    
    def __init__(self):
        self.parts = []
    
    def add_field(self, label: str, value: Any, condition: bool = True) -> 'ContentBuilder':
        """Add a field to the content if condition is met"""
        if condition and value:
            if isinstance(value, list):
                if value:  # Only add non-empty lists
                    self.parts.append(f"{label}: {', '.join(str(v) for v in value)}")
            else:
                self.parts.append(f"{label}: {value}")
        return self
    
    def add_section(self, title: str, content: str) -> 'ContentBuilder':
        """Add a section with title and content"""
        if content:
            self.parts.append(f"{title}:\n{content}")
        return self
    
    def add_custom_fields(self, fields: Dict[str, Any], skip_fields: List[str] = None) -> 'ContentBuilder':
        """Add custom fields to content"""
        skip_fields = skip_fields or []
        
        for field_key, field_value in fields.items():
            if (field_key.startswith('customfield_') and 
                field_value is not None and 
                field_key not in skip_fields):
                
                value = FieldExtractor.extract_custom_field_value(field_value)
                if value:
                    self.parts.append(f"Custom Field {field_key}: {value}")
        
        return self
    
    def build(self) -> str:
        """Build the final content string"""
        return '\n\n'.join(self.parts) 