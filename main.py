#!/usr/bin/env python3
"""
Main CLI application for Jira Q Business Custom Connector
"""
import argparse
import logging
import sys


from config import ConnectorConfig
from jira_connector import JiraQBusinessConnector


def setup_logging(level: str = "INFO"):
    """Setup logging configuration"""
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Setup console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    
    # Reduce noise from external libraries
    logging.getLogger('boto3').setLevel(logging.WARNING)
    logging.getLogger('botocore').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

def cmd_doctor(args, connector: JiraQBusinessConnector):
    """Test connections command"""
    print("🩺 Running connector diagnostics...")
    
    results = connector.test_connections()
    
    if results['overall_success']:
        print("✅ All connections successful!")
        return 0
    else:
        print("❌ Connection test failed!")
        return 1

def cmd_status(args, connector: JiraQBusinessConnector):
    """Check sync job status command"""
    if args.execution_id:
        # Check specific sync job
        execution_id = args.execution_id
        print(f"Checking status of sync job: {execution_id}")
        
        result = connector.get_sync_job_status(execution_id)
        
        if result['success']:
            job = result['sync_job']
            status = job.get('status', 'Unknown')
            print(f"✅ Sync job status: {status}")
            
            # Print additional details if available
            if 'startTime' in job:
                print(f"   Start Time: {job['startTime']}")
            if 'endTime' in job:
                print(f"   End Time: {job['endTime']}")
            
            # Try to get detailed metrics if job is completed
            if status in ['SUCCEEDED', 'FAILED', 'ABORTED']:
                print(f"\n📊 Attempting to retrieve detailed metrics...")
                metrics_result = connector.qbusiness_client.get_data_source_sync_job_metrics(execution_id)
                
                if metrics_result['success']:
                    print(f"📈 Detailed Metrics:")
                    print(f"   📄 Documents Added: {metrics_result['documents_added']}")
                    print(f"   📝 Documents Modified: {metrics_result['documents_modified']}")
                    print(f"   🗑️  Documents Deleted: {metrics_result['documents_deleted']}")
                    print(f"   ❌ Documents Failed: {metrics_result['documents_failed']}")
                else:
                    print(f"⚠️  Could not retrieve detailed metrics: {metrics_result['message']}")
                    # Fall back to basic job metrics
                    print(f"📈 Basic Metrics:")
                    if 'documentsAdded' in job:
                        print(f"   Documents Added: {job['documentsAdded']}")
                    if 'documentsModified' in job:
                        print(f"   Documents Modified: {job['documentsModified']}")
                    if 'documentsDeleted' in job:
                        print(f"   Documents Deleted: {job['documentsDeleted']}")
                    if 'documentsFailed' in job:
                        print(f"   Documents Failed: {job['documentsFailed']}")
            else:
                # Job still running, show basic info
                if 'documentsAdded' in job:
                    print(f"   Documents Added: {job['documentsAdded']}")
                if 'documentsModified' in job:
                    print(f"   Documents Modified: {job['documentsModified']}")
                if 'documentsDeleted' in job:
                    print(f"   Documents Deleted: {job['documentsDeleted']}")
                if 'documentsFailed' in job:
                    print(f"   Documents Failed: {job['documentsFailed']}")
            
            return 0
        else:
            print(f"❌ Failed to get sync job status: {result['message']}")
            return 1
    else:
        # List recent sync jobs
        print("📋 Checking recent Q Business sync jobs...")
        
        result = connector.qbusiness_client.list_data_source_sync_jobs(max_results=10)
        
        if result['success']:
            jobs = result['sync_jobs']
            if jobs:
                print(f"Found {len(jobs)} recent sync jobs:")
                print("-" * 80)
                
                for i, job in enumerate(jobs, 1):
                    status = job.get('status', 'Unknown')
                    execution_id = job.get('executionId', 'Unknown')
                    start_time = job.get('startTime', 'Unknown')
                    
                    status_emoji = {
                        'SYNCING': '🔄',
                        'SUCCEEDED': '✅',
                        'FAILED': '❌',
                        'STOPPING': '⏹️',
                        'STOPPED': '⏹️'
                    }.get(status, '❓')
                    
                    print(f"{i}. {status_emoji} Status: {status}")
                    print(f"   Execution ID: {execution_id}")
                    print(f"   Start Time: {start_time}")
                    
                    if 'endTime' in job:
                        print(f"   End Time: {job['endTime']}")
                    if 'documentsAdded' in job:
                        print(f"   Documents Added: {job['documentsAdded']}")
                    if 'documentsModified' in job:
                        print(f"   Documents Modified: {job['documentsModified']}")
                    if 'documentsDeleted' in job:
                        print(f"   Documents Deleted: {job['documentsDeleted']}")
                    if 'documentsFailed' in job:
                        print(f"   Documents Failed: {job['documentsFailed']}")
                    
                    print()
                
                print("💡 To check a specific job, use:")
                print(f"   python main.py status --execution-id <execution_id>")
            else:
                print("No recent sync jobs found.")
            
            return 0
        else:
            print(f"❌ Failed to list sync jobs: {result['message']}")
            return 1


