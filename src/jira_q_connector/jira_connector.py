"""
Jira Q Business Connector for syncing Jira issues to Amazon Q Business
"""
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from aws_lambda_powertools.utilities.idempotency import (
    IdempotencyConfig, DynamoDBPersistenceLayer, idempotent, idempotent_function
)
import functools
import boto3


from .jira_client import JiraClient
from .acl_manager import ACLManager

logger = logging.getLogger(__name__)

class JiraQBusinessConnector:
    """
    Connector for syncing Jira issues to Amazon Q Business
    
    This class handles the synchronization of Jira issues to Amazon Q Business,
    including document creation, ACL synchronization, and sync job management.
    """
    
    def __init__(self, config):
        """
        Initialize the connector
        
        Args:
            config: Configuration object with Jira and Q Business settings
        """
        self.config = config
        self.jira_client = JiraClient(config.jira)
        
        # Initialize ACL manager (always enabled)
        self.acl_manager = ACLManager()
    
        
        # Initialize Q Business client
        from .qbusiness_client import QBusinessClient
        self.qbusiness_client = QBusinessClient(config.aws, config.qbusiness)

        # Initialize Q Idempotency Config
        self.idempotency_config = IdempotencyConfig(
            event_key_jmespath="[key, fields.updated]",
            raise_on_no_idempotency_key=True,
            expires_after_seconds = 259200          # 3 days
        )
        self.persistent_store = DynamoDBPersistenceLayer(table_name=self.config.cache_table_name)
    
    def test_connections(self) -> Dict[str, Any]:
        """
        Test connections to Jira and Q Business
        
        Returns:
            Dictionary with test results
        """
        # Test Jira connection
        jira_result = self.jira_client.test_connection()
        
        # Test Q Business connection
        qbusiness_result = self.qbusiness_client.test_connection()
        
        # Overall success
        overall_success = jira_result['success'] and qbusiness_result['success']
        
        return {
            'overall_success': overall_success,
            'jira': jira_result,
            'qbusiness': qbusiness_result
        }
    
    def start_qbusiness_sync(self) -> Dict[str, Any]:
        """
        Start a Q Business data source sync job
        
        Returns:
            Dictionary with sync job information
        """
        return self.qbusiness_client.start_data_source_sync()
    
    def stop_qbusiness_sync(self, execution_id: str) -> Dict[str, Any]:
        """
        Stop a Q Business data source sync job
        
        Args:
            execution_id: The execution ID of the sync job
            
        Returns:
            Dictionary with sync job information
        """
        return self.qbusiness_client.stop_data_source_sync(execution_id)
    
    def get_sync_job_status(self, execution_id: str) -> Dict[str, Any]:
        """
        Get the status of a Q Business data source sync job
        
        Args:
            execution_id: The execution ID of the sync job
            
        Returns:
            Dictionary with sync job information
        """
        return self.qbusiness_client.get_data_source_sync_job(execution_id)
    
    def clean_all_documents(self, execution_id: str) -> Dict[str, Any]:
        """
        Clean all documents from Q Business
        
        Args:
            execution_id: The execution ID of the sync job
            
        Returns:
            Dictionary with clean results
        """
        logger.warning("Document cleaning is not implemented - skipping clean operation")
        return {
            'success': False,
            'message': "Document cleaning is not implemented",
            'deleted': 0
        }
    
    def sync_issues_with_execution_id(self, execution_id: str, clean_first: bool = False, sync_plan: dict = None) -> Dict[str, Any]:
        """
        Sync Jira issues to Q Business with the given execution ID
        
        Args:
            execution_id: The execution ID of the sync job
            clean_first: If True, clean all documents before syncing
            
        Returns:
            Dictionary with sync results
        """
        try:
            logger.info(f"Starting sync of Jira issues with execution ID: {execution_id}")
            
            # Initialize stats
            stats = {
                'processed_issues': 0,
                'uploaded_documents': 0,
                'deleted_documents': 0
            }
            
            sync_plan = sync_plan or {}
            start_at = sync_plan.get('start_at', 0) 
            total_available = sync_plan.get('max_results', None) 
            project = sync_plan.get('project', None)

            # Build JQL query
            jql_query = self._build_jql_query(project=project)
            
            # Initialize document processor
            from .document_processor import JiraDocumentProcessor
            doc_processor = JiraDocumentProcessor(
                include_comments=self.config.include_comments,
                include_history=self.config.include_history
            )
            
            # Process issues in batches
            batch_size = min(self.config.batch_size, 10)
            total_issues = 0
            
            # First, get total count for progress tracking
            if not total_available:
                search_result = self.jira_client.search_issues(
                    jql=jql_query,
                    start_at=0,
                    max_results=1  # Just to get total count
                )
                total_available = search_result.get('total', 0)
            logger.info(f"Found {total_available} total issues matching criteria")
            
            # Process all issues using iterator
            issues_batch = []
            idempotency_config = self.idempotency_config
            persistence_store = self.persistent_store

            for issue in self.jira_client.get_all_issues_iterator(
                jql=jql_query,
                start_at=start_at,
                batch_size=100  # Fetch from Jira in larger batches
            ):
                @idempotent_function(
                    data_keyword_argument="issue",
                    config=idempotency_config,
                    persistence_store=persistence_store
                )
                def process_single_issue(issue):
                    nonlocal issues_batch, total_issues
                    issues_batch.append(issue)
                    total_issues += 1

                    logger.debug(f"Processing issue with key: {issue.get('key', '')}")

                    # Process batch when it reaches the size limit
                    if len(issues_batch) >= batch_size:
                        batch_stats = self._process_issues_batch(
                            issues_batch, doc_processor, execution_id
                        )
                        stats['uploaded_documents'] += batch_stats['uploaded']
                        
                        logger.info(f"Processed batch: {len(issues_batch)} issues, "
                                f"uploaded: {batch_stats['uploaded']}")
                        
                        # Clear batch for next iteration
                        issues_batch.clear()
                        
                # Call the function
                process_single_issue(issue=issue)
            
            # Process remaining issues in the final batch
            if issues_batch:
                batch_stats = self._process_issues_batch(
                    issues_batch, doc_processor, execution_id
                )
                stats['uploaded_documents'] += batch_stats['uploaded']
                
                logger.info(f"Processed final batch: {len(issues_batch)} issues, "
                          f"uploaded: {batch_stats['uploaded']}")
            
            stats['processed_issues'] = total_issues
            
            logger.info(f"Sync completed successfully. Processed {total_issues} issues, "
                      f"uploaded {stats['uploaded_documents']} documents")
            
            return {
                'success': True,
                'message': "Issues synced successfully",
                'stats': stats
            }
            
        except Exception as e:
            logger.error(f"Error syncing issues: {e}")
            return {
                'success': False,
                'message': f"Failed to sync issues: {e}",
                'stats': stats if 'stats' in locals() else {
                    'processed_issues': 0,
                    'uploaded_documents': 0,
                    'deleted_documents': 0
                }
            }
    
    def _process_issues_batch(self, issues: List[Dict[str, Any]], doc_processor, execution_id: str) -> Dict[str, int]:
        """
        Process a batch of issues and upload to Q Business
        
        Args:
            issues: List of Jira issues to process
            doc_processor: Document processor instance
            execution_id: Q Business sync job execution ID
            
        Returns:
            Dictionary with batch processing stats
        """
        stats = {'uploaded': 0}
        
        if not issues:
            return stats
        
        try:
            # Convert issues to Q Business documents
            documents = []
            
            for issue in issues:
                try:
                    # Process issue to Q Business document
                    doc = doc_processor.process_issue(issue, execution_id)
                    
                    if doc:
                        # Add ACL information to the document
                        acl_info = self.acl_manager.get_document_acl(issue, jira_client=self.jira_client)
                        if acl_info:
                            doc.update(acl_info)
                        
                        documents.append(doc)
                    
                    # Process issue attachments to Q Business document
                    attachments = issue.get('fields', {}).get('attachment', [])
                    if doc and attachments and self.jira_client:
                        for attachment in attachments:
                            
                            mime_type = attachment.get('mimeType', '').lower()
                            if not ('pdf' in mime_type or 
                                    'word' in mime_type or 
                                    'doc' in mime_type or
                                    'powerpoint' in mime_type or
                                    'ppt' in mime_type):
                                continue

                            attach_doc = doc_processor.process_attachment(issue, attachment, execution_id, jira_client=self.jira_client)
                            if attach_doc:
                                documents.append(attach_doc)

                except Exception as e:
                    logger.error(f"Failed to process issue {issue.get('key', 'unknown')}: {e}")
                    continue
            
            # Upload documents to Q Business
            if documents:
                upload_result = self.qbusiness_client.batch_put_documents_with_execution_id(
                    documents, execution_id
                )
                
                if upload_result['success']:
                    stats['uploaded'] = len(documents)
                else:
                    logger.error(f"Failed to upload batch: {upload_result['message']}")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error processing batch: {e}")
            return stats
    
    def sync_acl_with_execution_id(self, execution_id: str, project_keys: list = None) -> Dict[str, Any]:
        """
        Synchronize ACL information with Q Business User Store
        
        Args:
            execution_id: The execution ID of the sync job
            
        Returns:
            Dictionary with sync results
        """
        try:
            logger.info(f"Starting comprehensive ACL synchronization with execution ID: {execution_id}")
            
            # ACL is always enabled now, but check if acl_manager exists
            if not hasattr(self, 'acl_manager') or self.acl_manager is None:
                logger.warning("ACL manager not initialized - this should not happen")
                return {
                    'success': False,
                    'message': "ACL manager not initialized",
                    'stats': {'users': 0, 'groups': 0, 'memberships': 0}
                }
            
            # Use the new comprehensive ACL sync method
            result = self.acl_manager.sync_jira_acl_to_qbusiness(self.jira_client, self.qbusiness_client, project_keys)
            
            # Transform stats format for backward compatibility
            if result.get('success') and 'stats' in result:
                original_stats = result['stats']
                transformed_stats = {
                    'users': original_stats.get('users_processed', 0),
                    'groups': original_stats.get('groups_processed', 0),
                    'memberships': original_stats.get('projects_processed', 0)  # Use projects as memberships proxy
                }
                result['stats'] = transformed_stats
            
            return result
            
        except Exception as e:
            logger.error(f"Error synchronizing ACL information: {e}")
            return {
                'success': False,
                'message': f"Failed to synchronize ACL information: {e}",
                'stats': {'users': 0, 'groups': 0, 'memberships': 0}
            }

    
    def cleanup(self):
        """Clean up resources"""
        if hasattr(self, 'jira_client'):
            self.jira_client.close()

    def _build_jql_query(self, project: str = None) -> str:
        """Build JQL query based on configuration"""

        # Build JQL query for filtering
        jql_parts = []
        
        # Add project filter if specified
        if project is not None:
            jql_parts.append(f"project in ('{project}')")
        elif self.config.projects:
            project_list = "','".join(self.config.projects)
            jql_parts.append(f"project in ('{project_list}')")
        
        # Add issue type filter if specified
        if self.config.issue_types:
            issue_type_list = "','".join(self.config.issue_types)
            jql_parts.append(f"issuetype in ('{issue_type_list}')")
        
        # Add custom JQL filter if specified
        if self.config.jql_filter:
            jql_parts.append(f"({self.config.jql_filter})")

        # Add last sync run date JQL filter to get incremental data        
        jql_parts.append(f"updated >= '{self.config.last_sync_date}'")
        
        # Build final JQL query
        if jql_parts:
            jql_query = ' AND '.join(jql_parts)
        else:
            jql_query = ""
        
        # Add default ordering
        if jql_query:
            jql_query += " ORDER BY updated DESC"
        else:
            jql_query = "ORDER BY updated DESC"
        
        logger.info(f"Using JQL query: {jql_query}")
        return jql_query

    def build_jira_acl_sync_plan(self, execution_id: str) -> Dict[str, Any]:
        """Build Jira ACL Sync plan"""
        sync_plan = []

        if self.config.projects:
            projects = self.config.projects
        else:
            projects = [project.get('key') for project in self.jira_client.get_projects()]
        logger.info(f"Creating Jira ACL Sync plan for Projects - {projects}")
        
        sync_plan = [{"projects": projects[i:i+1], "acl_sync": True, "execution_id": execution_id} for i in range(0, len(projects), 1)]
        
        return sync_plan        

    def build_jira_issues_sync_plan(self, execution_id: str) -> Dict[str, Any]:
        """Build Jira Issues Sync plan"""
        sync_plan = []

        if self.config.projects:
            projects = self.config.projects
        else:
            projects = [project.get('key') for project in self.jira_client.get_projects()]
        logger.info(f"Creating Jira Issues Sync plan for Projects - {projects}")

        for project in projects:
            jql_query = self._build_jql_query(project) 
            initial_result = self.jira_client.search_issues(jql=jql_query, start_at=0, max_results=1)
            total_issues = initial_result.get('total', 0)
            max_results_per_page = 100
            total_pages = (total_issues + max_results_per_page - 1) // max_results_per_page
            for page in range(1, total_pages + 1):
                start_at = (page - 1) * max_results_per_page
                max_results = min(total_issues - start_at, max_results_per_page)
                sync_plan.append({
                    "project": project,
                    "page": page,
                    "start_at": start_at,
                    "max_results": max_results,
                    "execution_id": execution_id,
                    "issues_sync": True
                })
        return sync_plan
    