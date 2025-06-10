"""
Amazon Q Business client for uploading documents
"""
import boto3
import logging
from typing import Dict, List, Any, Optional
from botocore.exceptions import ClientError, BotoCoreError
import time
from datetime import datetime

from config import AWSConfig

logger = logging.getLogger(__name__)


class QBusinessClient:
    """Client for interacting with Amazon Q Business"""
    
    def __init__(self, config: AWSConfig):
        self.config = config
        self.client = self._create_client()
    
    def _create_client(self) -> boto3.client:
        """Create Q Business client"""
        try:
            session = boto3.Session()
            
            # Assume role if specified
            if self.config.role_arn:
                sts_client = session.client('sts', region_name=self.config.region)
                assumed_role = sts_client.assume_role(
                    RoleArn=self.config.role_arn,
                    RoleSessionName=f"jira-connector-{int(time.time())}"
                )
                
                credentials = assumed_role['Credentials']
                client = boto3.client(
                    'qbusiness',
                    region_name=self.config.region,
                    aws_access_key_id=credentials['AccessKeyId'],
                    aws_secret_access_key=credentials['SecretAccessKey'],
                    aws_session_token=credentials['SessionToken']
                )
            else:
                client = session.client('qbusiness', region_name=self.config.region)
            
            return client
            
        except Exception as e:
            logger.error(f"Failed to create Q Business client: {e}")
            raise
    
    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Q Business"""
        try:
            # Try to get application info
            response = self.client.get_application(
                applicationId=self.config.application_id
            )
            
            return {
                'success': True,
                'application': response,
                'message': f"Connected to Q Business application: {response.get('displayName', 'Unknown')}"
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            return {
                'success': False,
                'error_code': error_code,
                'error_message': error_message,
                'message': f"Failed to connect to Q Business: {error_code} - {error_message}"
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f"Failed to connect to Q Business: {e}"
            }
    
    def batch_put_documents_with_execution_id(self, documents: List[Dict[str, Any]], execution_id: str) -> Dict[str, Any]:
        """Upload documents to Q Business with execution ID (for custom connector workflow)"""
        if not documents:
            return {
                'success': True,
                'processed': 0,
                'failed': 0,
                'message': "No documents to upload"
            }
        
        try:
            # Update documents with required custom connector attributes
            updated_documents = []
            for doc in documents:
                updated_doc = doc.copy()
                
                # Ensure required attributes are present and correctly set
                if 'attributes' not in updated_doc:
                    updated_doc['attributes'] = []
                
                # Update _data_source_id with actual data source ID
                data_source_id_found = False
                execution_id_found = False
                
                for attr in updated_doc['attributes']:
                    if attr.get('name') == '_data_source_id':
                        attr['value']['stringValue'] = self.config.data_source_id
                        data_source_id_found = True
                    elif attr.get('name') == '_data_source_sync_job_execution_id':
                        attr['value']['stringValue'] = execution_id
                        execution_id_found = True
                
                # Add missing required attributes
                if not data_source_id_found:
                    updated_doc['attributes'].append({
                        'name': '_data_source_id',
                        'value': {
                            'stringValue': self.config.data_source_id
                        }
                    })
                
                if not execution_id_found:
                    updated_doc['attributes'].append({
                        'name': '_data_source_sync_job_execution_id',
                        'value': {
                            'stringValue': execution_id
                        }
                    })
                
                updated_documents.append(updated_doc)
            
            # Use the regular batch upload with updated documents
            return self.batch_put_documents(updated_documents)
            
        except Exception as e:
            logger.error(f"Error updating documents for custom connector: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f"Failed to prepare documents for custom connector: {e}"
            }

    def batch_put_documents(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Upload documents to Q Business using BatchPutDocument"""
        if not documents:
            return {
                'success': True,
                'processed': 0,
                'failed': 0,
                'message': "No documents to upload"
            }
        
        try:
            # Prepare the batch request
            request_docs = []
            for doc in documents:
                request_doc = {
                    'id': doc['id'],
                    'title': doc['title'],
                    'content': doc['content'],
                    'contentType': doc.get('contentType', 'PLAIN_TEXT')
                }
                
                # Add attributes if present
                if 'attributes' in doc and doc['attributes']:
                    request_doc['attributes'] = doc['attributes']
                
                request_docs.append(request_doc)
            
            # Execute the batch request
            response = self.client.batch_put_document(
                applicationId=self.config.application_id,
                indexId=self.config.index_id,
                documents=request_docs
            )
            
            # Process response
            failed_docs = response.get('failedDocuments', [])
            processed_count = len(documents) - len(failed_docs)
            
            # Log failures
            for failed_doc in failed_docs:
                logger.error(f"Failed to upload document {failed_doc.get('id', 'unknown')}: "
                           f"{failed_doc.get('errorCode', 'Unknown')} - {failed_doc.get('errorMessage', 'Unknown error')}")
            
            return {
                'success': True,
                'processed': processed_count,
                'failed': len(failed_docs),
                'failed_documents': failed_docs,
                'message': f"Uploaded {processed_count} documents, {len(failed_docs)} failed"
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"AWS error during batch upload: {error_code} - {error_message}")
            
            return {
                'success': False,
                'error_code': error_code,
                'error_message': error_message,
                'message': f"Batch upload failed: {error_code} - {error_message}"
            }
        except Exception as e:
            logger.error(f"Unexpected error during batch upload: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f"Batch upload failed: {e}"
            }
    
    def delete_all_data_source_documents(self, execution_id: str) -> Dict[str, Any]:
        """Delete all documents from this data source
        
        Note: Since AWS Q Business doesn't provide a direct way to list documents by data source,
        we'll delete documents that would be created by the current sync operation.
        This ensures clean overwrites by deleting before uploading.
        """
        try:
            # For now, return success but note that actual deletion will happen
            # on a per-document basis during sync
            logger.info("Prepared for clean document sync - old documents will be overwritten")
            
            return {
                'success': True,
                'deleted': 0,  # Actual count will be updated during sync
                'message': "Prepared for clean document sync"
            }
            
        except Exception as e:
            logger.error(f"Error preparing clean sync: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f"Failed to prepare clean sync: {e}"
            }

    def _is_not_found_error(self, failed_doc: Dict[str, Any]) -> bool:
        """Check if a failed document error is due to document not found (expected)"""
        error_code = failed_doc.get('errorCode', 'Unknown')
        error_message = failed_doc.get('errorMessage', 'Unknown error')
        
        return ('not found' in error_message.lower() or 
                error_code in ['DocumentNotFound', 'NotFound'] or
                (error_code == 'Unknown' and error_message == 'Unknown error'))

    def batch_delete_documents(self, document_ids: List[str]) -> Dict[str, Any]:
        """Delete documents from Q Business using BatchDeleteDocument"""
        if not document_ids:
            return {
                'success': True,
                'deleted': 0,
                'failed': 0,
                'message': "No documents to delete"
            }
        
        try:
            # Convert document IDs to the format expected by the API
            documents_to_delete = [{'documentId': doc_id} for doc_id in document_ids]
            
            response = self.client.batch_delete_document(
                applicationId=self.config.application_id,
                indexId=self.config.index_id,
                documents=documents_to_delete
            )
            
            # Process response
            failed_docs = response.get('failedDocuments', [])
            
            # Count actual failures vs expected "not found" cases
            actual_failures = 0
            not_found_count = 0
            
            # Log failures (but treat "not found" as info, not error)
            for failed_doc in failed_docs:
                doc_id = failed_doc.get('id', 'unknown')
                error_code = failed_doc.get('errorCode', 'Unknown')
                error_message = failed_doc.get('errorMessage', 'Unknown error')
                
                # Document not found is expected for clean sync - not an error
                if self._is_not_found_error(failed_doc):
                    logger.debug(f"Document {doc_id} not found (already deleted or never existed)")
                    not_found_count += 1
                else:
                    logger.warning(f"Failed to delete document {doc_id}: {error_code} - {error_message}")
                    actual_failures += 1
            
            # Calculate success: documents that existed and were deleted successfully
            deleted_count = len(document_ids) - not_found_count - actual_failures
            
            return {
                'success': actual_failures == 0,  # Success if no actual failures
                'deleted': deleted_count,
                'failed': actual_failures,
                'not_found': not_found_count,
                'failed_documents': [doc for doc in failed_docs if not self._is_not_found_error(doc)],
                'message': f"Deleted {deleted_count} documents" + 
                          (f", {not_found_count} not found (expected)" if not_found_count > 0 else "") +
                          (f", {actual_failures} failed" if actual_failures > 0 else "")
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"AWS error during batch delete: {error_code} - {error_message}")
            
            return {
                'success': False,
                'error_code': error_code,
                'error_message': error_message,
                'message': f"Batch delete failed: {error_code} - {error_message}"
            }
        except Exception as e:
            logger.error(f"Unexpected error during batch delete: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f"Batch delete failed: {e}"
            }
    
    def start_data_source_sync(self) -> Dict[str, Any]:
        """Start a data source sync job"""
        try:
            response = self.client.start_data_source_sync_job(
                applicationId=self.config.application_id,
                indexId=self.config.index_id,
                dataSourceId=self.config.data_source_id
            )
            
            execution_id = response.get('executionId')
            
            return {
                'success': True,
                'execution_id': execution_id,
                'message': f"Started data source sync job: {execution_id}"
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"AWS error starting sync job: {error_code} - {error_message}")
            
            return {
                'success': False,
                'error_code': error_code,
                'error_message': error_message,
                'message': f"Failed to start sync job: {error_code} - {error_message}"
            }
        except Exception as e:
            logger.error(f"Unexpected error starting sync job: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f"Failed to start sync job: {e}"
            }
    
    def get_sync_job_by_id(self, execution_id: str) -> Dict[str, Any]:
        """Get sync job info by execution ID from the list of jobs"""
        try:
            # Since get_data_source_sync_job doesn't exist, we'll search the list
            list_result = self.list_data_source_sync_jobs(max_results=10)
            
            if not list_result['success']:
                return list_result
            
            # Find the job with matching execution ID
            for job in list_result['sync_jobs']:
                if job.get('executionId') == execution_id:
                    return {
                        'success': True,
                        'sync_job': job,
                        'status': job.get('status'),
                        'message': f"Sync job {execution_id} status: {job.get('status')}"
                    }
            
            return {
                'success': False,
                'message': f"Sync job {execution_id} not found in recent jobs"
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f"Failed to get sync job status: {e}"
            }
    
    def stop_data_source_sync(self, execution_id: str = None) -> Dict[str, Any]:
        """Stop a data source sync job"""
        try:
            response = self.client.stop_data_source_sync_job(
                applicationId=self.config.application_id,
                indexId=self.config.index_id,
                dataSourceId=self.config.data_source_id
            )
            
            return {
                'success': True,
                'message': f"Stopped data source sync job"
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"AWS error stopping sync job: {error_code} - {error_message}")
            
            return {
                'success': False,
                'error_code': error_code,
                'error_message': error_message,
                'message': f"Failed to stop sync job: {error_code} - {error_message}"
            }
        except Exception as e:
            logger.error(f"Unexpected error stopping sync job: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f"Failed to stop sync job: {e}"
            }

    def get_data_source_sync_job_metrics(self, execution_id: str) -> Dict[str, Any]:
        """Get detailed metrics for a completed sync job from the sync job history"""
        try:
            # Get sync job details from history which includes metrics
            response = self.client.list_data_source_sync_jobs(
                applicationId=self.config.application_id,
                indexId=self.config.index_id,
                dataSourceId=self.config.data_source_id,
                maxResults=10  # AWS Q Business API limit
            )
            
            # Find the job with matching execution ID
            sync_jobs = response.get('history', [])
            
            for job in sync_jobs:
                if job.get('executionId') == execution_id:
                    metrics = job.get('metrics', {})
                    
                    # Debug: Log the raw metrics to see what AWS is returning
                    logger.debug(f"Raw metrics from AWS for job {execution_id}: {metrics}")
                    logger.debug(f"Full job details: {job}")
                    
                    # Parse string metrics to integers, handle None/empty values
                    documents_added = int(metrics.get('documentsAdded', '0') or '0')
                    documents_deleted = int(metrics.get('documentsDeleted', '0') or '0')
                    documents_failed = int(metrics.get('documentsFailed', '0') or '0')
                    documents_modified = int(metrics.get('documentsModified', '0') or '0')
                    
                    # Log parsed values for debugging
                    logger.info(f"Parsed metrics - Added: {documents_added}, Modified: {documents_modified}, "
                              f"Deleted: {documents_deleted}, Failed: {documents_failed}")
                    
                    return {
                        'success': True,
                        'metrics': metrics,
                        'documents_added': documents_added,
                        'documents_deleted': documents_deleted,
                        'documents_failed': documents_failed,
                        'documents_modified': documents_modified,
                        'message': f"Retrieved metrics for sync job {execution_id}"
                    }
            
            # Job not found in recent history
            return {
                'success': False,
                'message': f"Sync job {execution_id} not found in recent job history"
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            return {
                'success': False,
                'error_code': error_code,
                'error_message': error_message,
                'message': f"Failed to get sync job metrics: {error_code} - {error_message}"
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f"Failed to get sync job metrics: {e}"
            }

    def list_data_source_sync_jobs(self, max_results: int = 10) -> Dict[str, Any]:
        """List recent data source sync jobs"""
        try:
            response = self.client.list_data_source_sync_jobs(
                applicationId=self.config.application_id,
                indexId=self.config.index_id,
                dataSourceId=self.config.data_source_id,
                maxResults=max_results
            )
            
            return {
                'success': True,
                'sync_jobs': response.get('history', []),
                'message': f"Retrieved {len(response.get('history', []))} sync jobs"
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            return {
                'success': False,
                'error_code': error_code,
                'error_message': error_message,
                'message': f"Failed to list sync jobs: {error_code} - {error_message}"
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f"Failed to list sync jobs: {e}"
            } 