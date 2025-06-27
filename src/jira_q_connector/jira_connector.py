"""
Jira Q Business Connector for syncing Jira issues to Amazon Q Business
"""
import logging
from typing import Dict, List, Any, Optional

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
    
    def sync_issues_with_execution_id(self, execution_id: str, dry_run: bool = False, clean_first: bool = False) -> Dict[str, Any]:
        """
        Sync Jira issues to Q Business with the given execution ID
        
        Args:
            execution_id: The execution ID of the sync job
            dry_run: If True, don't actually upload documents
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
            
            # Build JQL query for filtering
            jql_parts = []
            
            # Add project filter if specified
            if self.config.projects:
                project_list = "','".join(self.config.projects)
                jql_parts.append(f"project in ('{project_list}')")
            
            # Add issue type filter if specified
            if self.config.issue_types:
                issue_type_list = "','".join(self.config.issue_types)
                jql_parts.append(f"issuetype in ('{issue_type_list}')")
            
            # Add custom JQL filter if specified
            if self.config.jql_filter:
                jql_parts.append(f"({self.config.jql_filter})")
            
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
            
            # Initialize document processor
            from .document_processor import JiraDocumentProcessor
            doc_processor = JiraDocumentProcessor(
                include_comments=self.config.include_comments,
                include_history=self.config.include_history
            )
            
            # Process issues in batches
            batch_size = min(self.config.batch_size, 10)  # AWS Q Business limit is 10
            total_issues = 0
            
            # First, get total count for progress tracking
            search_result = self.jira_client.search_issues(
                jql=jql_query,
                start_at=0,
                max_results=1  # Just to get total count
            )
            total_available = search_result.get('total', 0)
            logger.info(f"Found {total_available} total issues matching criteria")
            
            # Process all issues using iterator
            issues_batch = []
            
            for issue in self.jira_client.get_all_issues_iterator(
                jql=jql_query,
                batch_size=100  # Fetch from Jira in larger batches
            ):
                issues_batch.append(issue)
                total_issues += 1
                
                # Process batch when it reaches the size limit
                if len(issues_batch) >= batch_size:
                    batch_stats = self._process_issues_batch(
                        issues_batch, doc_processor, execution_id, dry_run
                    )
                    stats['uploaded_documents'] += batch_stats['uploaded']
                    
                    logger.info(f"Processed batch: {len(issues_batch)} issues, "
                              f"uploaded: {batch_stats['uploaded']}")
                    
                    # Clear batch for next iteration
                    issues_batch = []
            
            # Process remaining issues in the final batch
            if issues_batch:
                batch_stats = self._process_issues_batch(
                    issues_batch, doc_processor, execution_id, dry_run
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
    
    def _process_issues_batch(self, issues: List[Dict[str, Any]], doc_processor, execution_id: str, dry_run: bool) -> Dict[str, int]:
        """
        Process a batch of issues and upload to Q Business
        
        Args:
            issues: List of Jira issues to process
            doc_processor: Document processor instance
            execution_id: Q Business sync job execution ID
            dry_run: If True, don't actually upload
            
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
                    
                except Exception as e:
                    logger.error(f"Failed to process issue {issue.get('key', 'unknown')}: {e}")
                    continue
            
            # Upload documents to Q Business if not dry run
            if documents and not dry_run:
                upload_result = self.qbusiness_client.batch_put_documents_with_execution_id(
                    documents, execution_id
                )
                
                if upload_result['success']:
                    stats['uploaded'] = len(documents)
                else:
                    logger.error(f"Failed to upload batch: {upload_result['message']}")
            elif documents and dry_run:
                stats['uploaded'] = len(documents)
                logger.info(f"Dry run: Would upload {len(documents)} documents")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error processing batch: {e}")
            return stats
    
    def sync_acl_with_execution_id(self, execution_id: str) -> Dict[str, Any]:
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
            result = self.acl_manager.sync_jira_acl_to_qbusiness(self.jira_client, self.qbusiness_client)
            
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