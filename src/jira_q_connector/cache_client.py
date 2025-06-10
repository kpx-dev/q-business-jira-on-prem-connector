"""
DynamoDB Cache Client for Jira Custom Connector
Tracks document sync states to avoid re-syncing unchanged documents
"""
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class CacheClient:
    """DynamoDB-based cache for tracking document sync states"""
    
    def __init__(self, aws_config):
        self.config = aws_config
        self.table_name = aws_config.cache_table_name
        self.client = None
        self.table = None
        
        if self.table_name:
            self._create_client()
    
    def _create_client(self) -> None:
        """Create DynamoDB client and table resource"""
        try:
            session = boto3.Session(region_name=self.config.region)
            
            # Assume role if specified
            if self.config.role_arn:
                sts_client = session.client('sts')
                response = sts_client.assume_role(
                    RoleArn=self.config.role_arn,
                    RoleSessionName='jira-q-connector-cache'
                )
                credentials = response['Credentials']
                
                # Create new session with assumed role credentials
                session = boto3.Session(
                    aws_access_key_id=credentials['AccessKeyId'],
                    aws_secret_access_key=credentials['SecretAccessKey'],
                    aws_session_token=credentials['SessionToken'],
                    region_name=self.config.region
                )
            
            self.client = session.client('dynamodb')
            dynamodb = session.resource('dynamodb')
            self.table = dynamodb.Table(self.table_name)
            
            logger.info(f"Connected to DynamoDB cache table: {self.table_name}")
            
        except Exception as e:
            logger.error(f"Failed to create DynamoDB client: {e}")
            raise
    
    def is_enabled(self) -> bool:
        """Check if caching is enabled and properly configured"""
        return self.table_name is not None and self.client is not None
    
    def ensure_table_exists(self) -> Dict[str, Any]:
        """Ensure the cache table exists, create if it doesn't"""
        if not self.is_enabled():
            return {'success': False, 'message': 'Cache not enabled'}
        
        try:
            # Check if table exists
            self.table.load()
            logger.info(f"Cache table {self.table_name} already exists")
            return {'success': True, 'message': f'Table {self.table_name} exists'}
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                # Create table
                logger.info(f"Creating cache table {self.table_name}...")
                
                try:
                    table = self.client.create_table(
                        TableName=self.table_name,
                        KeySchema=[
                            {
                                'AttributeName': 'document_id',
                                'KeyType': 'HASH'
                            }
                        ],
                        AttributeDefinitions=[
                            {
                                'AttributeName': 'document_id',
                                'AttributeType': 'S'
                            }
                        ],
                        BillingMode='PAY_PER_REQUEST',
                        Tags=[
                            {
                                'Key': 'Application',
                                'Value': 'jira-q-connector'
                            },
                            {
                                'Key': 'Purpose',
                                'Value': 'sync-cache'
                            }
                        ]
                    )
                    
                    # Wait for table to be active
                    waiter = self.client.get_waiter('table_exists')
                    waiter.wait(TableName=self.table_name)
                    
                    logger.info(f"Cache table {self.table_name} created successfully")
                    return {'success': True, 'message': f'Created table {self.table_name}'}
                    
                except ClientError as create_error:
                    logger.error(f"Failed to create cache table: {create_error}")
                    return {'success': False, 'message': f'Failed to create table: {create_error}'}
            else:
                logger.error(f"Error checking cache table: {e}")
                return {'success': False, 'message': f'Error checking table: {e}'}
    
    def _calculate_content_hash(self, issue_data: Dict[str, Any]) -> str:
        """Calculate hash of issue content for change detection"""
        # Create a deterministic hash from key issue fields
        hash_data = {
            'key': issue_data.get('key', ''),
            'updated': issue_data.get('fields', {}).get('updated', ''),
            'summary': issue_data.get('fields', {}).get('summary', ''),
            'description': issue_data.get('fields', {}).get('description', ''),
            'status': issue_data.get('fields', {}).get('status', {}).get('name', ''),
            'priority': issue_data.get('fields', {}).get('priority', {}).get('name', ''),
            'assignee': issue_data.get('fields', {}).get('assignee', {}).get('displayName', '') if issue_data.get('fields', {}).get('assignee') else '',
            'resolution': issue_data.get('fields', {}).get('resolution', {}).get('name', '') if issue_data.get('fields', {}).get('resolution') else ''
        }
        
        # Convert to string and hash
        hash_string = str(sorted(hash_data.items()))
        return hashlib.sha256(hash_string.encode()).hexdigest()
    
    def get_cached_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get cached document info by ID"""
        if not self.is_enabled():
            return None
        
        try:
            response = self.table.get_item(Key={'document_id': document_id})
            return response.get('Item')
            
        except ClientError as e:
            logger.warning(f"Error getting cached document {document_id}: {e}")
            return None
    
    def should_sync_document(self, document_id: str, issue_data: Dict[str, Any]) -> bool:
        """Determine if document should be synced based on cache"""
        if not self.is_enabled():
            return True  # Always sync if cache is disabled
        
        cached = self.get_cached_document(document_id)
        if not cached:
            logger.debug(f"Document {document_id} not in cache, needs sync")
            return True
        
        # Calculate current content hash
        current_hash = self._calculate_content_hash(issue_data)
        cached_hash = cached.get('content_hash', '')
        
        if current_hash != cached_hash:
            logger.debug(f"Document {document_id} content changed, needs sync")
            return True
        
        logger.debug(f"Document {document_id} unchanged, skipping sync")
        return False
    
    def update_document_cache(self, document_id: str, issue_data: Dict[str, Any], sync_status: str = 'success') -> bool:
        """Update cache entry for a document"""
        if not self.is_enabled():
            return True
        
        try:
            content_hash = self._calculate_content_hash(issue_data)
            
            self.table.put_item(
                Item={
                    'document_id': document_id,
                    'content_hash': content_hash,
                    'last_sync': datetime.utcnow().isoformat(),
                    'sync_status': sync_status,
                    'jira_key': issue_data.get('key', ''),
                    'jira_updated': issue_data.get('fields', {}).get('updated', ''),
                    'ttl': int((datetime.utcnow().timestamp() + (30 * 24 * 3600)))  # 30 days TTL
                }
            )
            
            logger.debug(f"Updated cache for document {document_id}")
            return True
            
        except ClientError as e:
            logger.warning(f"Error updating cache for document {document_id}: {e}")
            return False
    
    def batch_filter_changed_documents(self, documents_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter a batch of documents to only include those that need syncing"""
        if not self.is_enabled():
            return documents_data
        
        changed_documents = []
        
        for doc_data in documents_data:
            issue = doc_data.get('issue_data', {})
            document_id = f"jira-issue-{issue.get('key', '')}"
            
            if self.should_sync_document(document_id, issue):
                changed_documents.append(doc_data)
        
        logger.info(f"Cache filter: {len(changed_documents)}/{len(documents_data)} documents need syncing")
        return changed_documents
    
    def batch_update_cache(self, document_updates: List[Dict[str, Any]]) -> bool:
        """Batch update cache entries"""
        if not self.is_enabled():
            return True
        
        try:
            with self.table.batch_writer() as batch:
                for update in document_updates:
                    document_id = update['document_id']
                    issue_data = update['issue_data']
                    sync_status = update.get('sync_status', 'success')
                    
                    content_hash = self._calculate_content_hash(issue_data)
                    
                    batch.put_item(
                        Item={
                            'document_id': document_id,
                            'content_hash': content_hash,
                            'last_sync': datetime.utcnow().isoformat(),
                            'sync_status': sync_status,
                            'jira_key': issue_data.get('key', ''),
                            'jira_updated': issue_data.get('fields', {}).get('updated', ''),
                            'ttl': int((datetime.utcnow().timestamp() + (30 * 24 * 3600)))  # 30 days TTL
                        }
                    )
            
            logger.debug(f"Batch updated cache for {len(document_updates)} documents")
            return True
            
        except ClientError as e:
            logger.warning(f"Error batch updating cache: {e}")
            return False
    
    def clear_cache(self) -> Dict[str, Any]:
        """Clear all items from the cache table"""
        if not self.is_enabled():
            return {'success': False, 'message': 'Cache not enabled'}
        
        try:
            # Scan and delete all items
            deleted_count = 0
            
            # Get all items in batches
            response = self.table.scan()
            
            while 'Items' in response:
                with self.table.batch_writer() as batch:
                    for item in response['Items']:
                        batch.delete_item(Key={'document_id': item['document_id']})
                        deleted_count += 1
                
                # Check for more items
                if 'LastEvaluatedKey' in response:
                    response = self.table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
                else:
                    break
            
            logger.info(f"Cleared {deleted_count} items from cache")
            return {'success': True, 'deleted': deleted_count, 'message': f'Cleared {deleted_count} cache entries'}
            
        except ClientError as e:
            logger.error(f"Error clearing cache: {e}")
            return {'success': False, 'message': f'Failed to clear cache: {e}'}
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.is_enabled():
            return {'success': False, 'message': 'Cache not enabled'}
        
        try:
            response = self.table.scan(Select='COUNT')
            item_count = response.get('Count', 0)
            
            return {
                'success': True,
                'table_name': self.table_name,
                'item_count': item_count,
                'message': f'Cache contains {item_count} entries'
            }
            
        except ClientError as e:
            logger.error(f"Error getting cache stats: {e}")
            return {'success': False, 'message': f'Failed to get cache stats: {e}'} 