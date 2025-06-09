#!/usr/bin/env python3
"""
Demo script for Jira Q Business Custom Connector
Shows how the connector processes Jira issues into Q Business documents
"""
import json
from datetime import datetime
from document_processor import JiraDocumentProcessor


def create_mock_jira_issue():
    """Create a realistic mock Jira issue for demonstration"""
    return {
        "id": "12345",
        "key": "PROJ-123",
        "self": "https://demo-jira.company.com/rest/api/2/issue/12345",
        "fields": {
            "summary": "Implement user authentication system",
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": "We need to implement a secure user authentication system that supports:"
                            }
                        ]
                    },
                    {
                        "type": "bulletList",
                        "content": [
                            {
                                "type": "listItem",
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [
                                            {
                                                "type": "text",
                                                "text": "Multi-factor authentication (MFA)"
                                            }
                                        ]
                                    }
                                ]
                            },
                            {
                                "type": "listItem",
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [
                                            {
                                                "type": "text",
                                                "text": "OAuth2 integration"
                                            }
                                        ]
                                    }
                                ]
                            },
                            {
                                "type": "listItem",
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [
                                            {
                                                "type": "text",
                                                "text": "Password complexity requirements"
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            },
            "status": {
                "name": "In Progress",
                "id": "3",
                "statusCategory": {
                    "name": "In Progress",
                    "key": "indeterminate"
                }
            },
            "priority": {
                "name": "High",
                "id": "2"
            },
            "issuetype": {
                "name": "Story",
                "id": "10001"
            },
            "project": {
                "key": "PROJ",
                "name": "Demo Project",
                "id": "10000"
            },
            "assignee": {
                "accountId": "123456",
                "displayName": "Alice Johnson",
                "emailAddress": "alice.johnson@company.com"
            },
            "reporter": {
                "accountId": "789012",
                "displayName": "Bob Smith",
                "emailAddress": "bob.smith@company.com"
            },
            "creator": {
                "accountId": "789012",
                "displayName": "Bob Smith",
                "emailAddress": "bob.smith@company.com"
            },
            "created": "2024-01-15T10:30:00.000+0000",
            "updated": "2024-01-20T14:45:00.000+0000",
            "resolutiondate": None,
            "labels": ["authentication", "security", "backend"],
            "components": [
                {
                    "name": "Backend API",
                    "id": "10001"
                },
                {
                    "name": "Security",
                    "id": "10005"
                }
            ],
            "versions": [],
            "fixVersions": [
                {
                    "name": "v2.1.0",
                    "id": "10010",
                    "released": False
                }
            ],
            "environment": "Production deployment requires secure HTTPS connections",
            "comment": {
                "comments": [
                    {
                        "id": "10001",
                        "author": {
                            "displayName": "Alice Johnson",
                            "emailAddress": "alice.johnson@company.com"
                        },
                        "body": "I've started working on the OAuth2 integration. The third-party library looks promising.",
                        "created": "2024-01-16T09:15:00.000+0000",
                        "updated": "2024-01-16T09:15:00.000+0000"
                    },
                    {
                        "id": "10002",
                        "author": {
                            "displayName": "Charlie Brown",
                            "emailAddress": "charlie.brown@company.com"
                        },
                        "body": "Make sure to follow OWASP security guidelines for password storage and session management.",
                        "created": "2024-01-17T11:30:00.000+0000",
                        "updated": "2024-01-17T11:30:00.000+0000"
                    },
                    {
                        "id": "10003",
                        "author": {
                            "displayName": "Diana Prince",
                            "emailAddress": "diana.prince@company.com"
                        },
                        "body": "Please coordinate with the mobile team for consistent authentication flow across platforms.",
                        "created": "2024-01-18T16:20:00.000+0000",
                        "updated": "2024-01-18T16:20:00.000+0000"
                    }
                ]
            },
            "attachment": [
                {
                    "id": "10001",
                    "filename": "auth_architecture.pdf",
                    "size": 245760,
                    "mimeType": "application/pdf",
                    "content": "https://demo-jira.company.com/secure/attachment/10001/auth_architecture.pdf"
                },
                {
                    "id": "10002",
                    "filename": "security_requirements.docx",
                    "size": 102400,
                    "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "content": "https://demo-jira.company.com/secure/attachment/10002/security_requirements.docx"
                }
            ],
            "worklog": {
                "worklogs": [
                    {
                        "id": "10001",
                        "author": {
                            "displayName": "Alice Johnson"
                        },
                        "comment": "Initial research and OAuth2 library evaluation",
                        "started": "2024-01-16T08:00:00.000+0000",
                        "timeSpent": "4h",
                        "timeSpentSeconds": 14400
                    }
                ]
            }
        },
        "changelog": {
            "histories": [
                {
                    "id": "10001",
                    "author": {
                        "displayName": "Bob Smith"
                    },
                    "created": "2024-01-15T10:30:00.000+0000",
                    "items": [
                        {
                            "field": "status",
                            "fieldtype": "jira",
                            "from": "1",
                            "fromString": "To Do",
                            "to": "3",
                            "toString": "In Progress"
                        }
                    ]
                },
                {
                    "id": "10002",
                    "author": {
                        "displayName": "Project Manager"
                    },
                    "created": "2024-01-16T12:00:00.000+0000",
                    "items": [
                        {
                            "field": "assignee",
                            "fieldtype": "jira",
                            "from": None,
                            "fromString": None,
                            "to": "123456",
                            "toString": "Alice Johnson"
                        }
                    ]
                }
            ]
        }
    }


