#!/usr/bin/env python3
"""
Command Line Interface for Jira Q Business Connector
"""
import argparse
import logging
import sys

# Status emoji mapping
STATUS_EMOJIS = {
    'SUCCEEDED': '✅',
    'FAILED': '❌', 
    'RUNNING': '🔄',
    'STOPPING': '🛑',
    'STOPPED': '⏹️'
}

def get_status_emoji(status: str) -> str:
    """Get emoji for sync job status"""
    return STATUS_EMOJIS.get(status, '❓')

def print_result(success: bool, message: str, prefix: str = ""):
    """Print a result message with appropriate emoji"""
    emoji = "✅" if success else "❌"
    print(f"{prefix}{emoji} {message}")

def print_warning(message: str, prefix: str = ""):
    """Print a warning message"""
    print(f"{prefix}⚠️  Warning: {message}")

def print_info(message: str, prefix: str = ""):
    """Print an info message"""
    print(f"{prefix}ℹ️  {message}")


def setup_logging(level: str = "INFO"):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Reduce noise from third-party libraries
    logging.getLogger('boto3').setLevel(logging.WARNING)
    logging.getLogger('botocore').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)


def cmd_doctor(args, connector):
    """Test connections to Jira and Q Business"""
    print("🩺 Running connector diagnostics...")
    
    results = connector.test_connections()
    
    if results['overall_success']:
        print_result(True, "All connections successful!")
        return 0
    else:
        print_result(False, "Connection issues detected:")
        if not results['jira']['success']:
            print(f"   Jira: {results['jira']['message']}")
        if not results['qbusiness']['success']:
            print(f"   Q Business: {results['qbusiness']['message']}")
        return 1


def cmd_status(args, connector):
    """Check Q Business sync job status"""
    try:
        if args.execution_id:
            # Get specific sync job status
            print(f"🔍 Checking sync job status: {args.execution_id}")
            
            result = connector.get_sync_job_status(args.execution_id)
            
            if result['success']:
                job = result['job']
                status = job.get('status', 'Unknown')
                
                print(f"📊 Sync Job Details:")
                print(f"   Execution ID: {job.get('executionId', 'Unknown')}")
                print(f"   Status: {status}")
                print(f"   Data Source: {job.get('dataSourceId', 'Unknown')}")
                
                if 'startTime' in job:
                    print(f"   Started: {job['startTime']}")
                if 'endTime' in job:
                    print(f"   Ended: {job['endTime']}")
                
                # Show metrics if available
                if status in ['SUCCEEDED', 'FAILED', 'STOPPED']:
                    print(f"\n📈 Attempting to get sync metrics...")
                    metrics_result = connector.qbusiness_client.get_data_source_sync_job_metrics(args.execution_id)
                    
                    if metrics_result['success'] and 'metrics' in metrics_result:
                        metrics = metrics_result['metrics']
                        print(f"   Documents Added: {metrics.get('documentsAdded', 'N/A')}")
                        print(f"   Documents Modified: {metrics.get('documentsModified', 'N/A')}")
                        print(f"   Documents Deleted: {metrics.get('documentsDeleted', 'N/A')}")
                        print(f"   Documents Failed: {metrics.get('documentsFailed', 'N/A')}")
                    else:
                        print(f"   ⚠️  Metrics not available: {metrics_result.get('message', 'Unknown error')}")
                
                return 0 if status == 'SUCCEEDED' else 1
            else:
                print(f"❌ Failed to get sync job status: {result['message']}")
                return 1
                
        else:
            # List recent sync jobs
            print("📋 Recent Q Business sync jobs:")
            
            result = connector.qbusiness_client.list_data_source_sync_jobs(max_results=10)
            
            if result['success'] and 'sync_jobs' in result:
                jobs = result['sync_jobs']
                
                if not jobs:
                    print_info("No sync jobs found", "   ")
                    return 0
                
                for job in jobs[:5]:  # Show top 5
                    execution_id = job.get('executionId', 'Unknown')
                    status = job.get('status', 'Unknown')
                    start_time = job.get('startTime', 'Unknown')
                    
                    status_emoji = get_status_emoji(status)
                    
                    print(f"   {status_emoji} {execution_id} | {status} | {start_time}")
                
                print(f"\n💡 Check specific job: python -m jira_q_connector status --execution-id <id>")
                return 0
            else:
                print(f"❌ Failed to list sync jobs: {result.get('message', 'Unknown error')}")
                return 1
                
    except Exception as e:
        print(f"❌ Error checking status: {e}")
        return 1


