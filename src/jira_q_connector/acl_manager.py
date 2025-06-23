"""
ACL Manager for handling access control lists for Jira documents in Amazon Q Business
"""
import logging
from typing import Dict, List, Any, Optional, Set

logger = logging.getLogger(__name__)

class ACLManager:
    """Manages ACL information for Jira documents in Amazon Q Business"""
    
    def __init__(self):
        """
        Initialize the ACL manager
        
        ACL is always enabled for this connector
        """
    
    def get_document_acl(self, issue: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract ACL information from a Jira issue
        
        Args:
            issue: Jira issue object
            
        Returns:
            Dictionary with ACL information in the format required by Amazon Q Business
            or None if ACL is not enabled or no ACL information is available
        """        
        try:
            fields = issue.get('fields', {})
            
            # Get project key for permission lookup
            project_key = None
            project = fields.get('project')
            if project and isinstance(project, dict):
                project_key = project.get('key')
            
            if not project_key:
                logger.warning(f"No project key found for issue {issue.get('key')}")
                return None
            
            # Get security level if present
            security_level_id = None
            security = fields.get('security')
            if security and isinstance(security, dict):
                security_level_id = security.get('id')
            
            # Build ACL object for Q Business
            acl = {
                'aclType': 'USER_GROUP',
                'principalList': []
            }
            
            # Add users with direct access
            users = self._get_users_with_issue_access(issue, project_key, security_level_id)
            for user in users:
                acl['principalList'].append({
                    'principalType': 'USER',
                    'principalId': user
                })
                
            # Add groups with access
            groups = self._get_groups_with_issue_access(issue, project_key, security_level_id)
            for group in groups:
                acl['principalList'].append({
                    'principalType': 'GROUP',
                    'principalId': group
                })
            
            # If no users or groups have access, return None (public access)
            if not acl['principalList']:
                return None
                
            return acl
            
        except Exception as e:
            logger.error(f"Error extracting ACL information: {e}")
            return None
    
    def _get_users_with_issue_access(self, issue: Dict[str, Any], project_key: str, 
                                     security_level_id: Optional[str]) -> List[str]:
        """
        Get users who have access to the issue based on permissions
        
        Args:
            issue: Jira issue object
            project_key: Project key
            security_level_id: Security level ID if present
            
        Returns:
            List of user IDs who have access to the issue
        """
        users = set()
        
        # Add users with direct association to the issue
        fields = issue.get('fields', {})
        
        # Add assignee if present
        assignee = fields.get('assignee')
        if assignee and isinstance(assignee, dict):
            user_id = assignee.get('name')
            if user_id:
                users.add(user_id)
        
        # Add reporter if present
        reporter = fields.get('reporter')
        if reporter and isinstance(reporter, dict):
            user_id = reporter.get('name')
            if user_id:
                users.add(user_id)
        
        # Add creator if present
        creator = fields.get('creator')
        if creator and isinstance(creator, dict):
            user_id = creator.get('name')
            if user_id:
                users.add(user_id)
        
        return list(users)
    
    def _get_groups_with_issue_access(self, issue: Dict[str, Any], project_key: str, 
                                      security_level_id: Optional[str]) -> List[str]:
        """
        Get groups who have access to the issue based on permissions
        
        Args:
            issue: Jira issue object
            project_key: Project key
            security_level_id: Security level ID if present
            
        Returns:
            List of group IDs who have access to the issue
        """
        groups = set()
        
        # Add project role groups
        # In Jira, permissions are often assigned to project roles
        groups.add(f"jira-project-{project_key}")
        
        # Add security level groups if applicable
        if security_level_id:
            groups.add(f"jira-security-{security_level_id}")
        
        return list(groups)
    
    def get_principal_store_entries(self, jira_client) -> List[Dict[str, Any]]:
        """
        Generate principal store entries for Amazon Q Business User Store
        
        Args:
            jira_client: Jira client instance to fetch users and groups
            
        Returns:
            List of principal store entries in the format required by Amazon Q Business
        """        
        try:
            principal_entries = []
            
            # Get all users from Jira
            users = jira_client.get_all_users()
            for user in users:
                principal_entries.append(self._create_user_entry(user))
            
            # Get all groups and project roles from Jira
            groups = jira_client.get_all_groups()
            for group in groups:
                principal_entries.append(self._create_group_entry(group))
            
            # Get all project roles
            project_roles = jira_client.get_all_project_roles()
            for role in project_roles:
                principal_entries.append(self._create_project_role_entry(role))
            
            # Get all projects for project-based permissions
            projects = jira_client.get_all_projects()
            for project in projects:
                # Create project group entry
                project_key = project.get('key')
                if project_key:
                    principal_entries.append(self._create_project_group_entry(project))
                    
                    # Get project permissions
                    self._add_project_permission_entries(jira_client, project, principal_entries)
            
            # Get security levels
            security_levels = jira_client.get_all_security_levels()
            for security_level in security_levels:
                principal_entries.append(self._create_security_level_entry(security_level))
                
                # Get security level permissions
                self._add_security_level_permission_entries(jira_client, security_level, principal_entries)
            
            return principal_entries
            
        except Exception as e:
            logger.error(f"Error generating principal store entries: {e}")
            return []
    
    def _create_user_entry(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a user entry for the principal store
        
        Args:
            user: User object from Jira
            
        Returns:
            Principal store entry for the user
        """
        user_id = user.get('name', '')
        email = user.get('emailAddress', '')
        display_name = user.get('displayName', '')
        
        return {
            'operation': 'PUT',
            'principal': {
                'principalType': 'USER',
                'principalId': user_id,
                'dataSourceId': 'jira',  # This should match your data source ID
                'metadata': {
                    'email': email,
                    'displayName': display_name,
                    'lastModifiedDate': user.get('updateDate', ''),
                    'isHidden': False,
                    'isDeleted': user.get('active', True) == False
                }
            }
        }
    
    def _create_group_entry(self, group: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a group entry for the principal store
        
        Args:
            group: Group object from Jira
            
        Returns:
            Principal store entry for the group
        """
        group_id = group.get('name', '')
        
        return {
            'operation': 'PUT',
            'principal': {
                'principalType': 'GROUP',
                'principalId': group_id,
                'dataSourceId': 'jira',  # This should match your data source ID
                'metadata': {
                    'displayName': group_id,
                    'lastModifiedDate': group.get('updateDate', ''),
                    'isHidden': False,
                    'isDeleted': False
                }
            }
        }
    
    def _create_project_role_entry(self, role: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a project role entry for the principal store
        
        Args:
            role: Project role object from Jira
            
        Returns:
            Principal store entry for the project role
        """
        role_id = role.get('id', '')
        role_name = role.get('name', '')
        
        return {
            'operation': 'PUT',
            'principal': {
                'principalType': 'GROUP',
                'principalId': f"jira-role-{role_name}",
                'dataSourceId': 'jira',
                'metadata': {
                    'displayName': f"Jira Role: {role_name}",
                    'lastModifiedDate': '',
                    'isHidden': False,
                    'isDeleted': False
                }
            }
        }
    
    def _create_project_group_entry(self, project: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a project group entry for the principal store
        
        Args:
            project: Project object from Jira
            
        Returns:
            Principal store entry for the project group
        """
        project_key = project.get('key', '')
        project_name = project.get('name', '')
        
        return {
            'operation': 'PUT',
            'principal': {
                'principalType': 'GROUP',
                'principalId': f"jira-project-{project_key}",
                'dataSourceId': 'jira',
                'metadata': {
                    'displayName': f"Jira Project: {project_name}",
                    'lastModifiedDate': project.get('updateDate', ''),
                    'isHidden': False,
                    'isDeleted': False
                }
            }
        }
    
    def _create_security_level_entry(self, security_level: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a security level entry for the principal store
        
        Args:
            security_level: Security level object from Jira
            
        Returns:
            Principal store entry for the security level
        """
        security_id = security_level.get('id', '')
        security_name = security_level.get('name', '')
        
        return {
            'operation': 'PUT',
            'principal': {
                'principalType': 'GROUP',
                'principalId': f"jira-security-{security_id}",
                'dataSourceId': 'jira',
                'metadata': {
                    'displayName': f"Jira Security Level: {security_name}",
                    'lastModifiedDate': '',
                    'isHidden': False,
                    'isDeleted': False
                }
            }
        }
    
    def _create_group_membership_entry(self, group_id: str, member_ids: Set[str]) -> Dict[str, Any]:
        """
        Create a group membership entry for the principal store
        
        Args:
            group_id: Group ID
            member_ids: Set of user IDs who are members of the group
            
        Returns:
            Principal store entry for the group membership
        """
        return {
            'operation': 'PUT',
            'principal': {
                'principalType': 'GROUP',
                'principalId': group_id,
                'dataSourceId': 'jira',  # This should match your data source ID
                'memberIds': list(member_ids)
            }
        }
    
    def _add_project_permission_entries(self, jira_client, project: Dict[str, Any], 
                                        entries: List[Dict[str, Any]]) -> None:
        """
        Add permission entries for a project
        
        Args:
            jira_client: Jira client instance
            project: Project object
            entries: List to add entries to
        """
        project_key = project.get('key')
        if not project_key:
            return
            
        try:
            # Get project permissions
            permissions = jira_client.get_project_permissions(project_key)
            
            # Get users with browse permission
            users_with_browse = jira_client.get_users_with_project_permission(
                project_key, 'BROWSE_PROJECTS')
            
            # Get groups with browse permission
            groups_with_browse = jira_client.get_groups_with_project_permission(
                project_key, 'BROWSE_PROJECTS')
            
            # Create group membership entry for project
            project_group_id = f"jira-project-{project_key}"
            member_ids = set()
            
            # Add users with browse permission to project group
            for user in users_with_browse:
                user_id = user.get('name')
                if user_id:
                    member_ids.add(user_id)
            
            # Add group membership entry
            if member_ids:
                entries.append(self._create_group_membership_entry(project_group_id, member_ids))
            
            # Add project role memberships
            project_roles = jira_client.get_project_roles_for_project(project_key)
            for role in project_roles:
                role_id = role.get('id')
                role_name = role.get('name')
                if not role_id or not role_name:
                    continue
                
                # Get users and groups in this role
                role_members = jira_client.get_project_role_members(project_key, role_id)
                
                # Create role group
                role_group_id = f"jira-project-{project_key}-role-{role_name}"
                role_member_ids = set()
                
                # Add users in this role
                for member in role_members.get('users', []):
                    user_id = member.get('name')
                    if user_id:
                        role_member_ids.add(user_id)
                
                # Add role group membership entry
                if role_member_ids:
                    entries.append(self._create_group_membership_entry(role_group_id, role_member_ids))
                    
                    # Add this role group to the project group
                    entries.append({
                        'operation': 'PUT',
                        'principal': {
                            'principalType': 'GROUP',
                            'principalId': project_group_id,
                            'dataSourceId': 'jira',
                            'memberIds': [role_group_id]
                        }
                    })
            
        except Exception as e:
            logger.error(f"Error processing project permissions for {project_key}: {e}")
    
    def _add_security_level_permission_entries(self, jira_client, security_level: Dict[str, Any], 
                                              entries: List[Dict[str, Any]]) -> None:
        """
        Add permission entries for a security level
        
        Args:
            jira_client: Jira client instance
            security_level: Security level object
            entries: List to add entries to
        """
        security_id = security_level.get('id')
        if not security_id:
            return
            
        try:
            # Get security level permissions
            security_level_name = security_level.get('name', '')
            security_group_id = f"jira-security-{security_id}"
            
            # Get users with access to this security level
            users_with_access = jira_client.get_users_with_security_level_access(security_id)
            
            # Get groups with access to this security level
            groups_with_access = jira_client.get_groups_with_security_level_access(security_id)
            
            # Create group membership entry for security level
            member_ids = set()
            
            # Add users with access to security level group
            for user in users_with_access:
                user_id = user.get('name')
                if user_id:
                    member_ids.add(user_id)
            
            # Add group membership entry
            if member_ids:
                entries.append(self._create_group_membership_entry(security_group_id, member_ids))
            
        except Exception as e:
            logger.error(f"Error processing security level permissions for {security_id}: {e}")
    
    def delete_principal(self, principal_id: str, principal_type: str) -> Dict[str, Any]:
        """
        Create a delete operation entry for the principal store
        
        Args:
            principal_id: ID of the principal to delete
            principal_type: Type of the principal ('USER' or 'GROUP')
            
        Returns:
            Principal store entry for deleting the principal
        """
        return {
            'operation': 'DELETE',
            'principal': {
                'principalType': principal_type,
                'principalId': principal_id,
                'dataSourceId': 'jira'  # This should match your data source ID
            }
        }