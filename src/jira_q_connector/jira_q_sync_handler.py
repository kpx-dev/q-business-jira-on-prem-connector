import json
import logging
from jira_q_connector import ConnectorConfig, JiraQBusinessConnector
from pathlib import Path
from datetime import datetime, timedelta, timezone
import os
import boto3

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    try:
        logger.info(f"Received event: {event}")
        
        # Initialize connector and load configuration from SSM
        config = ConnectorConfig.from_ssm()
        connector = JiraQBusinessConnector(config)
        
        # Test connections
        results = connector.test_connections()
        logger.info(f"Connections: {results['overall_success']}")

        # Define action handlers
        actions = {
            'start_sync': handle_start_sync_job,
            'acl_sync_plan': handle_acl_sync_plan,
            'acl_sync': handle_acl_sync,
            'issues_sync_plan': handle_issues_sync_plan,
            'issues_sync': handle_issues_sync,
            'stop_sync': handle_stop_sync_job
        }
        
        # Find first matching action
        for flag, handler in actions.items():
            if event.get(flag, False):
                return handler(event, connector)
        
        # No matching action found
        logger.error("No valid action specified in event")
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'No valid action specified'})
        }
        
    except Exception as e:
        logger.error(f"Lambda handler error: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
        }

def handle_start_sync_job(event, connector):
    try:
        logger.info("Starting sync job")
        sync_job = connector.start_qbusiness_sync()
        execution_id = sync_job['execution_id']
        logger.info(f"Sync job started successfully with execution_id: {execution_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Sync job started successfully',
                'execution_id': execution_id
            })
        }
    except Exception as e:
        logger.error(f"Failed to start sync job: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Failed to start sync job: {str(e)}'})
        }

def handle_acl_sync_plan(event, connector):
    try:
        logger.info("Building ACL sync plan")
        execution_id = event.get('execution_id')
        if not execution_id:
            raise ValueError("execution_id is required")
            
        acl_sync_plan = connector.build_jira_acl_sync_plan(execution_id)
        logger.info(f"ACL sync plan built successfully with {len(acl_sync_plan)} items")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'ACL Sync plan built successfully',
                'plan': acl_sync_plan
            })
        }
    except Exception as e:
        logger.error(f"Failed to build ACL sync plan: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Failed to build ACL sync plan: {str(e)}'})
        }

def handle_acl_sync(event, connector):
    try:
        logger.info("Starting ACL sync")
        execution_id = event.get('execution_id')
        project_keys = event.get('projects')
        
        if not execution_id:
            raise ValueError("execution_id is required")
            
        acl_result = connector.sync_acl_with_execution_id(execution_id=execution_id, project_keys=project_keys)
        logger.info("ACL sync completed successfully")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'ACL Sync completed successfully',
                'result': acl_result
            })
        }
    except Exception as e:
        logger.error(f"Failed to sync ACL: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Failed to sync ACL: {str(e)}'})
        }

def handle_issues_sync_plan(event, connector):
    try:
        logger.info("Building issues sync plan")
        execution_id = event.get('execution_id')
        if not execution_id:
            raise ValueError("execution_id is required")
            
        issues_sync_plan = connector.build_jira_issues_sync_plan(execution_id=execution_id)
        logger.info(f"Issues sync plan built successfully with {len(issues_sync_plan)} items")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Issues Sync plan built successfully',
                'plan': issues_sync_plan
            })
        }
    except Exception as e:
        logger.error(f"Failed to build issues sync plan: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Failed to build issues sync plan: {str(e)}'})
        }

def handle_issues_sync(event, connector):
    try:
        logger.info("Starting issues sync")
        execution_id = event.get('execution_id')
        if not execution_id:
            raise ValueError("execution_id is required")
            
        sync_result = connector.sync_issues_with_execution_id(execution_id=execution_id, sync_plan=event)
        logger.info("Issues sync completed successfully")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Issues Sync completed successfully',
                'result': sync_result
            })
        }
    except Exception as e:
        logger.error(f"Failed to sync issues: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Failed to sync issues: {str(e)}'})
        }

def handle_stop_sync_job(event, connector):
    try:
        logger.info("Stopping sync job")
        execution_id = event.get('execution_id')
        if not execution_id:
            raise ValueError("execution_id is required")
            
        connector.stop_qbusiness_sync(execution_id)
        connector.cleanup()
        
        # Store LAST_SYNC_DATE in parameter store
        yesterday = datetime.now() - timedelta(days=1)
        last_sync_date = yesterday.strftime('%Y-%m-%d')
        
        ssm = boto3.client('ssm')
        param_name = "/jira-q-connector/LAST_SYNC_DATE"
        
        ssm.put_parameter(
            Name=param_name,
            Value=last_sync_date,
            Type='String',
            Overwrite=True
        )
        
        logger.info(f"Sync job stopped successfully, last sync date stored: {last_sync_date}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Sync job stopped successfully',
                'last_sync_date': last_sync_date
            })
        }
    except Exception as e:
        logger.error(f"Failed to stop sync job: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Failed to stop sync job: {str(e)}'})
        }
