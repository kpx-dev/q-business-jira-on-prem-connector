"""
Jira Client for connecting to on-premises Jira Server 9.12.17
Uses Jira REST API v2 for compatibility with on-prem installations
"""
import requests
import logging
from typing import Dict, List, Optional, Any, Iterator
from datetime import datetime
from urllib.parse import urljoin
import json
from requests.auth import HTTPBasicAuth
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import JiraConfig

logger = logging.getLogger(__name__)


class JiraClient:
    """Client for interacting with Jira Server REST API"""
    
    def __init__(self, config: JiraConfig):
        self.config = config
        self.base_url = config.server_url.rstrip('/')
        self.session = self._create_session()
        
    def _create_session(self) -> requests.Session:
        """Create a configured requests session with retry strategy"""
        session = requests.Session()
        
        # Authentication
        session.auth = HTTPBasicAuth(self.config.username, self.config.password)
        
        # Headers
        session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'Jira-Q-Business-Connector/1.0'
        })
        
        # SSL verification
        session.verify = self.config.verify_ssl
        
        # Retry strategy
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=1,
            respect_retry_after_header=True
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make a request to Jira API with error handling"""
        # Ensure base_url is not empty
        if not self.base_url:
            raise Exception("Jira server URL is not configured")
            
        url = urljoin(f"{self.base_url}/rest/api/2/", endpoint.lstrip('/'))
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                timeout=self.config.timeout,
                **kwargs
            )
            response.raise_for_status()
            return response
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error for {method} {url}: {e}")
            if response.status_code == 401:
                raise Exception("Authentication failed. Check your credentials.")
            elif response.status_code == 403:
                raise Exception("Access forbidden. Check your permissions.")
            elif response.status_code == 404:
                raise Exception("Resource not found.")
            else:
                raise Exception(f"HTTP {response.status_code}: {e}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error for {method} {url}: {e}")
            raise Exception(f"Request failed: {e}")
    
    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Jira server"""
        try:
            response = self._make_request('GET', 'serverInfo')
            server_info = response.json()
            
            # Also test authentication by getting current user
            user_response = self._make_request('GET', 'myself')
            user_info = user_response.json()
            
            return {
                'success': True,
                'server_info': server_info,
                'user_info': user_info,
                'message': f"Connected to Jira {server_info.get('version', 'Unknown')} as {user_info.get('displayName', 'Unknown')}"
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f"Failed to connect to Jira: {e}"
            }
    
    def get_projects(self) -> List[Dict[str, Any]]:
        """Get all projects the user has access to"""
        response = self._make_request('GET', 'project')
        projects = response.json()
        
        logger.info(f"Retrieved {len(projects)} projects")
        return projects
    
    def search_issues(self, 
                     jql: str = "", 
                     start_at: int = 0, 
                     max_results: int = 100,
                     fields: Optional[List[str]] = None,
                     expand: Optional[List[str]] = None) -> Dict[str, Any]:
        """Search for issues using JQL"""
        
        if fields is None:
            # Get comprehensive fields for Q Business - includes all standard and common custom fields
            fields = [
                # Core fields
                'key', 'id', 'self', 'summary', 'description', 'status', 'priority',
                'assignee', 'reporter', 'creator', 'created', 'updated', 'duedate',
                'resolutiondate', 'project', 'issuetype', 'resolution',
                
                # Content and metadata
                'labels', 'components', 'versions', 'fixVersions', 'environment',
                'comment', 'attachment', 'worklog', 'issuelinks', 'subtasks', 'parent',
                
                # Time tracking and progress
                'timetracking', 'timeestimate', 'timeoriginalestimate', 'timespent',
                'aggregatetimeestimate', 'aggregatetimeoriginalestimate', 'aggregatetimespent',
                'progress', 'aggregateprogress', 'workratio',
                
                # Security and permissions
                'security', 'watches', 'votes',
                
                # Agile/Custom fields (common field IDs - may vary by Jira instance)
                'customfield_10014',  # Epic Link
                'customfield_10015',  # Acceptance Criteria
                'customfield_10016',  # Story Points
                'customfield_10017',  # Business Value
                'customfield_10018',  # Risk
                'customfield_10019',  # Epic Name
                'customfield_10020',  # Sprint
                'customfield_10021',  # Team
                'customfield_10022',  # Epic Status
                'customfield_10023',  # Epic Color
                'customfield_10024',  # Rank
                'customfield_10025',  # Request Type
                'customfield_10026',  # Customer Request Type
                'customfield_10027',  # Organizations
                'customfield_10028',  # Request participants
                'customfield_10029',  # Approvers
                'customfield_10030',  # Epic Theme
                
                # Additional common custom fields (add more as needed)
                'customfield_10031', 'customfield_10032', 'customfield_10033', 'customfield_10034',
                'customfield_10035', 'customfield_10036', 'customfield_10037', 'customfield_10038',
                'customfield_10039', 'customfield_10040', 'customfield_10041', 'customfield_10042',
                'customfield_10043', 'customfield_10044', 'customfield_10045', 'customfield_10046',
                'customfield_10047', 'customfield_10048', 'customfield_10049', 'customfield_10050'
            ]
        
        if expand is None:
            expand = ['changelog', 'names', 'schema', 'operations', 'editmeta', 'renderedFields']
        
        params = {
            'jql': jql or 'order by updated DESC',
            'startAt': start_at,
            'maxResults': max_results,
            'fields': ','.join(fields),
            'expand': ','.join(expand)
        }
        
        response = self._make_request('GET', 'search', params=params)
        result = response.json()
        
        logger.info(f"Retrieved {len(result.get('issues', []))} issues (total: {result.get('total', 0)})")
        return result
    
    def get_issue(self, issue_key: str, expand: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get a specific issue by key"""
        if expand is None:
            expand = ['changelog', 'operations', 'editmeta', 'names', 'schema']
        
        params = {
            'expand': ','.join(expand)
        }
        
        response = self._make_request('GET', f'issue/{issue_key}', params=params)
        return response.json()
    
    def get_issue_comments(self, issue_key: str) -> List[Dict[str, Any]]:
        """Get comments for a specific issue"""
        response = self._make_request('GET', f'issue/{issue_key}/comment')
        comments = response.json().get('comments', [])
        return comments
    
    def get_issue_changelog(self, issue_key: str) -> List[Dict[str, Any]]:
        """Get changelog for a specific issue"""
        params = {'expand': 'changelog'}
        response = self._make_request('GET', f'issue/{issue_key}', params=params)
        
        issue = response.json()
        changelog = issue.get('changelog', {}).get('histories', [])
        return changelog
    
    def get_all_issues_iterator(self, 
                               jql: str = "", 
                               batch_size: int = 100,
                               fields: Optional[List[str]] = None) -> Iterator[Dict[str, Any]]:
        """Iterator to get all issues matching JQL query"""
        start_at = 0
        
        while True:
            result = self.search_issues(
                jql=jql,
                start_at=start_at,
                max_results=batch_size,
                fields=fields
            )
            
            issues = result.get('issues', [])
            if not issues:
                break
                
            for issue in issues:
                yield issue
            
            # Check if we've retrieved all issues
            total = result.get('total', 0)
            if start_at + len(issues) >= total:
                break
                
            start_at += batch_size
    
    def close(self):
        """Close the session"""
        if hasattr(self, 'session'):
            self.session.close()
    
    def get_all_users(self, start_at: int = 0, max_results: int = 100) -> List[Dict[str, Any]]:
        """
        Get all users from Jira using the user search API
        
        Args:
            start_at: Starting index for pagination
            max_results: Maximum number of results to return
            
        Returns:
            List of user objects
        """
        params = {
            'username': '.',  # Use '.' as a wildcard to get all users
            'startAt': start_at,
            'maxResults': max_results
        }
        
        try:
            # Use user/search endpoint instead of users
            response = self._make_request('GET', 'user/search', params=params)
            users = response.json()
            
            logger.info(f"Retrieved {len(users)} users")
            
            # Check if we need to paginate
            if len(users) == max_results:
                next_users = self.get_all_users(start_at + max_results, max_results)
                users.extend(next_users)
            
            return users
        except Exception as e:
            logger.error(f"Error getting users: {e}")
            # Try alternative approach if the above doesn't work
            try:
                # Alternative: use user/search with empty query
                params = {
                    'query': '',
                    'startAt': start_at,
                    'maxResults': max_results
                }
                response = self._make_request('GET', 'user/search', params=params)
                users = response.json()
                logger.info(f"Retrieved {len(users)} users using alternative method")
                return users
            except Exception as e2:
                logger.error(f"Error getting users with alternative method: {e2}")
                return []

    def get_all_groups(self, start_at: int = 0, max_results: int = 100) -> List[Dict[str, Any]]:
        """
        Get all groups from Jira
        
        Args:
            start_at: Starting index for pagination
            max_results: Maximum number of results to return
            
        Returns:
            List of group objects
        """
        params = {
            'startAt': start_at,
            'maxResults': max_results
        }
        
        try:
            response = self._make_request('GET', 'groups/picker', params=params)
            result = response.json()
            groups = result.get('groups', [])
            
            logger.info(f"Retrieved {len(groups)} groups")
            
            # Check if we need to paginate
            if result.get('total', 0) > start_at + len(groups):
                next_groups = self.get_all_groups(start_at + max_results, max_results)
                groups.extend(next_groups)
            
            return groups
        except Exception as e:
            logger.error(f"Error getting groups: {e}")
            return []

    def get_all_project_roles(self) -> List[Dict[str, Any]]:
        """
        Get all project roles from Jira
        
        Returns:
            List of project role objects
        """
        try:
            response = self._make_request('GET', 'role')
            roles = response.json()
            
            logger.info(f"Retrieved {len(roles)} project roles")
            return roles
        except Exception as e:
            logger.error(f"Error getting project roles: {e}")
            return []

    def get_all_projects(self) -> List[Dict[str, Any]]:
        """
        Get all projects from Jira
        
        Returns:
            List of project objects
        """
        try:
            response = self._make_request('GET', 'project')
            projects = response.json()
            
            logger.info(f"Retrieved {len(projects)} projects")
            return projects
        except Exception as e:
            logger.error(f"Error getting projects: {e}")
            return []

    def get_all_security_levels(self) -> List[Dict[str, Any]]:
        """
        Get all issue security levels from Jira
        
        Returns:
            List of security level objects
        """
        try:
            # First get all security schemes
            response = self._make_request('GET', 'issuesecurityschemes')
            schemes = response.json().get('issueSecuritySchemes', [])
            
            security_levels = []
            
            # For each scheme, get its security levels
            for scheme in schemes:
                scheme_id = scheme.get('id')
                if scheme_id:
                    scheme_response = self._make_request('GET', f'issuesecurityschemes/{scheme_id}')
                    scheme_details = scheme_response.json()
                    
                    # Extract security levels
                    levels = scheme_details.get('levels', [])
                    for level in levels:
                        level['schemeId'] = scheme_id
                        level['schemeName'] = scheme.get('name')
                    
                    security_levels.extend(levels)
            
            logger.info(f"Retrieved {len(security_levels)} security levels from {len(schemes)} schemes")
            return security_levels
        except Exception as e:
            logger.error(f"Error getting security levels: {e}")
            return []

    def get_group_members(self, group_name: str, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """
        Get members of a group
        
        Args:
            group_name: Group name
            include_inactive: Whether to include inactive users
            
        Returns:
            List of group members
        """
        try:
            params = {
                'groupname': group_name,
                'includeInactiveUsers': str(include_inactive).lower()
            }
            response = self._make_request('GET', 'group/member', params=params)
            result = response.json()
            return result.get('values', [])
        except Exception as e:
            logger.error(f"Error getting members for group {group_name}: {e}")
            return []

    def get_project_permissions(self, project_key: str) -> Dict[str, Any]:
        """
        Get permissions for a project using mypermissions API
        
        Args:
            project_key: Project key
            
        Returns:
            Dictionary of permissions
        """
        try:
            # Use mypermissions API to get permissions for current user in the project
            params = {'projectKey': project_key}
            response = self._make_request('GET', 'mypermissions', params=params)
            permissions = response.json()
            
            logger.info(f"Retrieved permissions for project {project_key}")
            return permissions
        except Exception as e:
            logger.error(f"Error getting permissions for project {project_key}: {e}")
            # Since the permissions endpoint doesn't exist, return empty dict
            # and rely on project roles instead
            return {}

    def get_users_with_project_permission(self, project_key: str, permission: str) -> List[Dict[str, Any]]:
        """
        Get users with a specific permission in a project by checking project roles
        
        Args:
            project_key: Project key
            permission: Permission key (e.g., 'BROWSE_PROJECTS')
            
        Returns:
            List of user objects with the permission
        """
        try:
            # Get project roles
            roles_response = self._make_request('GET', f'project/{project_key}/role')
            roles = roles_response.json()
            
            users = []
            unique_users = set()  # Track unique users to avoid duplicates
            
            # For each role, get its actors (users)
            for role_url in roles.values():
                if not isinstance(role_url, str):
                    continue
                    
                # Extract role ID from URL
                role_id = role_url.split('/')[-1]
                
                try:
                    # Get role details
                    role_response = self._make_request('GET', f'project/{project_key}/role/{role_id}')
                    role = role_response.json()
                    
                    # Extract users
                    actors = role.get('actors', [])
                    for actor in actors:
                        if actor.get('type') == 'atlassian-user-role-actor':
                            user_name = actor.get('name')
                            if user_name and user_name not in unique_users:
                                user = {
                                    'name': user_name,
                                    'displayName': actor.get('displayName', user_name)
                                }
                                users.append(user)
                                unique_users.add(user_name)
                except Exception as role_error:
                    logger.warning(f"Error getting role {role_id} for project {project_key}: {role_error}")
                    continue
            
            logger.info(f"Retrieved {len(users)} users with permission {permission} for project {project_key}")
            return users
        except Exception as e:
            logger.error(f"Error getting users with permission {permission} for project {project_key}: {e}")
            return []

    def get_groups_with_project_permission(self, project_key: str, permission: str) -> List[Dict[str, Any]]:
        """
        Get groups with a specific permission in a project by checking project roles
        
        Args:
            project_key: Project key
            permission: Permission key (e.g., 'BROWSE_PROJECTS')
            
        Returns:
            List of group objects with the permission
        """
        try:
            # Get project roles
            roles_response = self._make_request('GET', f'project/{project_key}/role')
            roles = roles_response.json()
            
            groups = []
            unique_groups = set()  # Track unique groups to avoid duplicates
            
            # For each role, get its actors (groups)
            for role_url in roles.values():
                if not isinstance(role_url, str):
                    continue
                    
                # Extract role ID from URL
                role_id = role_url.split('/')[-1]
                
                try:
                    # Get role details
                    role_response = self._make_request('GET', f'project/{project_key}/role/{role_id}')
                    role = role_response.json()
                    
                    # Extract groups
                    actors = role.get('actors', [])
                    for actor in actors:
                        if actor.get('type') == 'atlassian-group-role-actor':
                            group_name = actor.get('name')
                            if group_name and group_name not in unique_groups:
                                group = {
                                    'name': group_name,
                                    'displayName': actor.get('displayName', group_name)
                                }
                                groups.append(group)
                                unique_groups.add(group_name)
                except Exception as role_error:
                    logger.warning(f"Error getting role {role_id} for project {project_key}: {role_error}")
                    continue
            
            logger.info(f"Retrieved {len(groups)} groups with permission {permission} for project {project_key}")
            return groups
        except Exception as e:
            logger.error(f"Error getting groups with permission {permission} for project {project_key}: {e}")
            return []

    def get_project_roles_for_project(self, project_key: str) -> List[Dict[str, Any]]:
        """
        Get roles for a project
        
        Args:
            project_key: Project key
            
        Returns:
            List of role objects
        """
        try:
            response = self._make_request('GET', f'project/{project_key}/role')
            roles_dict = response.json()
            
            roles = []
            
            # Convert the role URLs to role objects
            for role_name, role_url in roles_dict.items():
                if not isinstance(role_url, str):
                    continue
                    
                # Extract role ID from URL
                role_id = role_url.split('/')[-1]
                
                # Get role details
                role_response = self._make_request('GET', f'project/{project_key}/role/{role_id}')
                role = role_response.json()
                roles.append(role)
            
            logger.info(f"Retrieved {len(roles)} roles for project {project_key}")
            return roles
        except Exception as e:
            logger.error(f"Error getting roles for project {project_key}: {e}")
            return []

    def get_project_role_members(self, project_key: str, role_id: str) -> Dict[str, Any]:
        """
        Get members of a project role
        
        Args:
            project_key: Project key
            role_id: Role ID
            
        Returns:
            Dictionary with users and groups in the role
        """
        try:
            response = self._make_request('GET', f'project/{project_key}/role/{role_id}')
            role = response.json()
            
            # Extract users and groups
            users = []
            groups = []
            
            actors = role.get('actors', [])
            for actor in actors:
                actor_type = actor.get('type')
                
                if actor_type == 'atlassian-user-role-actor':
                    users.append({
                        'name': actor.get('name'),
                        'displayName': actor.get('displayName')
                    })
                elif actor_type == 'atlassian-group-role-actor':
                    groups.append({
                        'name': actor.get('name'),
                        'displayName': actor.get('displayName')
                    })
            
            result = {
                'users': users,
                'groups': groups
            }
            
            logger.info(f"Retrieved {len(users)} users and {len(groups)} groups for role {role_id} in project {project_key}")
            return result
        except Exception as e:
            logger.error(f"Error getting members for role {role_id} in project {project_key}: {e}")
            return {'users': [], 'groups': []}

    def get_users_with_security_level_access(self, security_id: str) -> List[Dict[str, Any]]:
        """
        Get users with access to a security level
        
        Note: This is a stub implementation. Security level permissions
        require specific Jira configuration and APIs not implemented yet.
        
        Args:
            security_id: Security level ID
            
        Returns:
            Empty list (stub implementation)
        """
        logger.debug(f"Security level access not implemented for level {security_id}")
        return []

    def get_groups_with_security_level_access(self, security_id: str) -> List[Dict[str, Any]]:
        """
        Get groups with access to a security level
        
        Note: This is a stub implementation. Security level permissions
        require specific Jira configuration and APIs not implemented yet.
        
        Args:
            security_id: Security level ID
            
        Returns:
            Empty list (stub implementation)
        """
        logger.debug(f"Security level access not implemented for level {security_id}")
        return []

    def get_project_permission_scheme(self, project_key: str) -> Dict[str, Any]:
        """
        Get permission scheme for a project
        
        Args:
            project_key: Project key or ID
            
        Returns:
            Dictionary with permission scheme information
        """
        try:
            response = self._make_request('GET', f'project/{project_key}/permissionscheme')
            return response.json()
        except Exception as e:
            logger.error(f"Error getting permission scheme for project {project_key}: {e}")
            return {}
    
    def get_permission_scheme_grants(self, scheme_id: str) -> List[Dict[str, Any]]:
        """
        Get permission grants for a permission scheme
        
        Args:
            scheme_id: Permission scheme ID
            
        Returns:
            List of permission grants
        """
        try:
            response = self._make_request('GET', f'permissionscheme/{scheme_id}/permission')
            result = response.json()
            return result.get('permissions', [])
        except Exception as e:
            logger.error(f"Error getting permission grants for scheme {scheme_id}: {e}")
            return []
    
    def get_project_role_actors(self, project_key: str, role_id: str) -> Dict[str, Any]:
        """
        Get actors (users and groups) for a role in a project
        
        Args:
            project_key: Project key or ID
            role_id: Role ID
            
        Returns:
            Dictionary with role actors information
        """
        try:
            response = self._make_request('GET', f'project/{project_key}/role/{role_id}')
            return response.json()
        except Exception as e:
            logger.error(f"Error getting role actors for project {project_key}, role {role_id}: {e}")
            return {}