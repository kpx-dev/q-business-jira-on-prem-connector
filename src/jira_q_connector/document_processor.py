"""
Simplified document processor for converting Jira issues to Amazon Q Business documents
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import html
import re

from .field_utils import FieldExtractor, ContentBuilder

logger = logging.getLogger(__name__)


class JiraDocumentProcessor:
    """Simplified processor for Jira issues into Q Business compatible documents"""
    
    def __init__(self, include_comments: bool = True, include_history: bool = False):
        self.include_comments = include_comments
        self.include_history = include_history
    
    def process_issue(self, issue: Dict[str, Any], execution_id: str = None) -> Dict[str, Any]:
        """Convert a Jira issue to Q Business document format"""
        try:
            fields = issue.get('fields', {})
            key = issue.get('key', '')
            
            # Extract basic information
            title = f"{key}: {fields.get('summary', 'No title')}"
            description = self._extract_description(fields)
            
            # Build document content using ContentBuilder
            builder = ContentBuilder()
            builder.add_field("Issue Key", key)
            builder.add_field("Title", fields.get('summary', 'No title'))
            
            if description:
                builder.add_section("Description", description)
            
            # Add metadata content
            metadata_parts = self._extract_metadata_content(fields)
            builder.parts.extend(metadata_parts)
            
            # Add comments if enabled
            if self.include_comments:
                comments_content = self._extract_comments_content(fields)
                if comments_content:
                    builder.add_section("Comments", comments_content)
            
            # Add change history if enabled  
            if self.include_history and 'changelog' in issue:
                history_content = self._extract_history_content(issue['changelog'])
                if history_content:
                    builder.add_section("Change History", history_content)
            
            # Create document attributes
            attributes = self._create_document_attributes(issue, fields, execution_id)
            
            # Generate document URI
            base_url = self._extract_base_url_from_self_link(issue.get('self', ''))
            doc_uri = f"{base_url}/browse/{key}" if base_url else f"jira://issue/{key}"
            
            # Create Q Business document
            document = {
                'id': f"jira-issue-{key}",
                'title': title,
                'content': {
                    'blob': builder.build()
                },
                'attributes': attributes,
                'contentType': 'PLAIN_TEXT'
            }
            
            return document
            
        except Exception as e:
            logger.error(f"Failed to process issue {key}: {e}")
            return None
    
    def _extract_description(self, fields: Dict[str, Any]) -> str:
        """Extract and clean description text"""
        description = fields.get('description')
        if not description:
            return ""
        
        if isinstance(description, dict):
            return self._extract_text_from_adf(description)
        elif isinstance(description, str):
            return self._clean_html_text(description)
        
        return str(description)
    
    def _extract_text_from_adf(self, adf_content: Dict[str, Any]) -> str:
        """Extract text from Atlassian Document Format (ADF)"""
        def extract_text_recursive(node):
            if isinstance(node, dict):
                if node.get('type') == 'text':
                    return node.get('text', '')
                
                if 'content' in node:
                    text_parts = []
                    for child in node['content']:
                        child_text = extract_text_recursive(child)
                        if child_text:
                            text_parts.append(child_text)
                    return ' '.join(text_parts)
                
            elif isinstance(node, list):
                return ' '.join(extract_text_recursive(item) for item in node)
            
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
        """Extract metadata as searchable content using simplified approach"""
        builder = ContentBuilder()
        
        # Core issue information
        self._add_core_fields(builder, fields)
        
        # People and dates
        self._add_people_fields(builder, fields)
        
        # Content and structure  
        self._add_content_fields(builder, fields)
        
        # Relationships and links
        self._add_relationship_fields(builder, fields)
        
        # Progress and tracking
        self._add_tracking_fields(builder, fields)
        
        # Agile fields
        self._add_agile_fields(builder, fields)
        
        # Custom fields
        self._add_custom_fields(builder, fields)
        
        return builder.parts
    
    def _add_core_fields(self, builder: ContentBuilder, fields: Dict[str, Any]) -> None:
        """Add core issue fields"""
        status = fields.get('status', {})
        builder.add_field("Status", FieldExtractor.safe_get_name(status))
        builder.add_field("Status Description", FieldExtractor.safe_get_description(status))
        
        priority = fields.get('priority', {})
        builder.add_field("Priority", FieldExtractor.safe_get_name(priority))
        
        issuetype = fields.get('issuetype', {})
        builder.add_field("Issue Type", FieldExtractor.safe_get_name(issuetype))
        
        project = fields.get('project', {})
        if project:
            project_name = f"{FieldExtractor.safe_get_name(project)} ({project.get('key', '')})"
            builder.add_field("Project", project_name)
        
        resolution = fields.get('resolution', {})
        if resolution:
            builder.add_field("Resolution", FieldExtractor.safe_get_name(resolution))
        else:
            builder.add_field("Resolution", "Unresolved")
    
    def _add_people_fields(self, builder: ContentBuilder, fields: Dict[str, Any]) -> None:
        """Add people-related fields"""
        assignee = fields.get('assignee', {})
        if assignee:
            builder.add_field("Assignee", FieldExtractor.safe_get_name(assignee))
            builder.add_field("Assignee Email", FieldExtractor.safe_get_email(assignee))
        else:
            builder.add_field("Assignee", "Unassigned")
        
        reporter = fields.get('reporter', {})
        builder.add_field("Reporter", FieldExtractor.safe_get_name(reporter))
        
        builder.add_field("Due Date", fields.get('duedate'))
        builder.add_field("Resolution Date", fields.get('resolutiondate'))
    
    def _add_content_fields(self, builder: ContentBuilder, fields: Dict[str, Any]) -> None:
        """Add content and categorization fields"""
        builder.add_field("Labels", fields.get('labels', []))
        
        components = fields.get('components', [])
        builder.add_field("Components", FieldExtractor.extract_array_names(components))
        
        fix_versions = fields.get('fixVersions', [])
        builder.add_field("Fix Versions", FieldExtractor.extract_array_names(fix_versions))
        
        environment = fields.get('environment')
        if environment:
            env_text = self._clean_html_text(environment) if isinstance(environment, str) else str(environment)
            builder.add_field("Environment", env_text)
    
    def _add_relationship_fields(self, builder: ContentBuilder, fields: Dict[str, Any]) -> None:
        """Add relationship and linking fields"""
        # Attachments
        attachments = fields.get('attachment', [])
        if attachments:
            attachment_names = [att.get('filename') for att in attachments if att.get('filename')]
            builder.add_field("Attachments", attachment_names)
        
        # Subtasks
        subtasks = fields.get('subtasks', [])
        if subtasks:
            subtask_keys = [task.get('key') for task in subtasks if task.get('key')]
            builder.add_field("Subtasks", subtask_keys)
        
        # Parent
        parent = fields.get('parent', {})
        if parent and parent.get('key'):
            builder.add_field("Parent Issue", parent['key'])
        
        # Issue links (simplified)
        issuelinks = fields.get('issuelinks', [])
        if issuelinks:
            link_keys = []
            for link in issuelinks:
                if 'inwardIssue' in link:
                    link_keys.append(link['inwardIssue'].get('key'))
                if 'outwardIssue' in link:
                    link_keys.append(link['outwardIssue'].get('key'))
            if link_keys:
                builder.add_field("Linked Issues", [k for k in link_keys if k])
    
    def _add_tracking_fields(self, builder: ContentBuilder, fields: Dict[str, Any]) -> None:
        """Add time tracking and progress fields"""
        timetracking = fields.get('timetracking', {})
        builder.add_field("Original Estimate", timetracking.get('originalEstimate'))
        builder.add_field("Time Spent", timetracking.get('timeSpent'))
        
        votes = fields.get('votes', {})
        if votes.get('votes', 0) > 0:
            builder.add_field("Votes", votes['votes'])
        
        watches = fields.get('watches', {})
        if watches.get('watchCount', 0) > 0:
            builder.add_field("Watchers", watches['watchCount'])
    
    def _add_agile_fields(self, builder: ContentBuilder, fields: Dict[str, Any]) -> None:
        """Add common Agile fields"""
        # Epic Link
        epic_link = fields.get('customfield_10014') or fields.get('epicLink')
        builder.add_field("Epic Link", epic_link)
        
        # Story Points
        story_points = fields.get('customfield_10016') or fields.get('storyPoints')
        builder.add_field("Story Points", story_points)
        
        # Sprint
        sprint = fields.get('customfield_10020') or fields.get('sprint')
        sprint_names = FieldExtractor.extract_sprint_names(sprint)
        builder.add_field("Sprint", sprint_names)
        
        # Team
        team = fields.get('customfield_10021') or fields.get('team')
        team_name = FieldExtractor.extract_custom_field_value(team)
        builder.add_field("Team", team_name)
    
    def _add_custom_fields(self, builder: ContentBuilder, fields: Dict[str, Any]) -> None:
        """Add other custom fields"""
        known_custom_fields = {
            'customfield_10014', 'customfield_10015', 'customfield_10016', 
            'customfield_10017', 'customfield_10018', 'customfield_10019',
            'customfield_10020', 'customfield_10021'
        }
        builder.add_custom_fields(fields, skip_fields=list(known_custom_fields))
    
    def _extract_comments_content(self, fields: Dict[str, Any]) -> str:
        """Extract comments as searchable content"""
        comment_data = fields.get('comment', {})
        comments = comment_data.get('comments', []) if isinstance(comment_data, dict) else []
        
        if not comments:
            return ""
        
        comment_texts = []
        for comment in comments:
            author = comment.get('author', {}).get('displayName', 'Unknown')
            body = comment.get('body', '')
            
            if isinstance(body, dict):
                body = self._extract_text_from_adf(body)
            elif isinstance(body, str):
                body = self._clean_html_text(body)
            
            if body:
                comment_texts.append(f"[{author}]: {body}")
        
        return '\n'.join(comment_texts)
    
    def _extract_history_content(self, changelog: Dict[str, Any]) -> str:
        """Extract change history as searchable content"""
        histories = changelog.get('histories', [])
        
        if not histories:
            return ""
        
        history_texts = []
        for history in histories:
            author = history.get('author', {}).get('displayName', 'Unknown')
            changes = []
            
            for item in history.get('items', []):
                field = item.get('field', '')
                from_val = item.get('fromString', '')
                to_val = item.get('toString', '')
                
                if field:
                    changes.append(f"{field}: '{from_val}' → '{to_val}'")
            
            if changes:
                history_texts.append(f"[{author}]: {'; '.join(changes)}")
        
        return '\n'.join(history_texts)
    
    def _create_document_attributes(self, issue: Dict[str, Any], fields: Dict[str, Any], execution_id: str = None) -> List[Dict[str, Any]]:
        """Create document attributes for Q Business using simplified approach"""
        attributes = []
        
        # Source URI (required)
        base_url = self._extract_base_url_from_self_link(issue.get('self', ''))
        doc_uri = f"{base_url}/browse/{issue.get('key', '')}" if base_url else f"jira://issue/{issue.get('key', '')}"
        attributes.append(FieldExtractor.create_attribute('_source_uri', doc_uri))
        
        # Core attributes
        attributes.extend(filter(None, [
            FieldExtractor.create_attribute('jira_issue_key', issue.get('key')),
            FieldExtractor.create_attribute('jira_issue_id', issue.get('id')),
            FieldExtractor.create_attribute('jira_project', fields.get('project', {}).get('key')),
            FieldExtractor.create_attribute('jira_project_name', fields.get('project', {}).get('name')),
            FieldExtractor.create_attribute('jira_issue_type', FieldExtractor.safe_get_name(fields.get('issuetype', {}))),
            FieldExtractor.create_attribute('jira_status', FieldExtractor.safe_get_name(fields.get('status', {}))),
            FieldExtractor.create_attribute('jira_priority', FieldExtractor.safe_get_name(fields.get('priority', {}))),
            FieldExtractor.create_attribute('jira_resolution', FieldExtractor.safe_get_name(fields.get('resolution', {}))),
            FieldExtractor.create_attribute('jira_assignee', FieldExtractor.safe_get_name(fields.get('assignee', {}))),
            FieldExtractor.create_attribute('jira_assignee_email', FieldExtractor.safe_get_email(fields.get('assignee', {}))),
            FieldExtractor.create_attribute('jira_reporter', FieldExtractor.safe_get_name(fields.get('reporter', {}))),
            FieldExtractor.create_attribute('jira_created', fields.get('created'), is_date=True),
            FieldExtractor.create_attribute('jira_updated', fields.get('updated'), is_date=True),
            FieldExtractor.create_attribute('jira_due_date', fields.get('duedate'), is_date=True),
            FieldExtractor.create_attribute('jira_labels', fields.get('labels', [])),
            FieldExtractor.create_attribute('jira_components', FieldExtractor.extract_array_names(fields.get('components', []))),
            FieldExtractor.create_attribute('jira_fix_versions', FieldExtractor.extract_array_names(fields.get('fixVersions', []))),
        ]))
        
        # Agile attributes
        attributes.extend(filter(None, [
            FieldExtractor.create_attribute('jira_epic_link', fields.get('customfield_10014')),
            FieldExtractor.create_attribute('jira_story_points', fields.get('customfield_10016')),
            FieldExtractor.create_attribute('jira_sprint', FieldExtractor.extract_sprint_names(fields.get('customfield_10020'))),
            FieldExtractor.create_attribute('jira_team', FieldExtractor.extract_custom_field_value(fields.get('customfield_10021'))),
        ]))
        
        # Engagement metrics
        votes = fields.get('votes', {})
        if votes.get('votes', 0) > 0:
            attributes.append(FieldExtractor.create_attribute('jira_votes', votes['votes']))
        
        watches = fields.get('watches', {})
        if watches.get('watchCount', 0) > 0:
            attributes.append(FieldExtractor.create_attribute('jira_watchers', watches['watchCount']))
        
        # Attachment count
        attachments = fields.get('attachment', [])
        if attachments:
            attributes.append(FieldExtractor.create_attribute('jira_attachment_count', len(attachments)))
            attachment_names = [att.get('filename') for att in attachments if att.get('filename')]
            if attachment_names:
                attributes.append(FieldExtractor.create_attribute('jira_attachment_names', attachment_names))
        
        return [attr for attr in attributes if attr is not None]
    
    def _extract_base_url_from_self_link(self, self_url: str) -> str:
        """Extract base URL from Jira self link"""
        if not self_url:
            return ""
        
        match = re.match(r'(https?://[^/]+)', self_url)
        return match.group(1) if match else ""
    
    def create_batch_documents(self, issues: List[Dict[str, Any]], execution_id: str = None) -> List[Dict[str, Any]]:
        """Process multiple issues into Q Business documents"""
        documents = []
        
        for issue in issues:
            try:
                doc = self.process_issue(issue, execution_id)
                if doc:
                    documents.append(doc)
            except Exception as e:
                logger.error(f"Failed to process issue {issue.get('key', 'unknown')}: {e}")
                continue
        
        logger.info(f"Processed {len(documents)} documents from {len(issues)} issues")
        return documents 