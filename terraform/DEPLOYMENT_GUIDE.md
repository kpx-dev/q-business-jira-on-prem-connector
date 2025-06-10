# 🚀 Terraform Deployment Guide

## 🔐 Secure Deployment (Recommended)

### Step 1: Configure Environment Variables
```bash
cd terraform
cp env.terraform.example .env.terraform
nano .env.terraform  # Add your sensitive credentials
```

### Step 2: Configure Non-Sensitive Settings
```bash
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars  # Update non-sensitive configuration
```

### Step 3: Deploy
```bash
source .env.terraform
./deploy.sh plan
./deploy.sh apply
```

## 📋 Traditional Deployment (Less Secure)

### Step 1: Configure All Variables in File
```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars  # Add ALL configuration including credentials
```

### Step 2: Deploy
```bash
terraform init
terraform plan
terraform apply
```

## 🔒 Security Comparison

| Aspect | Environment Variables | tfvars File |
|--------|----------------------|-------------|
| **Credential Storage** | ✅ Memory only | ❌ On disk |
| **Git Safety** | ✅ Auto-excluded | ⚠️ Must remember to exclude |
| **Audit Trail** | ✅ No credentials in logs | ❌ May appear in state/logs |
| **Team Sharing** | ✅ Template only | ❌ Must share credentials |
| **Best Practice** | ✅ Industry standard | ❌ Deprecated approach |

## 🛡️ Files Overview

- **`env.terraform.example`** - Template for sensitive environment variables
- **`terraform.tfvars.example`** - Template for non-sensitive configuration  
- **`.env.terraform`** - Your actual credentials (never committed)
- **`terraform.tfvars`** - Your actual non-sensitive config
- **`deploy.sh`** - Secure deployment script with validation

## ✅ Quick Start

```bash
# 1. Setup credentials
cp env.terraform.example .env.terraform
# Edit .env.terraform with your credentials

# 2. Setup configuration  
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your settings

# 3. Deploy securely
source .env.terraform && ./deploy.sh apply
``` 