def demo_document_processing():
    """Demonstrate document processing capabilities"""
    print("🚀 Jira Q Business Custom Connector Demo")
    print("=" * 60)
    
    # Create mock issue
    mock_issue = create_mock_jira_issue()
    
    print("📄 Sample Jira Issue:")
    print(f"  Key: {mock_issue['key']}")
    print(f"  Summary: {mock_issue['fields']['summary']}")
    print(f"  Status: {mock_issue['fields']['status']['name']}")
    print(f"  Assignee: {mock_issue['fields']['assignee']['displayName']}")
    print(f"  Project: {mock_issue['fields']['project']['name']}")
    print(f"  Comments: {len(mock_issue['fields']['comment']['comments'])}")
    print()
    
    # Process with different configurations
    configurations = [
        {"include_comments": True, "include_history": False, "name": "Standard"},
        {"include_comments": True, "include_history": True, "name": "Full"},
        {"include_comments": False, "include_history": False, "name": "Minimal"},
    ]
    
    for config in configurations:
        print(f"🔧 Processing with {config['name']} Configuration:")
        print(f"   Include Comments: {config['include_comments']}")
        print(f"   Include History: {config['include_history']}")
        
        processor = JiraDocumentProcessor(
            include_comments=config['include_comments'],
            include_history=config['include_history']
        )
        
        document = processor.process_issue(mock_issue)
        
        # Show document structure
        print(f"\n📋 Generated Q Business Document:")
        print(f"   ID: {document['Id']}")
        print(f"   Title: {document['Title']}")
        print(f"   Content Type: {document['ContentType']}")
        print(f"   URI: {document['Uri']}")
        print(f"   Attributes: {len(document['Attributes'])} items")
        
        # Show content preview
        content = document['Content']['Text']
        lines = content.split('\n')
        print(f"   Content Preview ({len(lines)} lines):")
        
        for i, line in enumerate(lines[:10]):  # Show first 10 lines
            if line.strip():
                print(f"     {i+1:2d}: {line[:80]}{'...' if len(line) > 80 else ''}")
        
        if len(lines) > 10:
            print(f"     ... ({len(lines) - 10} more lines)")
        
        # Show key attributes
        print(f"\n🏷️  Key Attributes:")
        for attr in document['Attributes']:
            name = attr['Name']
            if name in ['_source_uri', 'jira_issue_key', 'jira_project', 'jira_status']:
                value = attr['Value']
                if 'StringValue' in value:
                    print(f"     {name}: {value['StringValue']}")
                elif 'DateValue' in value:
                    print(f"     {name}: {value['DateValue']}")
        
        print("\n" + "-" * 60)
    
    print("\n✅ Document processing demo completed!")
    print("\n💡 This demonstrates how Jira issues are converted to Q Business documents")
    print("   with configurable content inclusion options.")


