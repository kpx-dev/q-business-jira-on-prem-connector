#!/usr/bin/env python3

from setuptools import setup, find_packages
import os

# Read the README file
def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

# Define requirements directly (instead of reading from file)
def get_requirements():
    return [
        "requests>=2.25.0",
        "boto3>=1.26.0", 
        "pydantic>=1.8.0",
        "python-dotenv>=0.19.0",
    ]

# Get version from package without importing
def get_version():
    version_file = os.path.join(os.path.dirname(__file__), 'src', 'jira_q_connector', '__init__.py')
    with open(version_file, 'r') as f:
        for line in f:
            if line.startswith('__version__'):
                return line.split('=')[1].strip().strip('"\'')
    return "1.0.0"

setup(
    name="jira-q-connector",
    version=get_version(),
    author="Jira Q Business Connector Team",
    author_email="",
    description="A custom connector that synchronizes Jira on-premises server with Amazon Q Business",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/your-repo/jira-q-connector",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Systems Administration",
    ],
    python_requires=">=3.8",
    install_requires=get_requirements(),
    entry_points={
        "console_scripts": [
            "jira-q-connector=jira_q_connector.cli:main",
        ],
    },
    include_package_data=True,
    keywords="jira amazon-q-business connector enterprise-search",
    project_urls={
        "Bug Reports": "https://github.com/your-repo/jira-q-connector/issues",
        "Source": "https://github.com/your-repo/jira-q-connector",
        "Documentation": "https://github.com/your-repo/jira-q-connector#readme",
    },
) 