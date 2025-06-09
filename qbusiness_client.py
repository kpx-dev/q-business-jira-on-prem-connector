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
            response = self.client.batch_delete_document(
                applicationId=self.config.application_id,
                indexId=self.config.index_id,
                documentIds=document_ids
            )
            
            # Process response
            failed_docs = response.get('failedDocuments', [])
            deleted_count = len(document_ids) - len(failed_docs)
            
            # Log failures
            for failed_doc in failed_docs:
                logger.error(f"Failed to delete document {failed_doc.get('id', 'unknown')}: "
                           f"{failed_doc.get('errorCode', 'Unknown')} - {failed_doc.get('errorMessage', 'Unknown error')}")
            
            return {
                'success': True,
                'deleted': deleted_count,
                'failed': len(failed_docs),
                'failed_documents': failed_docs,
                'message': f"Deleted {deleted_count} documents, {len(failed_docs)} failed"
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
    
    def get_data_source_sync_job(self, execution_id: str) -> Dict[str, Any]:
        """Get status of a data source sync job"""
        try:
            response = self.client.get_data_source_sync_job(
                applicationId=self.config.application_id,
                indexId=self.config.index_id,
                dataSourceId=self.config.data_source_id,
                executionId=execution_id
            )
            
            return {
                'success': True,
                'sync_job': response,
                'status': response.get('status'),
                'message': f"Sync job {execution_id} status: {response.get('status')}"
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            return {
                'success': False,
                'error_code': error_code,
                'error_message': error_message,
                'message': f"Failed to get sync job status: {error_code} - {error_message}"
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f"Failed to get sync job status: {e}"
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