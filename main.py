#!/usr/bin/env python3
"""
Main CLI application for Jira Q Business Custom Connector
"""
import argparse
import logging
import sys
import json
from pathlib import Path

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


def load_config_from_file(config_file: str) -> ConnectorConfig:
    """Load configuration from JSON file"""
    config_path = Path(config_file)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_file}")
    
    with open(config_path, 'r') as f:
        config_data = json.load(f)
    
    return ConnectorConfig(**config_data)


def cmd_test(args, connector: JiraQBusinessConnector):
    """Test connections command"""
    print("Testing connections...")
    
    results = connector.test_connections()
    
    if results['overall_success']:
        print("✅ All connections successful!")
        return 0
    else:
        print("❌ Connection test failed!")
        return 1


def cmd_projects(args, connector: JiraQBusinessConnector):
    """List projects command"""
    print("Retrieving Jira projects...")
    
    result = connector.get_projects_info()
    
    if result['success']:
        print(f"\n📋 Found {result['count']} projects:")
        print("-" * 80)
        
        for project in result['projects']:
            lead = project.get('lead', 'N/A')
            print(f"  {project['key']:10} | {project['name']:30} | Lead: {lead}")
        
        return 0
    else:
        print(f"❌ Failed to retrieve projects: {result['message']}")
        return 1


def cmd_sync(args, connector: JiraQBusinessConnector):
    """Sync issues command"""
    dry_run = args.dry_run
    
    if dry_run:
        print("🔍 Starting dry run sync (no documents will be uploaded)...")
    else:
        print("🚀 Starting sync of Jira issues to Q Business...")
    
    result = connector.sync_issues(dry_run=dry_run)
    
    if result['success']:
        print(f"✅ {result['message']}")
        
        # Print detailed stats
        stats = result['stats']
        print("\n📊 Sync Statistics:")
        print(f"  Total Issues:      {stats['total_issues']}")
        print(f"  Processed Issues:  {stats['processed_issues']}")
        print(f"  Uploaded Docs:     {stats['uploaded_documents']}")
        
        if stats['failed_documents'] > 0:
            print(f"  Failed Docs:       {stats['failed_documents']}")
        
        if stats['errors']:
            print(f"  Errors:           {len(stats['errors'])}")
            print("\n❌ Errors:")
            for error in stats['errors']:
                print(f"    - {error}")
        
        # Print configuration used
        config_info = result['config']
        print(f"\n⚙️  Configuration:")
        print(f"  Sync Mode:         {config_info['sync_mode']}")
        print(f"  Batch Size:        {config_info['batch_size']}")
        print(f"  Include Comments:  {config_info['include_comments']}")
        print(f"  Include History:   {config_info['include_history']}")
        
        if config_info['projects']:
            print(f"  Projects:          {', '.join(config_info['projects'])}")
        
        if config_info['issue_types']:
            print(f"  Issue Types:       {', '.join(config_info['issue_types'])}")
        
        if config_info['jql_filter']:
            print(f"  JQL Filter:        {config_info['jql_filter']}")
        
        return 0
    else:
        print(f"❌ {result['message']}")
        
        if result['stats']['errors']:
            print("\n❌ Errors:")
            for error in result['stats']['errors']:
                print(f"    - {error}")
        
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


