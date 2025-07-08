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
    
    def process_issue(self, issue: Dict[str, Any], execution_id: str = None) -> Dict[str, Any]:
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
            attributes = self._create_document_attributes(issue, fields, execution_id)
            
            # Generate document URI
            base_url = self._extract_base_url_from_self_link(issue.get('self', ''))
            doc_uri = f"{base_url}/browse/{key}" if base_url else f"jira://issue/{key}"
            
            # Create Q Business document
            document = {
                'id': f"jira-issue-{key}",
                'title': title,
                'content': {
                    'blob': content  # Raw content, not base64 encoded - Q Business API handles encoding internally
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
            if status.get('description'):
                content_parts.append(f"Status Description: {status['description']}")
        
        # Priority
        priority = fields.get('priority') or {}
        if priority and isinstance(priority, dict):
            content_parts.append(f"Priority: {priority.get('name', 'Unknown')}")
            if priority.get('description'):
                content_parts.append(f"Priority Description: {priority['description']}")
        
        # Issue Type
        issuetype = fields.get('issuetype') or {}
        if issuetype and isinstance(issuetype, dict):
            content_parts.append(f"Issue Type: {issuetype.get('name', 'Unknown')}")
            if issuetype.get('description'):
                content_parts.append(f"Issue Type Description: {issuetype['description']}")
        
        # Project
        project = fields.get('project') or {}
        if project and isinstance(project, dict):
            content_parts.append(f"Project: {project.get('name', 'Unknown')} ({project.get('key', '')})")
            if project.get('description'):
                content_parts.append(f"Project Description: {project['description']}")
            if project.get('projectCategory', {}).get('name'):
                content_parts.append(f"Project Category: {project['projectCategory']['name']}")
        
        # Assignee
        assignee = fields.get('assignee') or {}
        if assignee and isinstance(assignee, dict):
            content_parts.append(f"Assignee: {assignee.get('displayName', 'Unknown')}")
            if assignee.get('emailAddress'):
                content_parts.append(f"Assignee Email: {assignee['emailAddress']}")
        else:
            content_parts.append("Assignee: Unassigned")
        
        # Reporter
        reporter = fields.get('reporter') or {}
        if reporter and isinstance(reporter, dict):
            content_parts.append(f"Reporter: {reporter.get('displayName', 'Unknown')}")
            if reporter.get('emailAddress'):
                content_parts.append(f"Reporter Email: {reporter['emailAddress']}")
        
        # Creator (if different from reporter)
        creator = fields.get('creator') or {}
        if creator and isinstance(creator, dict) and creator.get('name') != reporter.get('name'):
            content_parts.append(f"Creator: {creator.get('displayName', 'Unknown')}")
        
        # Resolution
        resolution = fields.get('resolution') or {}
        if resolution and isinstance(resolution, dict):
            content_parts.append(f"Resolution: {resolution.get('name', 'Unknown')}")
            if resolution.get('description'):
                content_parts.append(f"Resolution Description: {resolution['description']}")
        else:
            content_parts.append("Resolution: Unresolved")
        
        # Labels
        labels = fields.get('labels', [])
        if labels:
            content_parts.append(f"Labels: {', '.join(labels)}")
        
        # Components
        components = fields.get('components', [])
        if components:
            comp_names = []
            comp_descriptions = []
            for comp in components:
                if comp.get('name'):
                    comp_names.append(comp['name'])
                if comp.get('description'):
                    comp_descriptions.append(f"{comp.get('name', 'Unknown')}: {comp['description']}")
            if comp_names:
                content_parts.append(f"Components: {', '.join(comp_names)}")
            if comp_descriptions:
                content_parts.append(f"Component Details: {'; '.join(comp_descriptions)}")
        
        # Fix Versions
        fix_versions = fields.get('fixVersions', [])
        if fix_versions:
            version_names = []
            version_descriptions = []
            for ver in fix_versions:
                if ver.get('name'):
                    version_names.append(ver['name'])
                if ver.get('description'):
                    version_descriptions.append(f"{ver.get('name', 'Unknown')}: {ver['description']}")
            if version_names:
                content_parts.append(f"Fix Versions: {', '.join(version_names)}")
            if version_descriptions:
                content_parts.append(f"Fix Version Details: {'; '.join(version_descriptions)}")
        
        # Affects Versions
        affects_versions = fields.get('versions', [])
        if affects_versions:
            version_names = []
            for ver in affects_versions:
                if ver.get('name'):
                    version_names.append(ver['name'])
            if version_names:
                content_parts.append(f"Affects Versions: {', '.join(version_names)}")
        
        # Environment
        environment = fields.get('environment')
        if environment:
            env_text = self._clean_html_text(environment) if isinstance(environment, str) else str(environment)
            if env_text:
                content_parts.append(f"Environment: {env_text}")
        
        # Time Tracking
        timetracking = fields.get('timetracking') or {}
        if timetracking:
            if timetracking.get('originalEstimate'):
                content_parts.append(f"Original Estimate: {timetracking['originalEstimate']}")
            if timetracking.get('remainingEstimate'):
                content_parts.append(f"Remaining Estimate: {timetracking['remainingEstimate']}")
            if timetracking.get('timeSpent'):
                content_parts.append(f"Time Spent: {timetracking['timeSpent']}")
        
        # Security Level
        security = fields.get('security') or {}
        if security and isinstance(security, dict):
            content_parts.append(f"Security Level: {security.get('name', 'Unknown')}")
            if security.get('description'):
                content_parts.append(f"Security Level Description: {security['description']}")
        
        # Due Date
        due_date = fields.get('duedate')
        if due_date:
            content_parts.append(f"Due Date: {due_date}")
        
        # Resolution Date
        resolution_date = fields.get('resolutiondate')
        if resolution_date:
            content_parts.append(f"Resolution Date: {resolution_date}")
        
        # Votes
        votes = fields.get('votes') or {}
        if votes and isinstance(votes, dict) and votes.get('votes'):
            content_parts.append(f"Votes: {votes['votes']}")
        
        # Watchers
        watches = fields.get('watches') or {}
        if watches and isinstance(watches, dict) and watches.get('watchCount'):
            content_parts.append(f"Watchers: {watches['watchCount']}")
        
        # Attachments
        attachment = fields.get('attachment', [])
        if attachment:
            attachment_names = [att.get('filename', 'Unknown') for att in attachment if att.get('filename')]
            if attachment_names:
                content_parts.append(f"Attachments: {', '.join(attachment_names)}")
                content_parts.append(f"Attachment Count: {len(attachment)}")
        
        # Sub-tasks
        subtasks = fields.get('subtasks', [])
        if subtasks:
            subtask_keys = [task.get('key', 'Unknown') for task in subtasks if task.get('key')]
            if subtask_keys:
                content_parts.append(f"Subtasks: {', '.join(subtask_keys)}")
                content_parts.append(f"Subtask Count: {len(subtasks)}")
        
        # Parent (for subtasks)
        parent = fields.get('parent') or {}
        if parent and isinstance(parent, dict) and parent.get('key'):
            content_parts.append(f"Parent Issue: {parent['key']}")
            if parent.get('fields', {}).get('summary'):
                content_parts.append(f"Parent Summary: {parent['fields']['summary']}")
        
        # Issue Links
        issuelinks = fields.get('issuelinks', [])
        if issuelinks:
            inward_links = []
            outward_links = []
            
            for link in issuelinks:
                link_type = link.get('type', {})
                link_name = link_type.get('name', 'Unknown')
                
                if 'inwardIssue' in link:
                    inward_issue = link['inwardIssue']
                    inward_links.append(f"{link_type.get('inward', 'linked to')} {inward_issue.get('key', 'Unknown')}")
                
                if 'outwardIssue' in link:
                    outward_issue = link['outwardIssue']
                    outward_links.append(f"{link_type.get('outward', 'links to')} {outward_issue.get('key', 'Unknown')}")
            
            if inward_links:
                content_parts.append(f"Inward Links: {'; '.join(inward_links)}")
            if outward_links:
                content_parts.append(f"Outward Links: {'; '.join(outward_links)}")
        
        # Progress
        progress = fields.get('progress') or {}
        if progress and isinstance(progress, dict):
            total = progress.get('total', 0)
            percent = progress.get('percent', 0)
            if total > 0 or percent > 0:
                content_parts.append(f"Progress: {percent}% ({progress.get('progress', 0)}/{total})")
        
        # Aggregate Progress (for epics/parents)
        aggregateprogress = fields.get('aggregateprogress') or {}
        if aggregateprogress and isinstance(aggregateprogress, dict):
            total = aggregateprogress.get('total', 0)
            percent = aggregateprogress.get('percent', 0)
            if total > 0 or percent > 0:
                content_parts.append(f"Aggregate Progress: {percent}% ({aggregateprogress.get('progress', 0)}/{total})")
        
        # Work Ratio
        workratio = fields.get('workratio')
        if workratio is not None:
            content_parts.append(f"Work Ratio: {workratio}")
        
        # Custom Fields (commonly used ones)
        # Epic Link
        epic_link = fields.get('customfield_10014') or fields.get('epicLink')  # Common epic link field
        if epic_link:
            content_parts.append(f"Epic Link: {epic_link}")
        
        # Story Points
        story_points = fields.get('customfield_10016') or fields.get('storyPoints')  # Common story points field
        if story_points:
            content_parts.append(f"Story Points: {story_points}")
        
        # Sprint (if using Agile)
        sprint = fields.get('customfield_10020') or fields.get('sprint')  # Common sprint field
        if sprint:
            if isinstance(sprint, list) and sprint:
                # Extract sprint names from complex sprint objects
                sprint_names = []
                for sp in sprint:
                    if isinstance(sp, str):
                        # Extract sprint name from string format
                        import re
                        match = re.search(r'name=([^,\]]+)', sp)
                        if match:
                            sprint_names.append(match.group(1))
                        else:
                            sprint_names.append(str(sp))
                    elif isinstance(sp, dict) and sp.get('name'):
                        sprint_names.append(sp['name'])
                
                if sprint_names:
                    content_parts.append(f"Sprint: {', '.join(sprint_names)}")
            elif isinstance(sprint, str):
                content_parts.append(f"Sprint: {sprint}")
        
        # Team
        team = fields.get('customfield_10021') or fields.get('team')  # Common team field
        if team:
            if isinstance(team, dict) and team.get('name'):
                content_parts.append(f"Team: {team['name']}")
            elif isinstance(team, str):
                content_parts.append(f"Team: {team}")
        
        # Business Value
        business_value = fields.get('customfield_10017') or fields.get('businessValue')
        if business_value:
            content_parts.append(f"Business Value: {business_value}")
        
        # Acceptance Criteria
        acceptance_criteria = fields.get('customfield_10015') or fields.get('acceptanceCriteria')
        if acceptance_criteria:
            criteria_text = self._clean_html_text(acceptance_criteria) if isinstance(acceptance_criteria, str) else str(acceptance_criteria)
            if criteria_text:
                content_parts.append(f"Acceptance Criteria: {criteria_text}")
        
        # Risk
        risk = fields.get('customfield_10018') or fields.get('risk')
        if risk:
            if isinstance(risk, dict) and risk.get('value'):
                content_parts.append(f"Risk: {risk['value']}")
            elif isinstance(risk, str):
                content_parts.append(f"Risk: {risk}")
        
        # Add any other non-null custom fields
        for field_key, field_value in fields.items():
            if field_key.startswith('customfield_') and field_value is not None:
                # Skip already processed custom fields
                if field_key in ['customfield_10014', 'customfield_10015', 'customfield_10016', 
                                'customfield_10017', 'customfield_10018', 'customfield_10020', 'customfield_10021']:
                    continue
                
                # Try to extract meaningful value
                if isinstance(field_value, dict):
                    if field_value.get('name'):
                        content_parts.append(f"Custom Field {field_key}: {field_value['name']}")
                    elif field_value.get('value'):
                        content_parts.append(f"Custom Field {field_key}: {field_value['value']}")
                elif isinstance(field_value, list) and field_value:
                    if all(isinstance(item, dict) and item.get('name') for item in field_value):
                        names = [item['name'] for item in field_value]
                        content_parts.append(f"Custom Field {field_key}: {', '.join(names)}")
                    elif all(isinstance(item, str) for item in field_value):
                        content_parts.append(f"Custom Field {field_key}: {', '.join(field_value)}")
                elif isinstance(field_value, (str, int, float)) and str(field_value).strip():
                    content_parts.append(f"Custom Field {field_key}: {field_value}")
        
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
    
    def _create_document_attributes(self, issue: Dict[str, Any], fields: Dict[str, Any], execution_id: str = None) -> List[Dict[str, Any]]:
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
        
        # Required attributes for custom connector (per AWS documentation)
        # Note: _data_source_sync_job_execution_id is automatically added by AWS when using dataSourceSyncId parameter
        
        # Issue key
        if issue.get('key'):
            attributes.append({
                'name': 'jira_issue_key',
                'value': {
                    'stringValue': issue['key']
                }
            })
        
        # Issue ID
        if issue.get('id'):
            attributes.append({
                'name': 'jira_issue_id',
                'value': {
                    'stringValue': str(issue['id'])
                }
            })
        
        # Project
        project = fields.get('project') or {}
        if project and isinstance(project, dict):
            if project.get('key'):
                attributes.append({
                    'name': 'jira_project',
                    'value': {
                        'stringValue': project['key']
                    }
                })
            if project.get('name'):
                attributes.append({
                    'name': 'jira_project_name',
                    'value': {
                        'stringValue': project['name']
                    }
                })
            if project.get('projectCategory', {}).get('name'):
                attributes.append({
                    'name': 'jira_project_category',
                    'value': {
                        'stringValue': project['projectCategory']['name']
                    }
                })
        
        # Issue type
        issuetype = fields.get('issuetype') or {}
        if issuetype and isinstance(issuetype, dict):
            if issuetype.get('name'):
                attributes.append({
                    'name': 'jira_issue_type',
                    'value': {
                        'stringValue': issuetype['name']
                    }
                })
            if issuetype.get('subtask') is not None:
                attributes.append({
                    'name': 'jira_is_subtask',
                    'value': {
                        'stringValue': str(issuetype['subtask']).lower()
                    }
                })
        
        # Status
        status = fields.get('status') or {}
        if status and isinstance(status, dict):
            if status.get('name'):
                attributes.append({
                    'name': 'jira_status',
                    'value': {
                        'stringValue': status['name']
                    }
                })
            if status.get('statusCategory', {}).get('name'):
                attributes.append({
                    'name': 'jira_status_category',
                    'value': {
                        'stringValue': status['statusCategory']['name']
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
        
        # Resolution
        resolution = fields.get('resolution') or {}
        if resolution and isinstance(resolution, dict) and resolution.get('name'):
            attributes.append({
                'name': 'jira_resolution',
                'value': {
                    'stringValue': resolution['name']
                }
            })
        
        # Assignee
        assignee = fields.get('assignee') or {}
        if assignee and isinstance(assignee, dict):
            if assignee.get('displayName'):
                attributes.append({
                    'name': 'jira_assignee',
                    'value': {
                        'stringValue': assignee['displayName']
                    }
                })
            if assignee.get('emailAddress'):
                attributes.append({
                    'name': 'jira_assignee_email',
                    'value': {
                        'stringValue': assignee['emailAddress']
                    }
                })
            if assignee.get('name'):
                attributes.append({
                    'name': 'jira_assignee_username',
                    'value': {
                        'stringValue': assignee['name']
                    }
                })
        else:
            attributes.append({
                'name': 'jira_assignee',
                'value': {
                    'stringValue': 'Unassigned'
                }
            })
        
        # Reporter
        reporter = fields.get('reporter') or {}
        if reporter and isinstance(reporter, dict):
            if reporter.get('displayName'):
                attributes.append({
                    'name': 'jira_reporter',
                    'value': {
                        'stringValue': reporter['displayName']
                    }
                })
            if reporter.get('emailAddress'):
                attributes.append({
                    'name': 'jira_reporter_email',
                    'value': {
                        'stringValue': reporter['emailAddress']
                    }
                })
            if reporter.get('name'):
                attributes.append({
                    'name': 'jira_reporter_username',
                    'value': {
                        'stringValue': reporter['name']
                    }
                })
        
        # Creator
        creator = fields.get('creator') or {}
        if creator and isinstance(creator, dict):
            if creator.get('displayName'):
                attributes.append({
                    'name': 'jira_creator',
                    'value': {
                        'stringValue': creator['displayName']
                    }
                })
            if creator.get('emailAddress'):
                attributes.append({
                    'name': 'jira_creator_email',
                    'value': {
                        'stringValue': creator['emailAddress']
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
        
        # Due date
        if fields.get('duedate'):
            attributes.append({
                'name': 'jira_due_date',
                'value': {
                    'dateValue': self._parse_jira_date(fields['duedate'])
                }
            })
        
        # Resolution date
        if fields.get('resolutiondate'):
            attributes.append({
                'name': 'jira_resolution_date',
                'value': {
                    'dateValue': self._parse_jira_date(fields['resolutiondate'])
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
        
        # Components
        components = fields.get('components', [])
        if components:
            comp_names = [comp.get('name', '') for comp in components if comp.get('name')]
            if comp_names:
                attributes.append({
                    'name': 'jira_components',
                    'value': {
                        'stringListValue': comp_names
                    }
                })
        
        # Fix Versions
        fix_versions = fields.get('fixVersions', [])
        if fix_versions:
            version_names = [ver.get('name', '') for ver in fix_versions if ver.get('name')]
            if version_names:
                attributes.append({
                    'name': 'jira_fix_versions',
                    'value': {
                        'stringListValue': version_names
                    }
                })
        
        # Affects Versions
        affects_versions = fields.get('versions', [])
        if affects_versions:
            version_names = [ver.get('name', '') for ver in affects_versions if ver.get('name')]
            if version_names:
                attributes.append({
                    'name': 'jira_affects_versions',
                    'value': {
                        'stringListValue': version_names
                    }
                })
        
        # Security Level
        security = fields.get('security') or {}
        if security and isinstance(security, dict) and security.get('name'):
            attributes.append({
                'name': 'jira_security_level',
                'value': {
                    'stringValue': security['name']
                }
            })
        
        # Time Tracking
        timetracking = fields.get('timetracking') or {}
        if timetracking:
            if timetracking.get('originalEstimate'):
                attributes.append({
                    'name': 'jira_original_estimate',
                    'value': {
                        'stringValue': timetracking['originalEstimate']
                    }
                })
            if timetracking.get('remainingEstimate'):
                attributes.append({
                    'name': 'jira_remaining_estimate',
                    'value': {
                        'stringValue': timetracking['remainingEstimate']
                    }
                })
            if timetracking.get('timeSpent'):
                attributes.append({
                    'name': 'jira_time_spent',
                    'value': {
                        'stringValue': timetracking['timeSpent']
                    }
                })
            if timetracking.get('originalEstimateSeconds'):
                attributes.append({
                    'name': 'jira_original_estimate_seconds',
                    'value': {
                        'longValue': timetracking['originalEstimateSeconds']
                    }
                })
            if timetracking.get('remainingEstimateSeconds'):
                attributes.append({
                    'name': 'jira_remaining_estimate_seconds',
                    'value': {
                        'longValue': timetracking['remainingEstimateSeconds']
                    }
                })
            if timetracking.get('timeSpentSeconds'):
                attributes.append({
                    'name': 'jira_time_spent_seconds',
                    'value': {
                        'longValue': timetracking['timeSpentSeconds']
                    }
                })
        
        # Progress
        progress = fields.get('progress') or {}
        if progress and isinstance(progress, dict):
            if progress.get('percent') is not None:
                attributes.append({
                    'name': 'jira_progress_percent',
                    'value': {
                        'longValue': progress['percent']
                    }
                })
            if progress.get('total') is not None:
                attributes.append({
                    'name': 'jira_progress_total',
                    'value': {
                        'longValue': progress['total']
                    }
                })
        
        # Work Ratio
        workratio = fields.get('workratio')
        if workratio is not None:
            attributes.append({
                'name': 'jira_work_ratio',
                'value': {
                    'longValue': workratio
                }
            })
        
        # Votes
        votes = fields.get('votes') or {}
        if votes and isinstance(votes, dict) and votes.get('votes') is not None:
            attributes.append({
                'name': 'jira_votes',
                'value': {
                    'longValue': votes['votes']
                }
            })
        
        # Watchers
        watches = fields.get('watches') or {}
        if watches and isinstance(watches, dict) and watches.get('watchCount') is not None:
            attributes.append({
                'name': 'jira_watchers',
                'value': {
                    'longValue': watches['watchCount']
                }
            })
        
        # Attachments
        attachment = fields.get('attachment', [])
        if attachment:
            attributes.append({
                'name': 'jira_attachment_count',
                'value': {
                    'longValue': len(attachment)
                }
            })
            attachment_names = [att.get('filename', '') for att in attachment if att.get('filename')]
            if attachment_names:
                attributes.append({
                    'name': 'jira_attachment_names',
                    'value': {
                        'stringListValue': attachment_names
                    }
                })
        
        # Subtasks
        subtasks = fields.get('subtasks', [])
        if subtasks:
            attributes.append({
                'name': 'jira_subtask_count',
                'value': {
                    'longValue': len(subtasks)
                }
            })
            subtask_keys = [task.get('key', '') for task in subtasks if task.get('key')]
            if subtask_keys:
                attributes.append({
                    'name': 'jira_subtask_keys',
                    'value': {
                        'stringListValue': subtask_keys
                    }
                })
        
        # Parent (for subtasks)
        parent = fields.get('parent') or {}
        if parent and isinstance(parent, dict) and parent.get('key'):
            attributes.append({
                'name': 'jira_parent_key',
                'value': {
                    'stringValue': parent['key']
                }
            })
        
        # Issue Links
        issuelinks = fields.get('issuelinks', [])
        if issuelinks:
            inward_keys = []
            outward_keys = []
            link_types = []
            
            for link in issuelinks:
                link_type = link.get('type', {})
                if link_type.get('name'):
                    link_types.append(link_type['name'])
                
                if 'inwardIssue' in link:
                    inward_issue = link['inwardIssue']
                    if inward_issue.get('key'):
                        inward_keys.append(inward_issue['key'])
                
                if 'outwardIssue' in link:
                    outward_issue = link['outwardIssue']
                    if outward_issue.get('key'):
                        outward_keys.append(outward_issue['key'])
            
            if inward_keys:
                attributes.append({
                    'name': 'jira_inward_links',
                    'value': {
                        'stringListValue': inward_keys
                    }
                })
            
            if outward_keys:
                attributes.append({
                    'name': 'jira_outward_links',
                    'value': {
                        'stringListValue': outward_keys
                    }
                })
            
            if link_types:
                attributes.append({
                    'name': 'jira_link_types',
                    'value': {
                        'stringListValue': list(set(link_types))  # Remove duplicates
                    }
                })
        
        # Environment (as attribute for filtering)
        environment = fields.get('environment')
        if environment:
            env_text = self._clean_html_text(environment) if isinstance(environment, str) else str(environment)
            if env_text and len(env_text.strip()) > 0:
                # Truncate environment text for attribute if too long
                if len(env_text) > 1000:
                    env_text = env_text[:1000] + "..."
                attributes.append({
                    'name': 'jira_environment',
                    'value': {
                        'stringValue': env_text
                    }
                })
        
        # Custom Fields (commonly used ones)
        # Epic Link
        epic_link = fields.get('customfield_10014') or fields.get('epicLink')
        if epic_link:
            attributes.append({
                'name': 'jira_epic_link',
                'value': {
                    'stringValue': str(epic_link)
                }
            })
        
        # Story Points
        story_points = fields.get('customfield_10016') or fields.get('storyPoints')
        if story_points is not None:
            attributes.append({
                'name': 'jira_story_points',
                'value': {
                    'longValue': int(float(story_points)) if isinstance(story_points, (int, float, str)) else 0
                }
            })
        
        # Sprint (if using Agile)
        sprint = fields.get('customfield_10020') or fields.get('sprint')
        if sprint:
            sprint_names = []
            if isinstance(sprint, list) and sprint:
                for sp in sprint:
                    if isinstance(sp, str):
                        # Extract sprint name from string format
                        import re
                        match = re.search(r'name=([^,\]]+)', sp)
                        if match:
                            sprint_names.append(match.group(1))
                    elif isinstance(sp, dict) and sp.get('name'):
                        sprint_names.append(sp['name'])
            elif isinstance(sprint, str):
                sprint_names.append(sprint)
            
            if sprint_names:
                attributes.append({
                    'name': 'jira_sprint',
                    'value': {
                        'stringListValue': sprint_names
                    }
                })
        
        # Team
        team = fields.get('customfield_10021') or fields.get('team')
        if team:
            team_name = None
            if isinstance(team, dict) and team.get('name'):
                team_name = team['name']
            elif isinstance(team, str):
                team_name = team
            
            if team_name:
                attributes.append({
                    'name': 'jira_team',
                    'value': {
                        'stringValue': team_name
                    }
                })
        
        # Business Value
        business_value = fields.get('customfield_10017') or fields.get('businessValue')
        if business_value is not None:
            attributes.append({
                'name': 'jira_business_value',
                'value': {
                    'longValue': int(float(business_value)) if isinstance(business_value, (int, float, str)) else 0
                }
            })
        
        # Risk
        risk = fields.get('customfield_10018') or fields.get('risk')
        if risk:
            risk_value = None
            if isinstance(risk, dict) and risk.get('value'):
                risk_value = risk['value']
            elif isinstance(risk, str):
                risk_value = risk
            
            if risk_value:
                attributes.append({
                    'name': 'jira_risk',
                    'value': {
                        'stringValue': risk_value
                    }
                })
        
        # Add additional custom fields as generic attributes
        for field_key, field_value in fields.items():
            if field_key.startswith('customfield_') and field_value is not None:
                # Skip already processed custom fields
                if field_key in ['customfield_10014', 'customfield_10015', 'customfield_10016', 
                                'customfield_10017', 'customfield_10018', 'customfield_10020', 'customfield_10021']:
                    continue
                
                # Extract meaningful value for generic custom fields
                if isinstance(field_value, dict):
                    if field_value.get('name'):
                        attributes.append({
                            'name': f'jira_{field_key}',
                            'value': {
                                'stringValue': field_value['name']
                            }
                        })
                    elif field_value.get('value'):
                        attributes.append({
                            'name': f'jira_{field_key}',
                            'value': {
                                'stringValue': str(field_value['value'])
                            }
                        })
                elif isinstance(field_value, list) and field_value:
                    if all(isinstance(item, dict) and item.get('name') for item in field_value):
                        names = [item['name'] for item in field_value]
                        attributes.append({
                            'name': f'jira_{field_key}',
                            'value': {
                                'stringListValue': names
                            }
                        })
                    elif all(isinstance(item, str) for item in field_value):
                        attributes.append({
                            'name': f'jira_{field_key}',
                            'value': {
                                'stringListValue': field_value
                            }
                        })
                elif isinstance(field_value, (str, int, float)):
                    value_str = str(field_value).strip()
                    if value_str:
                        if isinstance(field_value, (int, float)):
                            attributes.append({
                                'name': f'jira_{field_key}',
                                'value': {
                                    'longValue': int(field_value)
                                }
                            })
                        else:
                            attributes.append({
                                'name': f'jira_{field_key}',
                                'value': {
                                    'stringValue': value_str
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