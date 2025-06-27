"""
Amazon Q Business Client for interacting with the Q Business API
"""
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class QBusinessClient:
    """Client for interacting with Amazon Q Business API"""
    
    def __init__(self, aws_config, qbusiness_config):
        """
        Initialize the Q Business client
        
        Args:
            aws_config: AWS configuration
            qbusiness_config: Q Business configuration
        """
        self.aws_config = aws_config
        self.qbusiness_config = qbusiness_config
        
        # Initialize boto3 client
        import boto3
        self.client = boto3.client(
            'qbusiness',
            region_name=aws_config.region
        )
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to Q Business
        
        Returns:
            Dictionary with test results
        """
        try:
            # For testing purposes, just check if we can list applications
            # This avoids the need for a specific application ID during testing
            response = self.client.list_applications()
            
            return {
                'success': True,
                'message': f"Connected to Q Business service",
                'application_info': {
                    'applications_count': len(response.get('applications', [])),
                    'service': 'qbusiness'
                }
            }
        except Exception as e:
            logger.error(f"Error connecting to Q Business: {e}")
            return {
                'success': False,
                'message': f"Failed to connect to Q Business: {e}"
            }
    
    def start_data_source_sync(self) -> Dict[str, Any]:
        """
        Start a data source sync job
        
        Returns:
            Dictionary with sync job information
        """
        try:
            response = self.client.start_data_source_sync_job(
                applicationId=self.qbusiness_config.application_id,
                indexId=self.qbusiness_config.index_id,
                dataSourceId=self.qbusiness_config.data_source_id
            )
            
            execution_id = response.get('executionId')
            
            return {
                'success': True,
                'message': f"Started sync job with execution ID: {execution_id}",
                'execution_id': execution_id
            }
        except Exception as e:
            logger.error(f"Error starting sync job: {e}")
            return {
                'success': False,
                'message': f"Failed to start sync job: {e}"
            }
    
    def stop_data_source_sync(self, execution_id: str) -> Dict[str, Any]:
        """
        Stop a data source sync job
        
        Args:
            execution_id: The execution ID of the sync job (not used by API, kept for compatibility)
            
        Returns:
            Dictionary with sync job information
        """
        try:
            # Note: AWS Q Business stop_data_source_sync_job API doesn't accept executionId
            # It simply stops the currently running sync job for the data source
            self.client.stop_data_source_sync_job(
                applicationId=self.qbusiness_config.application_id,
                indexId=self.qbusiness_config.index_id,
                dataSourceId=self.qbusiness_config.data_source_id
            )
            
            return {
                'success': True,
                'message': f"Stopped sync job (execution ID was: {execution_id})"
            }
        except Exception as e:
            logger.error(f"Error stopping sync job: {e}")
            return {
                'success': False,
                'message': f"Failed to stop sync job: {e}"
            }
    
    def get_data_source_sync_job(self, execution_id: str) -> Dict[str, Any]:
        """
        Get the status of a data source sync job
        
        Args:
            execution_id: The execution ID of the sync job
            
        Returns:
            Dictionary with sync job information
        """
        try:
            response = self.client.get_data_source_sync_job(
                applicationId=self.qbusiness_config.application_id,
                indexId=self.qbusiness_config.index_id,
                dataSourceId=self.qbusiness_config.data_source_id,
                executionId=execution_id
            )
            
            return {
                'success': True,
                'message': f"Retrieved sync job status",
                'job': response
            }
        except Exception as e:
            logger.error(f"Error getting sync job status: {e}")
            return {
                'success': False,
                'message': f"Failed to get sync job status: {e}"
            }
    
    def list_data_source_sync_jobs(self, max_results: int = 10) -> Dict[str, Any]:
        """
        List data source sync jobs
        
        Args:
            max_results: Maximum number of results to return
            
        Returns:
            Dictionary with sync jobs information
        """
        try:
            response = self.client.list_data_source_sync_jobs(
                applicationId=self.qbusiness_config.application_id,
                indexId=self.qbusiness_config.index_id,
                dataSourceId=self.qbusiness_config.data_source_id,
                maxResults=max_results
            )
            
            return {
                'success': True,
                'message': f"Retrieved sync jobs",
                'sync_jobs': response.get('syncJobs', [])
            }
        except Exception as e:
            logger.error(f"Error listing sync jobs: {e}")
            return {
                'success': False,
                'message': f"Failed to list sync jobs: {e}"
            }
    
    def batch_put_documents_with_execution_id(self, documents: List[Dict[str, Any]], execution_id: str) -> Dict[str, Any]:
        """
        Upload documents to Q Business with execution ID
        
        Args:
            documents: List of Q Business documents to upload
            execution_id: The sync job execution ID
            
        Returns:
            Dictionary with upload results
        """
        try:
            if not documents:
                return {
                    'success': True,
                    'message': "No documents to upload",
                    'uploaded_count': 0
                }
            
            # AWS Q Business BatchPutDocument has a limit of 10 documents per batch
            batch_size = min(len(documents), 10)
            
            if len(documents) > batch_size:
                logger.warning(f"Document batch size {len(documents)} exceeds limit of {batch_size}, truncating")
                documents = documents[:batch_size]
            
            # Add execution ID to each document's attributes
            for doc in documents:
                if 'attributes' not in doc:
                    doc['attributes'] = []
            
            # Upload documents
            logger.info(f"Uploading {len(documents)} documents to Q Business...")
            response = self.client.batch_put_document(
                applicationId=self.qbusiness_config.application_id,
                indexId=self.qbusiness_config.index_id,
                documents=documents,
                dataSourceSyncId=execution_id
            )
            
            # Check for failed documents
            failed_docs = response.get('failedDocuments', [])
            successful_count = len(documents) - len(failed_docs)
            
            if failed_docs:
                logger.warning(f"Failed to upload {len(failed_docs)} out of {len(documents)} documents")
                
                for failed_doc in failed_docs:
                    doc_id = failed_doc.get('id', 'unknown')
                    
                    # Handle nested error structure
                    error_obj = failed_doc.get('error', {})
                    if error_obj:
                        error_code = error_obj.get('errorCode', 'unknown')
                        error_message = error_obj.get('errorMessage', 'Unknown error')
                    else:
                        # Fallback to old format
                        error_code = failed_doc.get('errorCode', 'unknown')
                        error_message = failed_doc.get('errorMessage', 'Unknown error')
                    
                    logger.error(f"Document {doc_id} failed: {error_code} - {error_message}")
            
            return {
                'success': True,
                'message': f"Uploaded {successful_count} out of {len(documents)} documents",
                'uploaded_count': successful_count,
                'failed_count': len(failed_docs),
                'failed_documents': failed_docs
            }
            
        except Exception as e:
            logger.error(f"Error uploading documents: {str(e)}")
            logger.error(f"Exception type: {type(e).__name__}")
            
            # Handle specific boto3 ClientError
            if hasattr(e, 'response') and 'Error' in e.response:
                error_info = e.response['Error']
                error_code = error_info.get('Code', 'Unknown')
                error_message = error_info.get('Message', 'Unknown')
                logger.error(f"AWS Error Code: {error_code}")
                logger.error(f"AWS Error Message: {error_message}")
                
                # Log the full response for debugging
                logger.error(f"Full AWS Error Response: {e.response}")
            
            # Handle other boto3 exceptions
            elif hasattr(e, 'operation_name'):
                logger.error(f"AWS Operation: {e.operation_name}")
                if hasattr(e, 'args') and e.args:
                    logger.error(f"AWS Exception args: {e.args}")
            
            # Generic exception handling
            else:
                logger.error(f"Non-AWS Exception: {str(e)}")
                if hasattr(e, '__dict__'):
                    logger.error(f"Exception attributes: {e.__dict__}")
            
            # Import traceback to get full stack trace
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
                
            return {
                'success': False,
                'message': f"Failed to upload documents: {str(e)}",
                'uploaded_count': 0
            }
    
    def get_data_source_sync_job_metrics(self, execution_id: str) -> Dict[str, Any]:
        """
        Get metrics for a data source sync job
        
        Args:
            execution_id: The execution ID of the sync job
            
        Returns:
            Dictionary with sync job metrics
        """
        try:
            response = self.client.get_data_source_sync_job_metrics(
                applicationId=self.qbusiness_config.application_id,
                indexId=self.qbusiness_config.index_id,
                dataSourceId=self.qbusiness_config.data_source_id,
                executionId=execution_id
            )
            
            return {
                'success': True,
                'message': f"Retrieved sync job metrics",
                'metrics': response.get('metrics', {})
            }
        except Exception as e:
            logger.error(f"Error getting sync job metrics: {e}")
            return {
                'success': False,
                'message': f"Failed to get sync job metrics: {e}"
            }
    
    def batch_put_user_store_entries(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Put entries in the User Store using appropriate AWS Q Business APIs
        
        Args:
            entries: List of principal store entries (users and groups)
            
        Returns:
            Dictionary with result information
        """
        try:
            total_processed = 0
            failed_entries = []
            users_processed = 0
            groups_processed = 0
            
            for entry in entries:
                try:
                    operation = entry.get('operation', 'PUT')
                    principal = entry.get('principal', {})
                    principal_type = principal.get('principalType')
                    principal_id = principal.get('principalId')
                    
                    if not principal_id:
                        logger.warning(f"Skipping entry with missing principal ID: {entry}")
                        continue
                        
                    if principal_type == 'USER':
                        # Use create_user for users (will update if exists)
                        self._create_or_update_user(principal)
                        users_processed += 1
                        
                    elif principal_type == 'GROUP':
                        # Use put_group for groups 
                        self._create_or_update_group(principal)
                        groups_processed += 1
                        
                    else:
                        logger.warning(f"Unknown principal type: {principal_type}")
                        continue
                    
                    total_processed += 1
                    logger.debug(f"Successfully processed {principal_type}: {principal_id}")
                    
                except Exception as e:
                    logger.error(f"Failed to process entry {entry.get('principal', {}).get('principalId', 'unknown')}: {e}")
                    failed_entries.append({
                        'entry': entry,
                        'error': str(e)
                    })
            
            if failed_entries:
                message = f"Processed {total_processed} entries ({users_processed} users, {groups_processed} groups) with {len(failed_entries)} failures"
            else:
                message = f"Successfully processed {total_processed} entries ({users_processed} users, {groups_processed} groups)"
                
            return {
                'success': True,
                'message': message,
                'failed_entries': failed_entries,
                'users_processed': users_processed,
                'groups_processed': groups_processed
            }
        except Exception as e:
            logger.error(f"Error putting user store entries: {e}")
            return {
                'success': False,
                'message': f"Failed to put user store entries: {e}"
            }
    
    def _create_or_update_user(self, principal: Dict[str, Any]) -> None:
        """Create or update a user in Q Business"""
        principal_id = principal.get('principalId')
        metadata = principal.get('metadata', {})
        
        # Build user aliases with proper format
        user_aliases = []
        if metadata.get('email'):
            user_aliases.append({
                'indexId': self.qbusiness_config.index_id,
                'dataSourceId': self.qbusiness_config.data_source_id,
                'userId': metadata.get('email')
            })
        
        try:
            # Try to create user (this will fail if user exists)
            self.client.create_user(
                applicationId=self.qbusiness_config.application_id,
                userId=principal_id,
                userAliases=user_aliases
            )
            logger.debug(f"Created user: {principal_id}")
        except Exception as e:
            # If user exists, try to update
            if 'ConflictException' in str(e) or 'already exists' in str(e).lower():
                try:
                    self.client.update_user(
                        applicationId=self.qbusiness_config.application_id,
                        userId=principal_id,
                        userAliases=user_aliases
                    )
                    logger.debug(f"Updated user: {principal_id}")
                except Exception as update_e:
                    logger.warning(f"Failed to update user {principal_id}: {update_e}")
                    raise update_e
            else:
                logger.warning(f"Failed to create user {principal_id}: {e}")
                raise e
    
    def _create_or_update_group(self, principal: Dict[str, Any]) -> None:
        """Create or update a group in Q Business"""
        principal_id = principal.get('principalId')
        
        # Create basic group with no members initially
        self.client.put_group(
            applicationId=self.qbusiness_config.application_id,
            indexId=self.qbusiness_config.index_id,
            groupName=principal_id,
            dataSourceId=self.qbusiness_config.data_source_id,
            type='DATASOURCE',
            groupMembers={
                'memberUsers': [],
                'memberGroups': []
            }
        )
        logger.debug(f"Created/updated group: {principal_id}")

    def put_group(self, group_name: str, group_members: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Put a group with its members in Q Business
        
        Args:
            group_name: Name of the group
            group_members: Dictionary with memberUsers and memberGroups lists
            
        Returns:
            Dictionary with result information
        """
        try:
            self.client.put_group(
                applicationId=self.qbusiness_config.application_id,
                indexId=self.qbusiness_config.index_id,
                groupName=group_name,
                dataSourceId=self.qbusiness_config.data_source_id,
                type='DATASOURCE',
                groupMembers=group_members
            )
            
            return {
                'success': True,
                'message': f"Successfully created/updated group: {group_name}"
            }
        except Exception as e:
            logger.error(f"Error creating/updating group {group_name}: {e}")
            return {
                'success': False,
                'message': f"Failed to create/update group {group_name}: {e}"
            }
    
    def get_user(self, user_id: str) -> Dict[str, Any]:
        """
        Get user information from Q Business
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with user information or error
        """
        try:
            response = self.client.get_user(
                applicationId=self.qbusiness_config.application_id,
                userId=user_id
            )
            
            return {
                'success': True,
                'user': response
            }
        except Exception as e:
            if 'ResourceNotFoundException' in str(e):
                return {
                    'success': False,
                    'message': 'User not found',
                    'user_exists': False
                }
            else:
                logger.error(f"Error getting user {user_id}: {e}")
                return {
                    'success': False,
                    'message': f"Failed to get user {user_id}: {e}"
                }
    
    def create_user(self, user_id: str, user_aliases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create a user in Q Business
        
        Args:
            user_id: User ID
            user_aliases: List of user aliases
            
        Returns:
            Dictionary with result information
        """
        try:
            self.client.create_user(
                applicationId=self.qbusiness_config.application_id,
                userId=user_id,
                userAliases=user_aliases
            )
            
            return {
                'success': True,
                'message': f"Successfully created user: {user_id}"
            }
        except Exception as e:
            logger.error(f"Error creating user {user_id}: {e}")
            return {
                'success': False,
                'message': f"Failed to create user {user_id}: {e}"
            }
    
    def update_user(self, user_id: str, user_aliases: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Update a user in Q Business
        
        Args:
            user_id: User ID
            user_aliases: List of user aliases to update
            
        Returns:
            Dictionary with result information
        """
        try:
            params = {
                'applicationId': self.qbusiness_config.application_id,
                'userId': user_id
            }
            
            if user_aliases:
                params['userAliasesToUpdate'] = user_aliases
            
            self.client.update_user(**params)
            
            return {
                'success': True,
                'message': f"Successfully updated user: {user_id}"
            }
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            return {
                'success': False,
                'message': f"Failed to update user {user_id}: {e}"
            }