"""
ACL Manager for handling access control lists for Jira documents in Amazon Q Business
"""
import logging
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict

logger = logging.getLogger(__name__)

class ACLManager:
    """Manages ACL information for Jira documents in Amazon Q Business"""
    
    def __init__(self):
        """
        Initialize the ACL manager
        
        ACL is always enabled for this connector
        """
        self.project_permissions_cache = {}
        self.group_members_cache = {}
    
    def sync_jira_acl_to_qbusiness(self, jira_client, qbusiness_client) -> Dict[str, Any]:
        """
        Sync Jira ACL to Q Business User Store
        
        This method implements the comprehensive ACL synchronization process:
        1. Extract project permissions from Jira
        2. Get permission schemes and BROWSE_PROJECTS roles
        3. Get users from groups
        4. Build access controls for documents
        5. Create/update users and groups in Q Business
        
        Args:
            jira_client: Jira client instance
            qbusiness_client: Q Business client instance
            
        Returns:
            Dictionary with sync results
        """
        stats = {
            'users_processed': 0,
            'groups_processed': 0,
            'projects_processed': 0,
            'permissions_processed': 0
        }
        
        try:
            logger.info("Starting comprehensive ACL synchronization from Jira to Q Business")
            
            # Step 1: Get all projects to process
            projects = jira_client.get_all_projects()
            logger.info(f"Found {len(projects)} projects to process")
            
            # Track all users and groups to sync
            all_users = set()
            all_groups = {}  # group_name -> {members: [...], projects: [...]}
            
            # Step 2: Process each project for ACL information
            for project in projects:
                try:
                    project_key = project.get('key')
                    if not project_key:
                        continue
                        
                    logger.info(f"Processing ACL for project: {project_key}")
                    
                    # Get project permission scheme
                    permission_scheme = jira_client.get_project_permission_scheme(project_key)
                    if not permission_scheme:
                        logger.warning(f"No permission scheme found for project {project_key}")
                        continue
                    
                    scheme_id = permission_scheme.get('id')
                    if not scheme_id:
                        logger.warning(f"No scheme ID found for project {project_key}")
                        continue
                    
                    # Get permission scheme grants
                    grants = jira_client.get_permission_scheme_grants(str(scheme_id))
                    logger.debug(f"Found {len(grants)} permission grants for project {project_key}")
                    
                    # Find BROWSE_PROJECTS permission grants
                    browse_grants = [g for g in grants if g.get('permission') == 'BROWSE_PROJECTS']
                    
                    # Process each BROWSE_PROJECTS grant
                    for grant in browse_grants:
                        users, groups = self._process_permission_grant(
                            jira_client, project_key, grant
                        )
                        
                        # Add users to our tracking set
                        all_users.update(users)
                        
                        # Add groups and their members
                        for group_name in groups:
                            if group_name not in all_groups:
                                all_groups[group_name] = {'members': set(), 'projects': set()}
                            
                            all_groups[group_name]['projects'].add(project_key)
                            
                            # Get group members
                            group_members = jira_client.get_group_members(group_name)
                            member_emails = []
                            for member in group_members:
                                email = member.get('emailAddress') or member.get('name')
                                if email:
                                    member_emails.append(email)
                                    all_users.add(email)
                            
                            all_groups[group_name]['members'].update(member_emails)
                    
                    stats['projects_processed'] += 1
                    
                except Exception as e:
                    logger.error(f"Error processing project {project.get('key', 'unknown')}: {e}")
                    continue
            
            # Step 3: Sync groups to Q Business
            logger.info(f"Syncing {len(all_groups)} groups to Q Business")
            for group_name, group_info in all_groups.items():
                try:
                    # Prepare group members for Q Business format
                    group_members = {
                        'memberUsers': [
                            {
                                'userId': user_email,
                                'type': 'DATASOURCE'
                            }
                            for user_email in group_info['members']
                        ]
                    }
                    
                    # Create/update group in Q Business
                    result = qbusiness_client.put_group(group_name, group_members)
                    if result['success']:
                        stats['groups_processed'] += 1
                        logger.debug(f"Successfully synced group: {group_name}")
                    else:
                        logger.warning(f"Failed to sync group {group_name}: {result['message']}")
                        
                except Exception as e:
                    logger.error(f"Error syncing group {group_name}: {e}")
                    continue
            
            # Step 4: Sync users to Q Business
            logger.info(f"Syncing {len(all_users)} users to Q Business")
            for user_email in all_users:
                try:
                    self._sync_user_to_qbusiness(qbusiness_client, user_email)
                    stats['users_processed'] += 1
                    
                except Exception as e:
                    logger.error(f"Error syncing user {user_email}: {e}")
                    continue
            
            logger.info(f"ACL synchronization completed successfully: {stats}")
            return {
                'success': True,
                'message': "ACL synchronization completed successfully",
                'stats': stats
            }
            
        except Exception as e:
            logger.error(f"Error during ACL synchronization: {e}")
            return {
                'success': False,
                'message': f"Failed to synchronize ACL: {e}",
                'stats': stats
            }
    
    def _process_permission_grant(self, jira_client, project_key: str, grant: Dict[str, Any]) -> tuple:
        """
        Process a permission grant to extract users and groups
        
        Args:
            jira_client: Jira client instance
            project_key: Project key
            grant: Permission grant object
            
        Returns:
            Tuple of (users_set, groups_set)
        """
        users = set()
        groups = set()
        
        holder = grant.get('holder', {})
        holder_type = holder.get('type')
        
        if holder_type == 'group':
            # Group-based permission
            group_name = holder.get('parameter')
            if group_name:
                groups.add(group_name)
                
        elif holder_type == 'user':
            # User-based permission
            user_name = holder.get('parameter')
            if user_name:
                users.add(user_name)
                
        elif holder_type == 'projectRole':
            # Role-based permission - get role actors
            role_id = holder.get('parameter')
            if role_id:
                role_actors = jira_client.get_project_role_actors(project_key, role_id)
                actors = role_actors.get('actors', [])
                
                for actor in actors:
                    actor_type = actor.get('type')
                    if actor_type == 'atlassian-group-role-actor':
                        group_name = actor.get('name')
                        if group_name:
                            groups.add(group_name)
                    elif actor_type == 'atlassian-user-role-actor':
                        user_name = actor.get('name')
                        if user_name:
                            users.add(user_name)
        
        return users, groups
    
    def _sync_user_to_qbusiness(self, qbusiness_client, user_email: str) -> None:
        """
        Sync a user to Q Business with proper create/update logic
        
        Args:
            qbusiness_client: Q Business client instance
            user_email: User email address
        """
        try:
            # Check if user exists
            user_result = qbusiness_client.get_user(user_email)
            
            # Prepare user aliases
            user_aliases = [
                {
                    'indexId': qbusiness_client.qbusiness_config.index_id,
                    'dataSourceId': qbusiness_client.qbusiness_config.data_source_id,
                    'userId': user_email
                }
            ]
            
            if user_result.get('user_exists', True):
                # User exists, update aliases
                result = qbusiness_client.update_user(user_email, user_aliases)
                if result['success']:
                    logger.debug(f"Updated user: {user_email}")
                else:
                    logger.warning(f"Failed to update user {user_email}: {result['message']}")
            else:
                # User doesn't exist, create new user
                result = qbusiness_client.create_user(user_email, user_aliases)
                if result['success']:
                    logger.debug(f"Created user: {user_email}")
                else:
                    logger.warning(f"Failed to create user {user_email}: {result['message']}")
                    
        except Exception as e:
            logger.error(f"Error syncing user {user_email} to Q Business: {e}")
            raise
    
    def get_document_acl(self, issue: Dict[str, Any], jira_client=None) -> Optional[Dict[str, Any]]:
        """
        Extract ACL information from a Jira issue for Q Business document
        
        Args:
            issue: Jira issue object
            jira_client: Jira client instance (optional, for enhanced ACL)
            
        Returns:
            Dictionary with ACL information in the format required by Amazon Q Business
            or None if no specific ACL restrictions apply
        """        
        try:
            fields = issue.get('fields', {})
            
            # Get project key for permission lookup
            project = fields.get('project')
            if not project or not isinstance(project, dict):
                logger.warning(f"No project found for issue {issue.get('key')}")
                return None
            
            project_key = project.get('key')
            if not project_key:
                logger.warning(f"No project key found for issue {issue.get('key')}")
                return None
            
            # Build access controls based on project permissions
            access_controls = []
            
            # If we have a jira_client, we can do enhanced ACL lookup
            if jira_client:
                try:
                    # Get project permission scheme
                    permission_scheme = jira_client.get_project_permission_scheme(project_key)
                    if permission_scheme:
                        scheme_id = permission_scheme.get('id')
                        if scheme_id:
                            # Get BROWSE_PROJECTS permissions
                            grants = jira_client.get_permission_scheme_grants(str(scheme_id))
                            browse_grants = [g for g in grants if g.get('permission') == 'BROWSE_PROJECTS']
                            
                            # Process each grant to build access controls
                            for grant in browse_grants:
                                users, groups = self._process_permission_grant(
                                    jira_client, project_key, grant
                                )
                                
                                # Add user permissions
                                for user_email in users:
                                    access_controls.append({
                                        'principals': [
                                            {
                                                'user': {
                                                    'id': user_email,
                                                    'access': 'ALLOW',
                                                    'membershipType': 'DATASOURCE'
                                                }
                                            }
                                        ]
                                    })
                                
                                # Add group permissions  
                                for group_name in groups:
                                    access_controls.append({
                                        'principals': [
                                            {
                                                'group': {
                                                    'name': group_name,
                                                    'access': 'ALLOW',
                                                    'membershipType': 'DATASOURCE'
                                                }
                                            }
                                        ]
                                    })
                    
                except Exception as e:
                    logger.warning(f"Error getting enhanced ACL for issue {issue.get('key')}: {e}")
            
            # If no specific access controls found, return default project-based access
            if not access_controls:
                # Default: allow users who can browse the project
                access_controls.append({
                    'principals': [
                        {
                            'group': {
                                'name': f'jira-project-{project_key}',
                                'access': 'ALLOW',
                                'membershipType': 'DATASOURCE'
                            }
                        }
                    ]
                })
            
            return {
                'accessConfiguration': {
                    'accessControls': access_controls
                }
            }
            
        except Exception as e:
            logger.error(f"Error extracting ACL information for issue {issue.get('key', 'unknown')}: {e}")
            return None

    # Keep the existing method for backward compatibility
    def get_principal_store_entries(self, jira_client) -> List[Dict[str, Any]]:
        """
        Generate principal store entries for Amazon Q Business User Store
        
        This method is kept for backward compatibility but the new
        sync_jira_acl_to_qbusiness method should be used instead.
        
        Args:
            jira_client: Jira client instance to fetch users and groups
            
        Returns:
            List of principal store entries in the format required by Amazon Q Business
        """        
        logger.warning("get_principal_store_entries is deprecated, use sync_jira_acl_to_qbusiness instead")
        return []