def cmd_full_sync(args, connector):
    """Complete sync workflow: Start job → Sync ACL → Sync documents → Stop job"""
    clean_sync = args.clean
    
    print(f"🚀 Starting complete sync workflow: Jira → Q Business")
    
    try:
        # Step 1: Start Q Business sync job
        print(f"\n📋 Step 1 of 5: Starting Q Business data source sync job...")
        
        sync_job_result = connector.start_qbusiness_sync()
        
        if not sync_job_result['success']:
            print(f"❌ Failed to start sync job: {sync_job_result['message']}")
            return 1
        
        execution_id = sync_job_result['execution_id']
        print(f"✅ Sync job started successfully")
        print(f"   Execution ID: {execution_id}")
        
        # Step 1.5: Clean existing documents if requested
        if clean_sync:
            print(f"\n🧹 Step 1.5 of 5: Cleaning existing documents...")
            clean_result = connector.clean_all_documents(execution_id)
            
            if clean_result['success']:
                print(f"✅ Cleaned {clean_result.get('deleted', 0)} existing documents")
            else:
                print(f"⚠️  Warning: Failed to clean documents: {clean_result['message']}")
                print("   Continuing with sync...")
        
        # Step 2: Sync ACL information first (so users/groups exist before documents reference them)
        print(f"\n🔒 Step 2 of 5: Syncing ACL information to Q Business User Store...")
        
        # Sync ACL information with the execution ID
        acl_result = connector.sync_acl_with_execution_id(execution_id)
        
        if acl_result['success']:
            print(f"✅ ACL sync completed successfully")
            print(f"   Users: {acl_result.get('stats', {}).get('users', 0)}")
            print(f"   Groups: {acl_result.get('stats', {}).get('groups', 0)}")
            print(f"   Memberships: {acl_result.get('stats', {}).get('memberships', 0)}")
            acl_success = True
        else:
            print(f"❌ ACL sync failed: {acl_result.get('message', 'Unknown error')}")
            print("   Cannot proceed with document sync without proper ACL setup")
            # Stop the sync job and return error
            print(f"\n🛑 Step 4 of 5: Stopping sync job due to ACL sync failure...")
            stop_result = connector.stop_qbusiness_sync(execution_id)
            return 1
        
        # Step 3: Sync Jira documents (after ACL is properly set up)
        print(f"\n📄 Step 3 of 5: Syncing Jira issues to Q Business...")
        
        # Real sync with execution ID (only if ACL sync was successful)
        sync_result = connector.sync_issues_with_execution_id(execution_id, clean_first=clean_sync)
        
        if not sync_result['success']:
            print(f"❌ Document sync failed: {sync_result['message']}")
            # Still try to stop the sync job
            print(f"\n🛑 Step 4 of 5: Stopping sync job due to errors...")
            stop_result = connector.stop_qbusiness_sync(execution_id)
            return 1
        
        print(f"✅ Document sync completed successfully")
        print(f"   Processed: {sync_result['stats']['processed_issues']} issues")
        print(f"   Uploaded: {sync_result['stats']['uploaded_documents']} documents")
        
        if sync_result['stats'].get('deleted_documents', 0) > 0:
            print(f"   Deleted: {sync_result['stats']['deleted_documents']} old documents")
        
        # Step 4: Stop the sync job
        print(f"\n🏁 Step 4 of 5: Stopping Q Business sync job...")
        
        stop_result = connector.stop_qbusiness_sync(execution_id)
        
        if stop_result['success']:
            print(f"✅ Sync job stopped successfully")
        else:
            print(f"⚠️  Warning: Failed to stop sync job: {stop_result['message']}")
            print("   The sync job may continue running in the background")
        
        # Step 5: Completion
        print(f"\n🎯 Step 5 of 5: Sync completed successfully!")
        
        print(f"   Execution ID: {execution_id}")
        print(f"   💡 Check sync status with: jira-q-connector status --execution-id {execution_id}")
        
        print(f"\n🎉 Complete sync workflow finished successfully!")
        return 0
        
    except KeyboardInterrupt:
        print(f"\n🛑 Sync interrupted by user")
        if 'execution_id' in locals():
            print(f"🔧 Attempting to stop sync job {execution_id}...")
            try:
                connector.stop_qbusiness_sync(execution_id)
                print("✅ Sync job stopped")
            except:
                print("⚠️  Could not stop sync job - it may continue running")
        return 130
    except Exception as e:
        print(f"❌ Unexpected error during sync: {e}")
        if 'execution_id' in locals():
            print(f"🔧 Attempting to stop sync job {execution_id}...")
            try:
                connector.stop_qbusiness_sync(execution_id)
            except:
                pass
        return 1



