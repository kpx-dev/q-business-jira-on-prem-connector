"""
CLI utility functions for consistent output formatting
"""
from typing import Dict, Any, Optional


class CLIFormatter:
    """Utility class for consistent CLI output formatting"""
    
    # Color codes for terminal output
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'
    
    @staticmethod
    def success(message: str) -> str:
        """Format success message"""
        return f"✅ {message}"
    
    @staticmethod
    def error(message: str) -> str:
        """Format error message"""
        return f"❌ {message}"
    
    @staticmethod
    def warning(message: str) -> str:
        """Format warning message"""
        return f"⚠️  {message}"
    
    @staticmethod
    def info(message: str) -> str:
        """Format info message"""
        return f"ℹ️  {message}"
    
    @staticmethod
    def step(step_num: int, total_steps: int, message: str) -> str:
        """Format step message"""
        return f"\n📋 Step {step_num} of {total_steps}: {message}..."
    
    @staticmethod
    def result(label: str, value: Any) -> str:
        """Format result with label and value"""
        return f"   {label}: {value}"
    
    @staticmethod
    def section_header(title: str) -> str:
        """Format section header"""
        return f"\n🔍 {title}"
    
    @staticmethod
    def bullet_point(message: str) -> str:
        """Format bullet point"""
        return f"   • {message}"


class ProgressReporter:
    """Utility class for reporting sync progress"""
    
    def __init__(self):
        self.current_step = 0
        self.total_steps = 5
        
    def start_workflow(self, workflow_name: str) -> None:
        """Start workflow reporting"""
        print(f"🚀 Starting {workflow_name}")
        
    def step(self, message: str) -> None:
        """Report a step"""
        self.current_step += 1
        print(CLIFormatter.step(self.current_step, self.total_steps, message))
        
    def success(self, message: str) -> None:
        """Report success"""
        print(CLIFormatter.success(message))
        
    def error(self, message: str) -> None:
        """Report error"""
        print(CLIFormatter.error(message))
        
    def warning(self, message: str) -> None:
        """Report warning"""
        print(CLIFormatter.warning(message))
        
    def result(self, label: str, value: Any) -> None:
        """Report a result"""
        print(CLIFormatter.result(label, value))
        
    def stats(self, stats_dict: Dict[str, Any]) -> None:
        """Report statistics"""
        for key, value in stats_dict.items():
            label = key.replace('_', ' ').title()
            self.result(label, value)


class ConnectionTester:
    """Utility class for testing connections"""
    
    @staticmethod
    def test_connection(service_name: str, test_func, *args, **kwargs) -> bool:
        """Test a connection and report results"""
        print(f"\n🔗 Testing {service_name} connection...")
        
        try:
            result = test_func(*args, **kwargs)
            
            if result.get('success'):
                print(CLIFormatter.success(f"{service_name} connection successful"))
                
                # Show additional info if available
                if 'message' in result:
                    print(CLIFormatter.result("Details", result['message']))
                    
                # Show service info if available  
                info_keys = ['application_info', 'server_info', 'user_info']
                for key in info_keys:
                    if key in result:
                        info = result[key]
                        if isinstance(info, dict):
                            for sub_key, sub_value in info.items():
                                if sub_value:
                                    print(CLIFormatter.result(sub_key.replace('_', ' ').title(), sub_value))
                        else:
                            print(CLIFormatter.result(key.replace('_', ' ').title(), info))
                
                return True
            else:
                print(CLIFormatter.error(f"{service_name} connection failed"))
                if 'message' in result:
                    print(CLIFormatter.result("Error", result['message']))
                return False
                
        except Exception as e:
            print(CLIFormatter.error(f"{service_name} connection failed"))
            print(CLIFormatter.result("Error", str(e)))
            return False