def cmd_full_sync(args, connector: JiraQBusinessConnector):
    """Complete sync workflow following AWS Q Business custom connector best practices"""
    dry_run = getattr(args, 'dry_run', False)
    clean_sync = getattr(args, 'clean', False)
    
    if dry_run:
        print("🔍 Starting dry run of complete sync workflow (no documents will be uploaded)...")
    else:
        print("🚀 Starting complete sync workflow: Jira → Q Business")
        
    if clean_sync:
        print("🧹 Clean mode: Will delete all existing documents before syncing")
    
    try:
        # Step 1: Start the sync job
        print("\n📋 Step 1 of 4: Starting Q Business data source sync job...")
        
        if dry_run:
            print("✅ Dry run: Would start sync job here")
            execution_id = "dry-run-execution-id"
        else:
            start_result = connector.start_qbusiness_sync()
            
            if not start_result['success']:
                print(f"❌ Failed to start sync job: {start_result['message']}")
                return 1
                
            execution_id = start_result['execution_id']
            print(f"✅ Sync job started successfully")
            print(f"   Execution ID: {execution_id}")
        
        # Step 1.5: Clean existing documents if requested
        if clean_sync:
            print(f"\n🧹 Step 1.5 of 4: Cleaning existing documents...")
            
            if dry_run:
                print("✅ Dry run: Would delete all existing documents from data source")
            else:
                clean_result = connector.clean_all_documents(execution_id)
                if clean_result['success']:
                    print(f"✅ Cleaned {clean_result.get('deleted', 0)} existing documents")
                else:
                    print(f"⚠️  Warning: Failed to clean documents: {clean_result['message']}")
                    print("   Continuing with sync...")
        
        # Step 2: Sync Jira documents with the execution ID
        print(f"\n📄 Step 2 of 4: Syncing Jira issues to Q Business...")
        
        if dry_run:
            # For dry run, just show what would be done
            sync_result = connector.sync_issues_with_execution_id(execution_id, dry_run=True, clean_first=clean_sync)
            print(f"✅ Dry run completed. Would sync {sync_result.get('stats', {}).get('uploaded_documents', 0)} documents")
        else:
            # Real sync with execution ID
            sync_result = connector.sync_issues_with_execution_id(execution_id, dry_run=False, clean_first=clean_sync)
            
            if not sync_result['success']:
                print(f"❌ Document sync failed: {sync_result['message']}")
                # Still try to stop the sync job
                print(f"\n🛑 Step 3 of 4: Stopping sync job due to errors...")
                stop_result = connector.stop_qbusiness_sync(execution_id)
                return 1
            
            print(f"✅ Document sync completed successfully")
            print(f"   Processed: {sync_result['stats']['processed_issues']} issues")
            print(f"   Uploaded: {sync_result['stats']['uploaded_documents']} documents")
            
            if sync_result['stats'].get('deleted_documents', 0) > 0:
                print(f"   Deleted: {sync_result['stats']['deleted_documents']} old documents")
        
        # Step 3: Stop the sync job
        print(f"\n🏁 Step 3 of 4: Stopping Q Business sync job...")
        
        if not dry_run:
            stop_result = connector.stop_qbusiness_sync(execution_id)
            
            if stop_result['success']:
                print(f"✅ Sync job stopped successfully")
            else:
                print(f"⚠️  Warning: Failed to stop sync job: {stop_result['message']}")
                print("   The sync job may continue running in the background")
        else:
            print("✅ Dry run: Would stop sync job here")
        
        # Step 4: Completion
        print(f"\n🎯 Step 4 of 4: Sync completed successfully!")
        
        if not dry_run:
            print(f"   Execution ID: {execution_id}")
            print(f"   💡 Check sync status with: python main.py status --execution-id {execution_id}")
        else:
            print("   Dry run completed - no actual sync job was executed")
        
        print(f"\n🎉 Complete sync workflow finished successfully!")
        return 0
        
    except KeyboardInterrupt:
        print(f"\n🛑 Sync interrupted by user")
        if not dry_run and 'execution_id' in locals():
            print(f"🔧 Attempting to stop sync job {execution_id}...")
            try:
                connector.stop_qbusiness_sync(execution_id)
                print("✅ Sync job stopped")
            except:
                print("⚠️  Could not stop sync job - it may continue running")
        return 130
    except Exception as e:
        print(f"❌ Unexpected error during sync: {e}")
        if not dry_run and 'execution_id' in locals():
            print(f"🔧 Attempting to stop sync job {execution_id}...")
            try:
                connector.stop_qbusiness_sync(execution_id)
            except:
                pass
        return 1


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Jira Custom Connector for Amazon Q Business",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test connections
  python main.py doctor
  
  # Complete sync workflow (recommended)
  python main.py sync
  
  # Clean sync (delete duplicates, then upload)
  python main.py sync --clean
  
  # Dry run sync (preview only)
  python main.py sync --dry-run
  
  # Check recent sync jobs
  python main.py status
  
  # Check specific sync job status
  python main.py status --execution-id <id>

