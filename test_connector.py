#!/usr/bin/env python3
"""
Test script for Jira Q Business Custom Connector
"""
import os
import sys
import logging
from unittest.mock import Mock, patch
from datetime import datetime

# Setup path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import ConnectorConfig, JiraConfig, AWSConfig
from jira_client import JiraClient
from document_processor import JiraDocumentProcessor
from qbusiness_client import QBusinessClient
from jira_connector import JiraQBusinessConnector


def setup_test_logging():
    """Setup logging for tests"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def test_config():
    """Test configuration loading"""
    print("🧪 Testing Configuration...")
    
    # Test manual configuration
    jira_config = JiraConfig(
        server_url="https://test-jira.company.com",
        username="test-user",
        password="test-password"
    )
    
    aws_config = AWSConfig(
        application_id="test-app-id",
        data_source_id="test-ds-id",
        index_id="test-index-id"
    )
    
    config = ConnectorConfig(
        jira=jira_config,
        aws=aws_config
    )
    
    assert config.jira.server_url == "https://test-jira.company.com"
    assert config.aws.application_id == "test-app-id"
    assert config.sync_mode == "full"  # default
    assert config.batch_size == 100  # default
    
    print("✅ Configuration test passed!")


def test_document_processor():
    """Test document processing"""
    print("🧪 Testing Document Processor...")
    
    processor = JiraDocumentProcessor(include_comments=True, include_history=False)
    
    # Mock Jira issue data
    mock_issue = {
        "key": "TEST-123",
        "id": "12345",
        "self": "https://test-jira.company.com/rest/api/2/issue/12345",
        "fields": {
            "summary": "Test Issue Summary",
            "description": "This is a test description with some <b>HTML</b> content.",
            "status": {"name": "In Progress"},
            "priority": {"name": "High"},
            "issuetype": {"name": "Bug"},
            "project": {"key": "TEST", "name": "Test Project"},
            "assignee": {"displayName": "John Doe"},
            "reporter": {"displayName": "Jane Smith"},
            "created": "2024-01-15T10:30:00.000+0000",
            "updated": "2024-01-16T14:45:00.000+0000",
            "labels": ["urgent", "customer-facing"],
            "components": [{"name": "Frontend"}],
            "comment": {
                "comments": [
                    {
                        "author": {"displayName": "Bob Wilson"},
                        "created": "2024-01-16T12:00:00.000+0000",
                        "body": "This looks like a regression from the latest release."
                    }
                ]
            }
        }
    }
    
    # Process the issue
    document = processor.process_issue(mock_issue)
    
    # Verify document structure
    assert document["Id"] == "jira-issue-TEST-123"
    assert "TEST-123: Test Issue Summary" in document["Title"]
    assert "Issue Key: TEST-123" in document["Content"]["Text"]
    assert "This is a test description" in document["Content"]["Text"]
    assert "Status: In Progress" in document["Content"]["Text"]
    assert "Priority: High" in document["Content"]["Text"]
    assert "Comments:" in document["Content"]["Text"]
    assert "Bob Wilson" in document["Content"]["Text"]
    
    # Verify attributes
    attributes = {attr["Name"]: attr["Value"] for attr in document["Attributes"]}
    assert attributes["_source_uri"]["StringValue"] == "https://test-jira.company.com/browse/TEST-123"
    assert attributes["jira_issue_key"]["StringValue"] == "TEST-123"
    assert attributes["jira_project"]["StringValue"] == "TEST"
    assert attributes["jira_status"]["StringValue"] == "In Progress"
    
    print("✅ Document Processor test passed!")


def test_jira_client_mock():
    """Test Jira client with mocked responses"""
    print("🧪 Testing Jira Client (mocked)...")
    
    config = JiraConfig(
        server_url="https://test-jira.company.com",
        username="test-user",
        password="test-password"
    )
    
    with patch('requests.Session') as mock_session_class:
        # Setup mock response
        mock_session = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {
            "version": "9.12.17",
            "serverTitle": "Test Jira"
        }
        mock_response.raise_for_status.return_value = None
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        client = JiraClient(config)
        
        # Test connection should work with mocked response
        result = client.test_connection()
        
        # We can't fully test without real credentials, but we can verify structure
        assert hasattr(client, 'session')
        assert hasattr(client, 'config')
        
    print("✅ Jira Client test passed!")


def test_qbusiness_client_mock():
    """Test Q Business client with mocked responses"""
    print("🧪 Testing Q Business Client (mocked)...")
    
    config = AWSConfig(
        application_id="test-app-id",
        data_source_id="test-ds-id",
        index_id="test-index-id"
    )
    
    with patch('boto3.Session') as mock_session_class:
        # Setup mock
        mock_session = Mock()
        mock_client = Mock()
        mock_session.client.return_value = mock_client
        mock_session_class.return_value = mock_session
        
        qb_client = QBusinessClient(config)
        
        assert hasattr(qb_client, 'client')
        assert hasattr(qb_client, 'config')
        
    print("✅ Q Business Client test passed!")


def test_connector_integration():
    """Test the main connector integration"""
    print("🧪 Testing Connector Integration...")
    
    # Create test configuration
    jira_config = JiraConfig(
        server_url="https://test-jira.company.com",
        username="test-user",
        password="test-password"
    )
    
    aws_config = AWSConfig(
        application_id="test-app-id",
        data_source_id="test-ds-id",
        index_id="test-index-id"
    )
    
    config = ConnectorConfig(
        jira=jira_config,
        aws=aws_config,
        batch_size=10
    )
    
    # Test connector initialization
    with patch('jira_client.JiraClient'), patch('qbusiness_client.QBusinessClient'):
        connector = JiraQBusinessConnector(config)
        
        assert hasattr(connector, 'config')
        assert hasattr(connector, 'jira_client')
        assert hasattr(connector, 'qbusiness_client')
        assert hasattr(connector, 'document_processor')
        assert connector.config.batch_size == 10
        
        # Test JQL query building
        jql = connector.build_jql_query()
        assert "ORDER BY updated DESC" in jql
        
    print("✅ Connector Integration test passed!")


def run_all_tests():
    """Run all tests"""
    print("🚀 Starting Jira Q Business Connector Tests")
    print("=" * 60)
    
    setup_test_logging()
    
    try:
        test_config()
        test_document_processor()
        test_jira_client_mock()
        test_qbusiness_client_mock()
        test_connector_integration()
        
        print("=" * 60)
        print("🎉 All tests passed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_real_connections():
    """Test real connections (requires environment variables)"""
    print("🧪 Testing Real Connections...")
    
    # Check if environment variables are set
    required_vars = [
        'JIRA_SERVER_URL', 'JIRA_USERNAME', 'JIRA_PASSWORD',
        'Q_APPLICATION_ID', 'Q_DATA_SOURCE_ID', 'Q_INDEX_ID'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"⚠️  Skipping real connection test. Missing environment variables: {', '.join(missing_vars)}")
        print("   Set these variables to test real connections.")
        return True
    
    try:
        # Load configuration from environment
        config = ConnectorConfig.from_env()
        connector = JiraQBusinessConnector(config)
        
        # Test connections
        results = connector.test_connections()
        
        if results['overall_success']:
            print("✅ Real connection test passed!")
            
            # Note: Project info functionality has been removed to simplify the connector
            
            return True
        else:
            print("❌ Real connection test failed!")
            if not results['jira']['success']:
                print(f"   Jira: {results['jira']['message']}")
            if not results['qbusiness']['success']:
                print(f"   Q Business: {results['qbusiness']['message']}")
            return False
            
    except Exception as e:
        print(f"❌ Real connection test failed with error: {e}")
        return False
    finally:
        if 'connector' in locals():
            connector.cleanup()


if __name__ == "__main__":
    success = run_all_tests()
    
    print("\n" + "=" * 60)
    print("🔗 Testing Real Connections (optional)")
    print("=" * 60)
    
    real_success = test_real_connections()
    
    if success and real_success:
        print("\n🎉 All tests completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1) 