"""
Document processor for converting Jira issues to Amazon Q Business documents
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import html
import re

logger = logging.getLogger(__name__)


class JiraDocumentProcessor:
    """Processes Jira issues into Q Business compatible documents"""
    
    def __init__(self, include_comments: bool = True, include_history: bool = False):
        self.include_comments = include_comments
        self.include_history = include_history
    
    def process_issue(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a Jira issue to Q Business document format"""
        try:
            fields = issue.get('fields', {})
            key = issue.get('key', '')
            
            # Extract basic information
            title = f"{key}: {fields.get('summary', 'No title')}"
            description = self._extract_description(fields)
            
            # Build document content
            content_parts = []
            
            # Add issue details
            content_parts.append(f"Issue Key: {key}")
            content_parts.append(f"Title: {fields.get('summary', 'No title')}")
            
            if description:
                content_parts.append(f"Description:\n{description}")
            
            # Add metadata as searchable content
            content_parts.extend(self._extract_metadata_content(fields))
            
            # Add comments if enabled
            if self.include_comments:
                comments_content = self._extract_comments_content(fields)
                if comments_content:
                    content_parts.append(comments_content)
            
            # Add change history if enabled
            if self.include_history and 'changelog' in issue:
                history_content = self._extract_history_content(issue['changelog'])
                if history_content:
                    content_parts.append(history_content)
            
            # Combine all content
            content = '\n\n'.join(content_parts)
            
            # Create document attributes
            attributes = self._create_document_attributes(issue, fields)
            
            # Generate document URI
            base_url = self._extract_base_url_from_self_link(issue.get('self', ''))
            doc_uri = f"{base_url}/browse/{key}" if base_url else f"jira://issue/{key}"
            
            # Create Q Business document
            document = {
                'id': f"jira-issue-{key}",
                'title': title,
                'content': {
                    'blob': content.encode('utf-8')
                },
                'attributes': attributes,
                'contentType': 'PLAIN_TEXT'
            }
            
            logger.debug(f"Processed issue {key} into document")
            return document
            
        except Exception as e:
            logger.error(f"Error processing issue {issue.get('key', 'unknown')}: {e}")
            raise
    
    def _extract_description(self, fields: Dict[str, Any]) -> str:
        """Extract and clean description text"""
        description = fields.get('description')
        if not description:
            return ""
        
        if isinstance(description, dict):
            # Handle ADF (Atlassian Document Format) content
            return self._extract_text_from_adf(description)
        elif isinstance(description, str):
            # Handle plain text or HTML
            return self._clean_html_text(description)
        
        return str(description)
    
    def _extract_text_from_adf(self, adf_content: Dict[str, Any]) -> str:
        """Extract text from Atlassian Document Format (ADF)"""
        def extract_text_recursive(node):
            if isinstance(node, dict):
                text_parts = []
                
                # Handle text nodes
                if node.get('type') == 'text':
                    return node.get('text', '')
                
                # Handle other node types
                if 'content' in node:
                    for child in node['content']:
                        child_text = extract_text_recursive(child)
                        if child_text:
                            text_parts.append(child_text)
                
                return ' '.join(text_parts)
            elif isinstance(node, list):
                return ' '.join(extract_text_recursive(item) for item in node)
            else:
                return str(node) if node else ''
        
        return extract_text_recursive(adf_content)
    
    def _clean_html_text(self, text: str) -> str:
        """Clean HTML and wiki markup from text"""
        if not text:
            return ""
        
        # Unescape HTML entities
        text = html.unescape(text)
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Clean up wiki markup (basic patterns)
        text = re.sub(r'\*([^*]+)\*', r'\1', text)  # Bold
        text = re.sub(r'_([^_]+)_', r'\1', text)    # Italic
        text = re.sub(r'\[([^|]+)\|([^\]]+)\]', r'\1 (\2)', text)  # Links
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _extract_metadata_content(self, fields: Dict[str, Any]) -> List[str]:
        """Extract metadata as searchable content"""
        content_parts = []
        
        # Status
        status = fields.get('status') or {}
        if status and isinstance(status, dict):
            content_parts.append(f"Status: {status.get('name', 'Unknown')}")
        
        # Priority
        priority = fields.get('priority') or {}
        if priority and isinstance(priority, dict):
            content_parts.append(f"Priority: {priority.get('name', 'Unknown')}")
        
        # Issue Type
        issuetype = fields.get('issuetype') or {}
        if issuetype and isinstance(issuetype, dict):
            content_parts.append(f"Issue Type: {issuetype.get('name', 'Unknown')}")
        
        # Project
        project = fields.get('project') or {}
        if project and isinstance(project, dict):
            content_parts.append(f"Project: {project.get('name', 'Unknown')} ({project.get('key', '')})")
        
        # Assignee
        assignee = fields.get('assignee') or {}
        if assignee and isinstance(assignee, dict):
            content_parts.append(f"Assignee: {assignee.get('displayName', 'Unknown')}")
        
        # Reporter
        reporter = fields.get('reporter') or {}
        if reporter and isinstance(reporter, dict):
            content_parts.append(f"Reporter: {reporter.get('displayName', 'Unknown')}")
        
        # Labels
        labels = fields.get('labels', [])
        if labels:
            content_parts.append(f"Labels: {', '.join(labels)}")
        
        # Components
        components = fields.get('components', [])
        if components:
            comp_names = [comp.get('name', '') for comp in components]
            content_parts.append(f"Components: {', '.join(comp_names)}")
        
        # Fix Versions
        fix_versions = fields.get('fixVersions', [])
        if fix_versions:
            version_names = [ver.get('name', '') for ver in fix_versions]
            content_parts.append(f"Fix Versions: {', '.join(version_names)}")
        
        # Environment
        environment = fields.get('environment')
        if environment:
            env_text = self._clean_html_text(environment) if isinstance(environment, str) else str(environment)
            if env_text:
                content_parts.append(f"Environment: {env_text}")
        
        return content_parts
    
    def _extract_comments_content(self, fields: Dict[str, Any]) -> str:
        """Extract comments as searchable content"""
        comment_data = fields.get('comment', {})
        comments = comment_data.get('comments', []) if isinstance(comment_data, dict) else []
        
        if not comments:
            return ""
        
        comment_parts = ["Comments:"]
        
        for comment in comments:
            author_info = comment.get('author') or {}
            author = author_info.get('displayName', 'Unknown') if isinstance(author_info, dict) else 'Unknown'
            created = comment.get('created', '')
            body = comment.get('body', '')
            
            # Clean comment body
            if isinstance(body, dict):
                body = self._extract_text_from_adf(body)
            elif isinstance(body, str):
                body = self._clean_html_text(body)
            
            if body:
                comment_parts.append(f"[{author} - {created}]: {body}")
        
        return '\n'.join(comment_parts)
    
    def _extract_history_content(self, changelog: Dict[str, Any]) -> str:
        """Extract change history as searchable content"""
        histories = changelog.get('histories', [])
        
        if not histories:
            return ""
        
        history_parts = ["Change History:"]
        
        for history in histories:
            author = history.get('author', {}).get('displayName', 'Unknown')
            created = history.get('created', '')
            
            changes = []
            for item in history.get('items', []):
                field = item.get('field', '')
                from_val = item.get('fromString', '')
                to_val = item.get('toString', '')
                
                if field and (from_val or to_val):
                    changes.append(f"{field}: '{from_val}' → '{to_val}'")
            
            if changes:
                history_parts.append(f"[{author} - {created}]: {'; '.join(changes)}")
        
        return '\n'.join(history_parts)
    
    def _create_document_attributes(self, issue: Dict[str, Any], fields: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create document attributes for Q Business"""
        attributes = []
        
        # Required _source_uri attribute
        base_url = self._extract_base_url_from_self_link(issue.get('self', ''))
        doc_uri = f"{base_url}/browse/{issue.get('key', '')}" if base_url else f"jira://issue/{issue.get('key', '')}"
        
        attributes.append({
            'name': '_source_uri',
            'value': {
                'stringValue': doc_uri
            }
        })
        
        # Issue key
        if issue.get('key'):
            attributes.append({
                'name': 'jira_issue_key',
                'value': {
                    'stringValue': issue['key']
                }
            })
        
        # Project
        project = fields.get('project') or {}
        if project and isinstance(project, dict) and project.get('key'):
            attributes.append({
                'name': 'jira_project',
                'value': {
                    'stringValue': project['key']
                }
            })
        
        # Issue type
        issuetype = fields.get('issuetype') or {}
        if issuetype and isinstance(issuetype, dict) and issuetype.get('name'):
            attributes.append({
                'name': 'jira_issue_type',
                'value': {
                    'stringValue': issuetype['name']
                }
            })
        
        # Status
        status = fields.get('status') or {}
        if status and isinstance(status, dict) and status.get('name'):
            attributes.append({
                'name': 'jira_status',
                'value': {
                    'stringValue': status['name']
                }
            })
        
        # Priority
        priority = fields.get('priority') or {}
        if priority and isinstance(priority, dict) and priority.get('name'):
            attributes.append({
                'name': 'jira_priority',
                'value': {
                    'stringValue': priority['name']
                }
            })
        
        # Assignee
        assignee = fields.get('assignee') or {}
        if assignee and isinstance(assignee, dict) and assignee.get('displayName'):
            attributes.append({
                'name': 'jira_assignee',
                'value': {
                    'stringValue': assignee['displayName']
                }
            })
        
        # Reporter
        reporter = fields.get('reporter') or {}
        if reporter and isinstance(reporter, dict) and reporter.get('displayName'):
            attributes.append({
                'name': 'jira_reporter',
                'value': {
                    'stringValue': reporter['displayName']
                }
            })
        
        # Created date
        if fields.get('created'):
            attributes.append({
                'name': 'jira_created',
                'value': {
                    'dateValue': self._parse_jira_date(fields['created'])
                }
            })
        
        # Updated date
        if fields.get('updated'):
            attributes.append({
                'name': 'jira_updated',
                'value': {
                    'dateValue': self._parse_jira_date(fields['updated'])
                }
            })
        
        # Labels
        labels = fields.get('labels', [])
        if labels:
            attributes.append({
                'name': 'jira_labels',
                'value': {
                    'stringListValue': labels
                }
            })
        
        return attributes
    
    def _extract_base_url_from_self_link(self, self_url: str) -> str:
        """Extract base URL from Jira self link"""
        if not self_url:
            return ""
        
        # Extract base URL from self link like "https://jira.company.com/rest/api/2/issue/12345"
        match = re.match(r'(https?://[^/]+)', self_url)
        return match.group(1) if match else ""
    
    def _parse_jira_date(self, date_str: str) -> datetime:
        """Parse Jira date string to datetime"""
        try:
            # Handle different Jira date formats
            formats = [
                '%Y-%m-%dT%H:%M:%S.%f%z',  # With timezone and microseconds
                '%Y-%m-%dT%H:%M:%S%z',     # With timezone
                '%Y-%m-%dT%H:%M:%S.%f',    # Without timezone, with microseconds
                '%Y-%m-%dT%H:%M:%S',       # Without timezone
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            
            # If none work, try parsing without format
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            
        except Exception as e:
            logger.warning(f"Could not parse date '{date_str}': {e}")
            return datetime.now()
    
    def create_batch_documents(self, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process multiple issues into Q Business documents"""
        documents = []
        
        for issue in issues:
            try:
                doc = self.process_issue(issue)
                if doc:
                    documents.append(doc)
            except Exception as e:
                logger.error(f"Failed to process issue {issue.get('key', 'unknown')}: {e}")
                continue
        
        logger.info(f"Processed {len(documents)} documents from {len(issues)} issues")
        return documents 