def cmd_start_sync(args, connector: JiraQBusinessConnector):
    """Start Q Business sync job command"""
    print("Starting Q Business data source sync job...")
    
    result = connector.start_qbusiness_sync()
    
    if result['success']:
        print(f"✅ {result['message']}")
        print(f"   Execution ID: {result['execution_id']}")
        print("\n💡 Use the 'status' command to check progress:")
        print(f"   python main.py status --execution-id {result['execution_id']}")
        return 0
    else:
        print(f"❌ {result['message']}")
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
        print("\n📋 Step 1: Starting Q Business data source sync job...")
        
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
            print(f"\n🧹 Step 1.5: Cleaning existing documents...")
            
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
        print(f"\n📄 Step 2: Syncing Jira issues to Q Business...")
        
        if dry_run:
            # For dry run, just show what would be done
            if clean_sync:
                # Simulate the new method for dry run with clean
                sync_result = connector.sync_issues_with_execution_id(execution_id, dry_run=True, clean_first=True)
            else:
                sync_result = connector.sync_issues(dry_run=True)
            print(f"✅ Dry run completed. Would sync {sync_result.get('stats', {}).get('uploaded_documents', 0)} documents")
        else:
            # Real sync with execution ID
            sync_result = connector.sync_issues_with_execution_id(execution_id, dry_run=False, clean_first=clean_sync)
            
            if not sync_result['success']:
                print(f"❌ Document sync failed: {sync_result['message']}")
                # Still try to stop the sync job
                print(f"\n🛑 Step 3: Stopping sync job due to errors...")
                stop_result = connector.stop_qbusiness_sync(execution_id)
                return 1
            
            print(f"✅ Document sync completed successfully")
            print(f"   Processed: {sync_result['stats']['processed_issues']} issues")
            print(f"   Uploaded: {sync_result['stats']['uploaded_documents']} documents")
            
            if sync_result['stats'].get('deleted_documents', 0) > 0:
                print(f"   Deleted: {sync_result['stats']['deleted_documents']} old documents")
        
        # Step 3: Stop the sync job
        print(f"\n🏁 Step 3: Stopping Q Business sync job...")
        
        if not dry_run:
            stop_result = connector.stop_qbusiness_sync(execution_id)
            
            if stop_result['success']:
                print(f"✅ Sync job stopped successfully")
            else:
                print(f"⚠️  Warning: Failed to stop sync job: {stop_result['message']}")
                print("   The sync job may continue running in the background")
        else:
            print("✅ Dry run: Would stop sync job here")
        
        # Step 4: Wait for completion and get detailed metrics
        print(f"\n📊 Step 4: Waiting for sync completion and retrieving metrics...")
        
        if not dry_run:
            import time
            
            # Wait for the sync job to complete and get detailed metrics
            max_wait_time = 300  # 5 minutes max wait
            wait_interval = 10   # Check every 10 seconds
            elapsed_time = 0
            
            print(f"⏳ Waiting for sync job to complete (max {max_wait_time//60} minutes)...")
            
            final_status = None
            metrics_result = None
            
            while elapsed_time < max_wait_time:
                # Check job status
                status_result = connector.get_sync_job_status(execution_id)
                
                if status_result['success']:
                    job = status_result['sync_job']
                    status = job.get('status', 'Unknown')
                    
                    if status in ['SUCCEEDED', 'FAILED', 'ABORTED']:
                        final_status = status
                        print(f"📈 Sync Job Completed: {status}")
                        
                        # Wait a bit more for metrics to be populated by AWS
                        print(f"⏳ Waiting for metrics to be available...")
                        time.sleep(5)
                        
                        # Try to get detailed metrics
                        metrics_result = connector.qbusiness_client.get_data_source_sync_job_metrics(execution_id)
                        
                        if metrics_result['success']:
                            print(f"📊 AWS Q Business Metrics (First-Time Additions Only):")
                            print(f"   📄 Documents Added: {metrics_result['documents_added']} (new documents only)")
                            print(f"   📝 Documents Modified: {metrics_result['documents_modified']}")
                            print(f"   🗑️  Documents Deleted: {metrics_result['documents_deleted']}")
                            print(f"   ❌ Documents Failed: {metrics_result['documents_failed']}")
                            
                            # Show local sync activity metrics too
                            print(f"\n📈 Local Sync Activity (This Session):")
                            print(f"   📄 Documents Processed: {sync_result['stats']['processed_issues']} issues")
                            print(f"   📤 Documents Uploaded: {sync_result['stats']['uploaded_documents']}")
                            if sync_result['stats'].get('deleted_documents', 0) > 0:
                                print(f"   🗑️  Documents Deleted: {sync_result['stats']['deleted_documents']}")
                            
                            # Explain the difference if there's a mismatch
                            aws_added = metrics_result['documents_added']
                            local_uploaded = sync_result['stats']['uploaded_documents']
                            if aws_added == 0 and local_uploaded > 0:
                                print(f"\n💡 Note: AWS shows 0 'Documents Added' because it only counts")
                                print(f"   documents being indexed for the first time. Re-uploading")
                                print(f"   existing documents doesn't count as 'added' in AWS metrics.")
                                
                        else:
                            print(f"⚠️  Could not retrieve detailed AWS metrics: {metrics_result['message']}")
                            # Show local metrics only
                            print(f"\n📈 Local Sync Activity (This Session):")
                            print(f"   📄 Documents Processed: {sync_result['stats']['processed_issues']} issues")
                            print(f"   📤 Documents Uploaded: {sync_result['stats']['uploaded_documents']}")
                            if sync_result['stats'].get('deleted_documents', 0) > 0:
                                print(f"   🗑️  Documents Deleted: {sync_result['stats']['deleted_documents']}")
                        
                        break
                    else:
                        print(f"   Status: {status} (still running...)")
                else:
                    print(f"   Could not check status: {status_result['message']}")
                
                # Wait before next check
                time.sleep(wait_interval)
                elapsed_time += wait_interval
            
            if final_status is None:
                print(f"⚠️  Sync job did not complete within {max_wait_time//60} minutes")
                print(f"   💡 Check status later with: python main.py status --execution-id {execution_id}")
            
            print(f"   Execution ID: {execution_id}")
            
        else:
            print("✅ Dry run completed - no actual sync job was executed")
        
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
  python main.py test
  
  # List Jira projects  
  python main.py projects
  
  # Dry run sync (preview only)
  python main.py sync-jira-to-q --dry-run
  
  # Full sync (upload only)
  python main.py sync-jira-to-q
  
  # Complete sync workflow (recommended)
  python main.py sync
  
  # Clean sync (delete duplicates, then upload)
  python main.py sync --clean
  
  # Start Q Business sync job
  python main.py sync-q-index
  
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
  BATCH_SIZE          - Batch size for processing (default: 100)
  INCLUDE_COMMENTS    - Include issue comments (default: true)
  INCLUDE_HISTORY     - Include change history (default: false)
  PROJECTS            - Comma-separated project keys to sync
  ISSUE_TYPES         - Comma-separated issue types to sync
  JQL_FILTER          - Custom JQL filter
        """
    )
    
    parser.add_argument(
        "--config", "-c",
        help="Configuration file (JSON format)"
    )
    
    parser.add_argument(
        "--log-level", "-l",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Log level (default: INFO)"
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Test connections to Jira and Q Business')
    
    # Projects command
    projects_parser = subparsers.add_parser('projects', help='List available Jira projects')
    
    # Sync Jira to Q command
    sync_parser = subparsers.add_parser('sync-jira-to-q', help='Sync Jira issues to Q Business')
    sync_parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Preview sync without uploading documents'
    )
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Check Q Business sync job status')
    status_parser.add_argument(
        '--execution-id',
        help='Sync job execution ID (optional - shows recent jobs if omitted)'
    )
    
    # Sync Q index command
    sync_q_parser = subparsers.add_parser('sync-q-index', help='Start Q Business data source sync job')
    
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
        # Load configuration
        if args.config:
            config = load_config_from_file(args.config)
        else:
            config = ConnectorConfig.from_env()
        
        # Create connector
        connector = JiraQBusinessConnector(config)
        
        # Execute command
        command_functions = {
            'test': cmd_test,
            'projects': cmd_projects,
            'sync-jira-to-q': cmd_sync,
            'status': cmd_status,
            'sync-q-index': cmd_start_sync,
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