def cmd_stop(args, connector):
    """Stop a running Q Business sync job"""
    try:
        if args.execution_id:
            # Stop specific sync job
            execution_id = args.execution_id
            print(f"🛑 Stopping Q Business sync job: {execution_id}")
            
            result = connector.stop_qbusiness_sync(execution_id)
            
            if result['success']:
                print(f"✅ Sync job stopped successfully")
                print(f"   Execution ID: {execution_id}")
                return 0
            else:
                print(f"❌ Failed to stop sync job: {result['message']}")
                return 1
                
        else:
            # Find and stop the latest running sync job
            print("🔍 Looking for running sync jobs to stop...")
            
            list_result = connector.qbusiness_client.list_data_source_sync_jobs(max_results=10)
            
            if not list_result['success']:
                print(f"❌ Failed to list sync jobs: {list_result['message']}")
                return 1
            
            jobs = list_result.get('sync_jobs', [])
            running_jobs = [job for job in jobs if job.get('status') in ['RUNNING', 'STOPPING']]
            
            if not running_jobs:
                print_info("No running sync jobs found")
                return 0
            
            if len(running_jobs) == 1:
                # Stop the single running job
                job = running_jobs[0]
                execution_id = job.get('executionId')
                status = job.get('status')
                
                print(f"🛑 Stopping {status.lower()} sync job: {execution_id}")
                
                result = connector.stop_qbusiness_sync(execution_id)
                
                if result['success']:
                    print(f"✅ Sync job stopped successfully")
                    return 0
                else:
                    print(f"❌ Failed to stop sync job: {result['message']}")
                    return 1
            else:
                # Multiple running jobs - show them and ask user to specify
                print(f"🔄 Found {len(running_jobs)} running sync jobs:")
                for job in running_jobs:
                    execution_id = job.get('executionId', 'Unknown')
                    status = job.get('status', 'Unknown')
                    start_time = job.get('startTime', 'Unknown')
                    print(f"   🔄 {execution_id} | {status} | {start_time}")
                
                print(f"\n💡 Specify which job to stop: jira-q-connector stop --execution-id <id>")
                return 1
                
    except Exception as e:
        print(f"❌ Error stopping sync job: {e}")
        return 1


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Jira Custom Connector for Amazon Q Business",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test connections
  jira-q-connector doctor
  
  # Complete sync workflow (recommended)
  jira-q-connector sync
  
  # Clean sync (delete duplicates, then upload)
  jira-q-connector sync --clean
  
  # Debug mode with detailed logging
  jira-q-connector sync --debug
  
  # Check recent sync jobs
  jira-q-connector status
  
  # Check specific sync job status
  jira-q-connector status --execution-id <id>
  
  # Stop running sync jobs
  jira-q-connector stop
  jira-q-connector stop --execution-id <id>

Environment Variables:
  JIRA_SERVER_URL      - Jira server URL (required)
  JIRA_USERNAME        - Jira username (required)
  JIRA_PASSWORD        - Jira password or API token (required)
  Q_APPLICATION_ID     - Q Business application ID (required)
  Q_DATA_SOURCE_ID     - Q Business data source ID (required)
  Q_INDEX_ID           - Q Business index ID (required)
  
  AWS_REGION           - AWS region (default: us-east-1)
  BATCH_SIZE           - Documents per batch (default: 10)
  INCLUDE_COMMENTS     - Include issue comments (default: true)
  INCLUDE_HISTORY      - Include change history (default: false)
  
  PROJECTS             - Comma-separated project keys to sync
  ISSUE_TYPES          - Comma-separated issue types to sync
  JQL_FILTER           - Custom JQL filter for issue selection
        """
    )
    
    parser.add_argument(
        "--log-level", "-l",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Log level (default: INFO)"
    )
    
    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="Enable debug mode (equivalent to --log-level DEBUG)"
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
    
    # Sync command (new)
    sync_parser = subparsers.add_parser('sync', help='Sync Jira issues to Q Business')
    sync_parser.add_argument(
        '--clean',
        action='store_true',
        help='Delete all existing documents before syncing (full refresh)'
    )

    
    # Stop command
    stop_parser = subparsers.add_parser('stop', help='Stop a running Q Business sync job')
    stop_parser.add_argument(
        '--execution-id',
        help='Sync job execution ID (optional - stops specific job if provided, otherwise stops latest running job)'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Determine log level: --debug flag overrides --log-level
    log_level = "DEBUG" if args.debug else args.log_level
    
    # Setup logging
    setup_logging(log_level)
    
    try:
        # Import here to avoid circular imports
        from .config import ConnectorConfig
        from .jira_connector import JiraQBusinessConnector
        
        # Load configuration from environment
        try:
            config = ConnectorConfig.from_env()
        except ValueError as e:
            print(f"\n❌ Configuration Error: {e}")
            print("\n🔧 Quick Setup:")
            print("   1. Copy env.example to .env:")
            print("      cp env.example .env")
            print("   2. Edit .env file with your Jira and Q Business settings")
            print("   3. Run the command again")
            print("\n📖 See README.md for detailed configuration instructions")
            return 1
        
        # Create connector
        connector = JiraQBusinessConnector(config)
        
        # Execute command
        command_functions = {
            'doctor': cmd_doctor,
            'status': cmd_status,
            'sync': cmd_full_sync,
            'stop': cmd_stop
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
        if log_level == "DEBUG":
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main()) 