class SyncReporter:
    """Utility class for sync operation reporting"""
    
    def __init__(self):
        self.progress = ProgressReporter()
        
    def start_sync(self, sync_type: str = "complete sync workflow") -> None:
        """Start sync reporting"""
        self.progress.start_workflow(f"{sync_type}: Jira → Q Business")
        
    def step_start_job(self) -> None:
        """Report starting sync job"""
        self.progress.step("Starting Q Business data source sync job")
        
    def step_job_started(self, execution_id: str) -> None:
        """Report job started successfully"""
        self.progress.success("Sync job started successfully")
        self.progress.result("Execution ID", execution_id)
        
    def step_clean_documents(self) -> None:
        """Report cleaning documents"""
        self.progress.step("Cleaning existing documents")
        
    def step_clean_completed(self, deleted_count: int) -> None:
        """Report cleaning completed"""
        if deleted_count > 0:
            self.progress.success(f"Cleaned {deleted_count} existing documents")
        else:
            self.progress.warning("No documents found to clean")
            
    def step_sync_acl(self) -> None:
        """Report syncing ACL"""
        self.progress.step("Syncing ACL information to Q Business User Store")
        
    def step_acl_completed(self, stats: Dict[str, Any]) -> None:
        """Report ACL sync completed"""
        self.progress.success("ACL synchronization completed")
        self.progress.stats(stats)
        
    def step_sync_documents(self) -> None:
        """Report syncing documents"""
        self.progress.step("Syncing Jira issues to Q Business")
        
    def step_documents_completed(self, stats: Dict[str, Any]) -> None:
        """Report document sync completed"""
        self.progress.success("Document synchronization completed")
        self.progress.stats(stats)
        
    def step_stop_job(self) -> None:
        """Report stopping sync job"""
        self.progress.step("Stopping sync job and finalizing")
        
    def step_job_stopped(self) -> None:
        """Report job stopped successfully"""
        self.progress.success("Sync job completed successfully")
        
    def sync_completed(self, total_time: Optional[float] = None) -> None:
        """Report sync completed"""
        message = "🎉 Sync workflow completed successfully!"
        if total_time:
            message += f" Total time: {total_time:.1f}s"
        print(f"\n{message}")
        
    def sync_failed(self, error_message: str) -> None:
        """Report sync failed"""
        self.progress.error(f"Sync workflow failed: {error_message}")
        
    def sync_warning(self, warning_message: str) -> None:
        """Report sync warning"""
        self.progress.warning(warning_message)


class StatusReporter:
    """Utility class for status reporting"""
    
    @staticmethod
    def show_job_status(job_info: Dict[str, Any]) -> None:
        """Show sync job status"""
        print(CLIFormatter.section_header("Sync Job Status"))
        
        status = job_info.get('Status', 'Unknown')
        print(CLIFormatter.result("Status", status))
        
        if 'ExecutionId' in job_info:
            print(CLIFormatter.result("Execution ID", job_info['ExecutionId']))
            
        if 'StartTime' in job_info:
            print(CLIFormatter.result("Start Time", job_info['StartTime']))
            
        if 'EndTime' in job_info:
            print(CLIFormatter.result("End Time", job_info['EndTime']))
            
        if 'ErrorMessage' in job_info and job_info['ErrorMessage']:
            print(CLIFormatter.result("Error", job_info['ErrorMessage']))
            
        # Show metrics if available
        metrics = job_info.get('Metrics', {})
        if metrics:
            print(CLIFormatter.section_header("Metrics"))
            for key, value in metrics.items():
                label = key.replace('_', ' ').replace('Documents', 'Docs').title()
                print(CLIFormatter.result(label, value))
    
    @staticmethod
    def show_recent_jobs(jobs: list) -> None:
        """Show recent sync jobs"""
        if not jobs:
            print(CLIFormatter.info("No recent sync jobs found"))
            return
            
        print(CLIFormatter.section_header(f"Recent Sync Jobs ({len(jobs)})"))
        
        for i, job in enumerate(jobs[:5], 1):  # Show max 5 recent jobs
            status = job.get('Status', 'Unknown')
            execution_id = job.get('ExecutionId', 'Unknown')
            start_time = job.get('StartTime', 'Unknown')
            
            status_icon = "✅" if status == "SUCCEEDED" else "❌" if status == "FAILED" else "🔄"
            print(f"   {i}. {status_icon} {status} - {execution_id} ({start_time})")


class ConfigHelper:
    """Utility class for configuration help"""
    
    @staticmethod
    def show_setup_help() -> None:
        """Show configuration setup help"""
        print(CLIFormatter.error("Configuration Error"))
        print(CLIFormatter.section_header("Quick Setup"))
        print(CLIFormatter.bullet_point("Copy env.example to .env:"))
        print("      cp env.example .env")
        print(CLIFormatter.bullet_point("Edit .env file with your Jira and Q Business settings"))
        print(CLIFormatter.bullet_point("Run the command again"))
        print(CLIFormatter.section_header("Documentation"))
        print(CLIFormatter.bullet_point("See README.md for detailed configuration instructions"))
    
    @staticmethod  
    def show_debug_help() -> None:
        """Show debug mode help"""
        print(CLIFormatter.section_header("Debug Mode"))
        print(CLIFormatter.bullet_point("Use --debug or -d flag for detailed logging"))
        print(CLIFormatter.bullet_point("Shows complete API payloads and processing details"))
        print(CLIFormatter.bullet_point("Example: jira-q-connector sync --debug")) 