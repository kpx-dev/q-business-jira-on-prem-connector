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

from config import JiraConfig

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
            # Get essential fields for Q Business
            fields = [
                'key', 'id', 'summary', 'description', 'status', 'priority',
                'assignee', 'reporter', 'creator', 'created', 'updated',
                'resolutiondate', 'project', 'issuetype', 'labels',
                'components', 'versions', 'fixVersions', 'environment',
                'comment', 'attachment', 'worklog'
            ]
        
        if expand is None:
            expand = ['changelog']
        
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
        issue = response.json()
        
        logger.debug(f"Retrieved issue {issue_key}")
        return issue
    
    def get_issue_comments(self, issue_key: str) -> List[Dict[str, Any]]:
        """Get comments for a specific issue"""
        response = self._make_request('GET', f'issue/{issue_key}/comment')
        comments = response.json().get('comments', [])
        
        logger.debug(f"Retrieved {len(comments)} comments for issue {issue_key}")
        return comments
    
    def get_issue_changelog(self, issue_key: str) -> List[Dict[str, Any]]:
        """Get changelog for a specific issue"""
        params = {'expand': 'changelog'}
        response = self._make_request('GET', f'issue/{issue_key}', params=params)
        
        issue = response.json()
        changelog = issue.get('changelog', {}).get('histories', [])
        
        logger.debug(f"Retrieved {len(changelog)} changelog entries for issue {issue_key}")
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
    
    def get_user(self, username: str) -> Dict[str, Any]:
        """Get user information"""
        params = {'username': username}
        response = self._make_request('GET', 'user', params=params)
        return response.json()
    
    def close(self):
        """Close the session"""
        if hasattr(self, 'session'):
            self.session.close() 