def demo_batch_processing():
    """Demonstrate batch processing capabilities"""
    print("\n🔄 Batch Processing Demo")
    print("=" * 60)
    
    # Create multiple mock issues
    issues = []
    for i in range(5):
        issue = create_mock_jira_issue()
        issue['key'] = f"PROJ-{120 + i}"
        issue['id'] = str(12340 + i)
        issue['fields']['summary'] = f"Sample issue #{i+1}: {['Bug fix', 'Feature request', 'Documentation', 'Security update', 'Performance improvement'][i]}"
        issue['fields']['status']['name'] = ['To Do', 'In Progress', 'Code Review', 'Testing', 'Done'][i]
        issue['fields']['priority']['name'] = ['Low', 'Medium', 'High', 'Critical', 'Medium'][i]
        issues.append(issue)
    
    print(f"📊 Processing {len(issues)} issues in batch:")
    
    processor = JiraDocumentProcessor(include_comments=True, include_history=False)
    documents = processor.create_batch_documents(issues)
    
    print(f"   Successfully created {len(documents)} documents")
    print("\n📋 Document Summary:")
    
    for i, doc in enumerate(documents):
        print(f"   {i+1}. {doc['Id']} - {doc['Title'][:60]}{'...' if len(doc['Title']) > 60 else ''}")
    
    print(f"\n📈 Batch Statistics:")
    print(f"   Total Issues: {len(issues)}")
    print(f"   Documents Created: {len(documents)}")
    print(f"   Success Rate: {len(documents)/len(issues)*100:.1f}%")
    
    # Calculate content sizes
    total_content_size = sum(len(doc['Content']['Text']) for doc in documents)
    avg_content_size = total_content_size / len(documents) if documents else 0
    
    print(f"   Total Content Size: {total_content_size:,} characters")
    print(f"   Average Content Size: {avg_content_size:.0f} characters")
    
    print("\n✅ Batch processing demo completed!")


def show_sample_config():
    """Show sample configuration options"""
    print("\n⚙️ Configuration Options Demo")
    print("=" * 60)
    
    print("📝 Environment Variables:")
    env_vars = [
        ("JIRA_SERVER_URL", "https://your-jira.company.com", "Jira server URL"),
        ("JIRA_USERNAME", "your-username", "Jira username"),
        ("JIRA_PASSWORD", "your-password", "Jira password or API token"),
        ("Q_APPLICATION_ID", "app-12345", "Q Business application ID"),
        ("Q_DATA_SOURCE_ID", "ds-67890", "Q Business data source ID"),
        ("Q_INDEX_ID", "idx-abcde", "Q Business index ID"),
        ("SYNC_MODE", "full", "Sync mode: full or incremental"),
        ("BATCH_SIZE", "100", "Batch size for processing"),
        ("INCLUDE_COMMENTS", "true", "Include issue comments"),
        ("PROJECTS", "PROJ1,PROJ2", "Comma-separated project keys"),
        ("JQL_FILTER", "status != 'Closed'", "Custom JQL filter"),
    ]
    
    for var, example, description in env_vars:
        print(f"   {var:20} = {example:25} # {description}")
    
    print("\n📄 JSON Configuration Example:")
    config_example = {
        "jira": {
            "server_url": "https://your-jira.company.com",
            "username": "your-username",
            "password": "your-password"
        },
        "aws": {
            "application_id": "app-12345",
            "data_source_id": "ds-67890",
            "index_id": "idx-abcde"
        },
        "sync_mode": "full",
        "batch_size": 100,
        "include_comments": True,
        "projects": ["PROJ1", "PROJ2"],
        "jql_filter": "status != 'Closed'"
    }
    
    print(json.dumps(config_example, indent=2))
    
    print("\n🔧 Usage Examples:")
    commands = [
        ("python main.py test", "Test connections to Jira and Q Business"),
        ("python main.py projects", "List available Jira projects"),
        ("python main.py sync --dry-run", "Preview sync without uploading"),
        ("python main.py sync", "Perform full sync"),
        ("python main.py sync -c config.json", "Use custom configuration file"),
        ("python main.py status --execution-id abc123", "Check sync job status"),
    ]
    
    for command, description in commands:
        print(f"   {command:40} # {description}")
    
    print("\n✅ Configuration demo completed!")


if __name__ == "__main__":
    demo_document_processing()
    demo_batch_processing()
    show_sample_config()
    
    print("\n🎉 Demo completed successfully!")
    print("\n📚 Next Steps:")
    print("   1. Set up your Jira and Q Business credentials")
    print("   2. Run 'python main.py test' to verify connections")
    print("   3. Use 'python main.py sync --dry-run' to preview")
    print("   4. Execute 'python main.py sync' for full synchronization")
    print("\n📖 For detailed documentation, see README.md") 