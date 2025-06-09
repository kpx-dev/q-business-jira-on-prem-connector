"""
Main Jira Custom Connector for Amazon Q Business
"""
import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json

from config import ConnectorConfig
from jira_client import JiraClient
from document_processor import JiraDocumentProcessor
from qbusiness_client import QBusinessClient

logger = logging.getLogger(__name__)


class JiraQBusinessConnector:
    """Main connector class for syncing Jira to Q Business"""
    
    def __init__(self, config: ConnectorConfig):
        self.config = config
        self.jira_client = JiraClient(config.jira)
        self.qbusiness_client = QBusinessClient(config.aws)
        self.document_processor = JiraDocumentProcessor(
            include_comments=config.include_comments,
            include_history=config.include_history
        )
        
        # Sync state
        self.sync_stats = {
            'total_issues': 0,
            'processed_issues': 0,
            'uploaded_documents': 0,
            'failed_documents': 0,
            'start_time': None,
            'end_time': None,
            'errors': []
        }
    
    def test_connections(self) -> Dict[str, Any]:
        """Test connections to both Jira and Q Business"""
        results = {
            'jira': None,
            'qbusiness': None,
            'overall_success': False
        }
        
        # Test Jira connection
        logger.info("Testing Jira connection...")
        jira_result = self.jira_client.test_connection()
        results['jira'] = jira_result
        
        if jira_result['success']:
            logger.info(f"✓ Jira: {jira_result['message']}")
        else:
            logger.error(f"✗ Jira: {jira_result['message']}")
        
        # Test Q Business connection
        logger.info("Testing Q Business connection...")
        qb_result = self.qbusiness_client.test_connection()
        results['qbusiness'] = qb_result
        
        if qb_result['success']:
            logger.info(f"✓ Q Business: {qb_result['message']}")
        else:
            logger.error(f"✗ Q Business: {qb_result['message']}")
        
        results['overall_success'] = jira_result['success'] and qb_result['success']
        
        return results
    
    def build_jql_query(self) -> str:
        """Build JQL query based on configuration"""
        conditions = []
        
        # Add project filter
        if self.config.projects:
            project_list = "', '".join(self.config.projects)
            conditions.append(f"project in ('{project_list}')")
        
        # Add issue type filter
        if self.config.issue_types:
            type_list = "', '".join(self.config.issue_types)
            conditions.append(f"issuetype in ('{type_list}')")
        
        # Add incremental sync filter
        if self.config.sync_mode == 'incremental':
            # For incremental sync, get issues updated in the last 24 hours
            # In a real implementation, you'd store the last sync time
            yesterday = datetime.now() - timedelta(days=1)
            conditions.append(f"updated >= '{yesterday.strftime('%Y-%m-%d')}'")
        
        # Add custom JQL filter
        if self.config.jql_filter:
            conditions.append(f"({self.config.jql_filter})")
        
        # Combine conditions
        if conditions:
            jql = " AND ".join(conditions)
        else:
            jql = ""
        
        # Add ordering
        jql += " ORDER BY updated DESC"
        
        logger.info(f"Built JQL query: {jql}")
        return jql
    
    def sync_issues(self, dry_run: bool = False) -> Dict[str, Any]:
        """Sync Jira issues to Q Business"""
        logger.info(f"Starting {'dry run' if dry_run else 'sync'} of Jira issues to Q Business")
        
        self.sync_stats['start_time'] = datetime.now()
        
        try:
            # Build JQL query
            jql_query = self.build_jql_query()
            
            # Get total count first
            logger.info("Getting total issue count...")
            initial_result = self.jira_client.search_issues(jql=jql_query, max_results=1)
            total_issues = initial_result.get('total', 0)
            
            if total_issues == 0:
                logger.info("No issues found matching criteria")
                return self._build_sync_result(success=True, message="No issues to sync")
            
            logger.info(f"Found {total_issues} issues to sync")
            self.sync_stats['total_issues'] = total_issues
            
            # Process issues in batches
            processed_count = 0
            batch_count = 0
            
            for batch_issues in self._get_issues_in_batches(jql_query):
                batch_count += 1
                batch_size = len(batch_issues)
                logger.info(f"Processing batch {batch_count} ({batch_size} issues)")
                
                try:
                    # Convert issues to documents
                    documents = self.document_processor.create_batch_documents(batch_issues)
                    
                    if not documents:
                        logger.warning(f"No valid documents created from batch {batch_count}")
                        continue
                    
                    if dry_run:
                        logger.info(f"DRY RUN: Would upload {len(documents)} documents")
                        self.sync_stats['uploaded_documents'] += len(documents)
                    else:
                        # Upload to Q Business
                        upload_result = self.qbusiness_client.batch_put_documents(documents)
                        
                        if upload_result['success']:
                            self.sync_stats['uploaded_documents'] += upload_result['processed']
                            self.sync_stats['failed_documents'] += upload_result['failed']
                            
                            if upload_result['failed'] > 0:
                                logger.warning(f"Batch {batch_count}: {upload_result['failed']} documents failed to upload")
                        else:
                            logger.error(f"Batch {batch_count} upload failed: {upload_result['message']}")
                            self.sync_stats['errors'].append(f"Batch {batch_count}: {upload_result['message']}")
                    
                    processed_count += batch_size
                    self.sync_stats['processed_issues'] = processed_count
                    
                    # Progress logging
                    progress = (processed_count / total_issues) * 100
                    logger.info(f"Progress: {processed_count}/{total_issues} ({progress:.1f}%)")
                    
                    # Rate limiting - be nice to Jira server
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Error processing batch {batch_count}: {e}")
                    self.sync_stats['errors'].append(f"Batch {batch_count}: {str(e)}")
                    continue
            
            self.sync_stats['end_time'] = datetime.now()
            
            # Build result
            success = len(self.sync_stats['errors']) == 0
            duration = (self.sync_stats['end_time'] - self.sync_stats['start_time']).total_seconds()
            
            message = (f"{'Dry run' if dry_run else 'Sync'} completed in {duration:.1f}s. "
                      f"Processed: {self.sync_stats['processed_issues']}/{self.sync_stats['total_issues']} issues, "
                      f"Uploaded: {self.sync_stats['uploaded_documents']} documents")
            
            if self.sync_stats['failed_documents'] > 0:
                message += f", Failed: {self.sync_stats['failed_documents']} documents"
            
            if self.sync_stats['errors']:
                message += f", Errors: {len(self.sync_stats['errors'])}"
            
            logger.info(message)
            return self._build_sync_result(success=success, message=message)
            
        except Exception as e:
            logger.error(f"Sync failed with error: {e}")
            self.sync_stats['end_time'] = datetime.now()
            self.sync_stats['errors'].append(str(e))
            return self._build_sync_result(success=False, message=f"Sync failed: {e}")
    
    def _get_issues_in_batches(self, jql_query: str):
        """Generator that yields batches of issues"""
        batch_size = self.config.batch_size
        start_at = 0
        
        while True:
            result = self.jira_client.search_issues(
                jql=jql_query,
                start_at=start_at,
                max_results=batch_size
            )
            
            issues = result.get('issues', [])
            if not issues:
                break
            
            yield issues
            
            # Check if we've retrieved all issues
            total = result.get('total', 0)
            if start_at + len(issues) >= total:
                break
            
            start_at += batch_size
    
    def _build_sync_result(self, success: bool, message: str) -> Dict[str, Any]:
        """Build sync result dictionary"""
        return {
            'success': success,
            'message': message,
            'stats': self.sync_stats.copy(),
            'config': {
                'sync_mode': self.config.sync_mode,
                'batch_size': self.config.batch_size,
                'include_comments': self.config.include_comments,
                'include_history': self.config.include_history,
                'projects': self.config.projects,
                'issue_types': self.config.issue_types,
                'jql_filter': self.config.jql_filter
            }
        }
    
    def get_projects_info(self) -> Dict[str, Any]:
        """Get information about available projects"""
        try:
            projects = self.jira_client.get_projects()
            
            project_info = []
            for project in projects:
                project_info.append({
                    'key': project.get('key'),
                    'name': project.get('name'),
                    'id': project.get('id'),
                    'projectTypeKey': project.get('projectTypeKey'),
                    'lead': project.get('lead', {}).get('displayName')
                })
            
            return {
                'success': True,
                'projects': project_info,
                'count': len(project_info),
                'message': f"Retrieved {len(project_info)} projects"
            }
            
        except Exception as e:
            logger.error(f"Failed to get projects: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f"Failed to get projects: {e}"
            }
    
    def get_sync_job_status(self, execution_id: str) -> Dict[str, Any]:
        """Get status of a Q Business sync job"""
        return self.qbusiness_client.get_data_source_sync_job(execution_id)
    
    def start_qbusiness_sync(self) -> Dict[str, Any]:
        """Start a Q Business data source sync job"""
        return self.qbusiness_client.start_data_source_sync()
    
    def cleanup(self):
        """Cleanup resources"""
        if hasattr(self, 'jira_client'):
            self.jira_client.close()
        
        logger.info("Connector cleanup completed") 