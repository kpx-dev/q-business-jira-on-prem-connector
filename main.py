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
    execution_id = args.execution_id
    
    print(f"Checking status of sync job: {execution_id}")
    
    result = connector.get_sync_job_status(execution_id)
    
    if result['success']:
        job = result['sync_job']
        print(f"✅ Sync job status: {job.get('status', 'Unknown')}")
        
        # Print additional details if available
        if 'startTime' in job:
            print(f"   Start Time: {job['startTime']}")
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
        
        return 0
    else:
        print(f"❌ Failed to get sync job status: {result['message']}")
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
  python main.py sync --dry-run
  
  # Full sync
  python main.py sync
  
  # Start Q Business sync job
  python main.py start-sync
  
  # Check sync job status
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
    
    # Sync command
    sync_parser = subparsers.add_parser('sync', help='Sync Jira issues to Q Business')
    sync_parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Preview sync without uploading documents'
    )
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Check Q Business sync job status')
    status_parser.add_argument(
        '--execution-id',
        required=True,
        help='Sync job execution ID'
    )
    
    # Start sync command
    start_sync_parser = subparsers.add_parser('start-sync', help='Start Q Business data source sync job')
    
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
            'sync': cmd_sync,
            'status': cmd_status,
            'start-sync': cmd_start_sync
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