Environment Variables:
  JIRA_SERVER_URL     - Jira server URL (required)
  JIRA_USERNAME       - Jira username (required)
  JIRA_PASSWORD       - Jira password/token (required)
  Q_APPLICATION_ID    - Q Business application ID (required)
  Q_DATA_SOURCE_ID    - Q Business data source ID (required)
  Q_INDEX_ID          - Q Business index ID (required)
  AWS_REGION          - AWS region (default: us-east-1)
  SYNC_MODE           - Sync mode: full or incremental (default: full)
  BATCH_SIZE          - Batch size for processing (default: 10)
  INCLUDE_COMMENTS    - Include issue comments (default: true)
  INCLUDE_HISTORY     - Include change history (default: false)
  PROJECTS            - Comma-separated project keys to sync
  ISSUE_TYPES         - Comma-separated issue types to sync
  JQL_FILTER          - Custom JQL filter
        """
    )
    
    parser.add_argument(
        "--log-level", "-l",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Log level (default: INFO)"
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Doctor command
    doctor_parser = subparsers.add_parser('doctor', help='Test connections to Jira and Q Business')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Check Q Business sync job status')
    status_parser.add_argument(
        '--execution-id',
        help='Sync job execution ID (optional - shows recent jobs if omitted)'
    )
    
    # Full sync command (new)
    full_sync_parser = subparsers.add_parser('sync', help='Complete sync: Jira to Q Business with proper sync job lifecycle')
    full_sync_parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Preview sync without uploading documents'
    )
    full_sync_parser.add_argument(
        '--clean',
        action='store_true',
        help='Delete all existing documents before syncing (full refresh)'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Setup logging
    setup_logging(args.log_level)
    
    try:
        # Load configuration from environment
        config = ConnectorConfig.from_env()
        
        # Create connector
        connector = JiraQBusinessConnector(config)
        
        # Execute command
        command_functions = {
            'doctor': cmd_doctor,
            'status': cmd_status,
            'sync': cmd_full_sync
        }
        
        exit_code = command_functions[args.command](args, connector)
        
        # Cleanup
        connector.cleanup()
        
        return exit_code
        
    except KeyboardInterrupt:
        print("\n🛑 Operation cancelled by user")
        return 130
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        if args.log_level == "DEBUG":
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main()) 