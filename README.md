# 📞 Alcon AI: Production-Grade Telephony & Conversational Voice Agent System

An enterprise-grade, high-availability, highly scalable outbound and inbound AI voice agent platform designed for automated insurance renewals and service workflows. The system integrates **FastAPI**, **Redis distributed locking**, **PostgreSQL transactional persistence**, **Twilio Media Streams**, and **Twilio TaskRouter**, deployed on a highly secure **AWS EKS (Kubernetes)** cluster with git-driven **GitOps CI/CD** automation.

---

## 🔗 Portfolio Repositories Linkage

This project is split into two sister repositories to separate business application logic from cloud infrastructure engineering:
* **Application Codebase (This Repository)**: Contains the core conversational AI engines, telephony flow runtime, campaign managers, and real-time agent console.
  👉 **[Go to AI Voice Bot Application Repository](https://github.com/sanjanamahajan2001-sys/Alcon-AI-voice-agent)**
* **Infrastructure & Deployment Codebase**: Contains the Terraform IaC configurations, AWS EKS networking modules, Kubernetes/Helm deployment manifests, Docker containers, and Prometheus/Grafana/Loki monitoring dashboards.
  👉 **[Go to AI Voice Infrastructure Platform Repository](https://github.com/sanjanamahajan2001-sys/AI-Voice-Infrastructure-Platform)**

---

## 📖 Table of Contents
1. [Project Overview & Key Business Value](#1-project-overview--key-business-value)
2. [High-Level Architecture Diagrams](#2-high-level-architecture-diagrams)
3. [Production Tech Stack & Services](#3-production-tech-stack--services)
4. [Enterprise Core Features & Workflows](#4-enterprise-core-features--workflows)
5. [AWS EKS Infrastructure & Network Design](#5-aws-eks-infrastructure--network-design)
6. [Kubernetes (EKS) Orchestration & Scalability](#6-kubernetes-eks-orchestration--scalability)
7. [Security & Compliance Governance (IRDAI Standards)](#7-security--compliance-governance-irdai-standards)
8. [GitOps CI/CD Pipeline (GitHub Actions & ArgoCD)](#8-gitops-cicd-pipeline-github-actions--argocd)
9. [Local Development & Simulation Setup](#9-local-development--simulation-setup)
10. [Repository Deployment & Git Push Playbook](#10-repository-deployment--git-push-playbook)

---

## 1. Project Overview & Key Business Value

**Alcon AI** is a production-grade conversational engine designed to solve the critical business challenge of customer outreach and retention. While human agents face fatigue and high turnover rates, Alcon AI operates continuously, handling thousands of simultaneous calls, validating eligibility dynamically, classifying user intents in real-time, and executing seamless live-agent handovers.

### 🌟 Business Impact Metrics
* **100% Outreach Coverage**: Ensures every customer is contacted on critical lifecycle stages (T-30 to T+1 days).
* **80% Cost Reduction**: Automates initial qualifications, objection handling, and routine renewals.
* **Instant Human Handovers**: Less than 1.5 seconds latency when routing hot leads or frustrated customers to live advisors.
* **100% IRDAI Regulatory Adherence**: Enforces strict "Do Not Call" (DND/NCPR) registries, digital consent validation, and automated compliance auditing.

---

## 2. High-Level Architecture Diagrams

### A. End-to-End System & Runtime Data Flow
This diagram illustrates how a customer's voice stream is processed dynamically via Twilio webhooks, mapped to the deterministic runtime, and supported by cognitive AI and high-availability caching.

```mermaid
flowchart TD
    subgraph Customer [Customer Telephony]
        User([Customer Handset]) <-->|SIP/PSTN Trunk| Twilio[Twilio Voice Gateway]
    end

    subgraph VPC [AWS Cloud - VPC]
        ALB[Application Load Balancer] <-->|HTTPS / WebSockets| EKS[AWS EKS Pods - FastAPI Backend]
        
        subgraph Caching [High-Availability State]
            EKS <-->|Distributed Locks & Sessions| Redis[(ElastiCache Redis cluster)]
        end
        
        subgraph Storage [Persistent Storage]
            EKS <-->|Transactional Records & Audit| RDS[(Amazon RDS PostgreSQL)]
        end
        
        subgraph NLP [Cognitive AI Layer]
            EKS <-->|Speech Processing & Transcripts| LLM[LLM Client / Intent Engine]
            EKS <-->|FAQ KB Search| KB[FAQ Knowledge Base]
        end
    end

    subgraph Agent [Human Live-Agent Network]
        Twilio <-->|SIP Handoff via TaskRouter| AgentPhone([Agent VoIP Phone])
        EKS -.->|CTI Screen-Pop Websocket| AgentDash([React Live-Agent Dashboard])
    end

    %% Flow Paths
    Twilio <-->|HTTPS Webhook / Media Streams| ALB
```

### B. AWS EKS Deployment Architecture
A secure, multi-AZ networking setup isolating workload layers, database layers, and management gateways to guarantee maximum resilience and tight security, fully aligned with the active Terraform and Kubernetes deployment manifests.

```mermaid
graph TD
    Internet[Internet / Twilio API] -->|HTTPS Route53| ALB[AWS Application Load Balancer]
    
    subgraph VPC [AWS Multi-AZ VPC]
        subgraph PublicSubnet [Public Subnets]
            ALB
            NAT[NAT Gateways]
        end
        
        subgraph PrivateSubnet [Private Subnets - EKS Worker Nodes]
            subgraph EKSCluster [Amazon EKS Cluster]
                Nginx[Nginx Ingress Controller] --> BackendPods[FastAPI Backend Pods]
                Nginx --> FrontendPods[Next.js/React Dashboard Pods]
                BackendPods --> CeleryWorkers[Celery Background Workers]
                
                subgraph Observability [Observability Namespace]
                    Prom[Prometheus]
                    Graf[Grafana]
                    Loki[Loki Log Aggregator]
                end
            end
        end
        
        subgraph IsolatedSubnet [Isolated Data Subnets]
            RDS[(Amazon RDS PostgreSQL)]
            Redis[(Amazon ElastiCache Redis)]
            S3[(Amazon S3 - Audio Logs Vault)]
        end
    end
    
    ALB -->|TLS via Cert-Manager| Nginx
    BackendPods --> RDS
    BackendPods --> Redis
    BackendPods --> S3
    CeleryWorkers --> Redis
    BackendPods --> NAT --> ExternalLLM[External LLM / Twilio APIs]
```

### C. GitOps CI/CD Deployment Flow
Automating tests, linting, packaging, and deployments safely across environments with a single source of truth.

```mermaid
sequenceDiagram
    autonumber
    actor Developer
    participant Git as GitHub Repository
    participant GA as GitHub Actions
    participant ECR as AWS ECR Registry
    participant GitOps as GitOps Repo (Helm Charts)
    participant ArgoCD as ArgoCD (EKS Operator)
    participant EKS as AWS EKS Cluster

    Developer->>Git: git push feature/devops-eks
    Git->>GA: Trigger CI Pipeline
    GA->>GA: Run Linters & Unit Tests
    GA->>GA: Build Docker Image
    GA->>ECR: Push Image with SHA Tag
    GA->>GitOps: Update values.yaml image.tag
    GitOps->>ArgoCD: Trigger Auto-Sync Check
    ArgoCD->>EKS: Reconcile Drift & Apply Rolling Upgrade
    EKS->>EKS: Spin up new Pods, Terminate old Pods (Zero-Downtime)
```

---

## 3. Production Tech Stack & Services

### 💻 Application Tier
* **FastAPI**: Asynchronous web engine providing low-latency execution and automatic OpenAPI generation.
* **Uvicorn**: High-performance ASGI web server powering concurrent connections.
* **Celery + Redis**: Distributed asynchronous task execution engine for running mass campaigns and background retry schedules.
* **Vite + React (Frontend)**: Highly responsive dashboard with real-time analytics and CTI screen-pops powered by WebSockets.

### 💾 Caching & Database Tier
* **PostgreSQL (RDS)**: Relational engine managing structural transactions, user profile lists, campaign executions, and IRDAI compliance vaults.
* **Redis (ElastiCache)**: Dedicated sub-millisecond cache coordinating session state persistence, rate-limiting, and distributed locking.

### 📞 Telephony & Communication Tier
* **Twilio Voice & Media Streams**: Two-way real-time audio streaming from PSTN/SIP directly into application webhooks.
* **Twilio TaskRouter**: Skill-based, stateful routing engine ensuring perfect distribution of agent transfer events.
* **Twilio Programmable SMS / WhatsApp Business API**: Automatic multi-channel fallbacks when voice retry budgets are depleted.

### ☁️ Infrastructure & DevOps Tier
* **AWS Elastic Kubernetes Service (EKS)**: Managed Kubernetes cluster managing high-availability pod workloads.
* **Terraform / Helm**: Infrastructure as Code (IaC) and Kubernetes packaging utilities.
* **AWS ALB Ingress Controller**: Dynamic application load balancing for secure routing.
* **AWS Route53 / ACM**: High-availability DNS management and automated TLS certificate handling.
* **ArgoCD**: GitOps declarative continuous deployment controller.

---

## 4. Enterprise Core Features & Workflows

### 📅 A. Campaign Schedule Engine
Automates contact patterns based on the policy expiration lifecycle, ensuring continuous customer coverage.
* **Stage Timeline**:
  * **T-30 (Awareness)**: Generates initial policy status and triggers soft reminders.
  * **T-15 (Follow-up)**: Delivers explicit quote options.
  * **T-7 (Urgency)**: Focuses on potential No-Claim Bonus (NCB) loss.
  * **T-1 (Final Push)**: Final day check for instant payment.
  * **T+1 (Recovery)**: Identifies break-in grace-period policies.
* **Compliance Checks**:
  * **Quiet Hours Enforcement**: Restricts all campaign activities to the standard hours of 9:00 AM to 8:00 PM local time.
  * **Real-time API Validation**: Executes a check against the Dealer Management System (DMS) to confirm the policy hasn't been renewed manually before triggering the call.

### 🔁 B. Retry & Reachability Engine
Ensures robust outreach across diverse network scenarios using custom retry delays.
* **Failure Handling**: Handles network outcomes including `BUSY`, `NO_ANSWER`, or `TEMPORARILY_UNREACHABLE` dynamically.
* **Exponential Backoff**: Coordinates retries progressively (e.g., 5 min $\rightarrow$ 30 min $\rightarrow$ 2 hours).
* **Multi-Channel Fallback**: Automatically sends an interactive payment link or digital callback form via **WhatsApp / SMS** when a customer is unreachable on voice after maximum retries.

### 🔒 C. Call Safety & Distributed Idempotency Layer
Prevents parallel execution and double-dialing errors inside replicated worker environments.
* **Redis `SETNX` Lock**: Executes a lock using `lock:call:{customer_phone}` before initiating a call request.
* **Atomic Lead Toggling**: Coordinates transaction statuses atomically to avoid race conditions across celery worker pools.

### 🗣️ D. Conversational AI & Intent Engine
Processes complex natural spoken responses, including regional linguistic mixtures.
* **Hinglish/Regional Understanding**: Handles natural code-mixed statements (e.g., *"Abhi busy hoon, kal call back karo"* is parsed into a `CALLBACK` intent).
* **Objection Handling**: Detects objections ("Too expensive", "Competitor offering better quote") and dynamically triggers benefits (OEM parts support, cashless claims, paperless onboarding).
* **Sentiment Escalation**: Scores customer emotions dynamically; scores $> 0.8$ (indicating frustration) instantly skip standard prompts and route directly to a human agent.

### 🔄 E. Hybrid Switchover & CTI Integration
Links automated artificial intelligence seamlessly to standard contact center human agents.
* **Skill-Based Routing**: Twilio TaskRouter evaluates agent skills (e.g., *Motor Insurance Expert*) to assign calls.
* **Presence Checking**: The AI confirms an agent is active and "Online" via WebSockets before offering a live transfer.
* **CTI Screen-Pop**: Automatically displays the complete visual conversation history and extracted intent entities on the manager's console the moment their handset rings.

### 🛡️ F. IRDAI Quality & Compliance Engine
Provides comprehensive verification mechanisms for regulated insurance environments.
* **Digital Consent**: Prompts explicit consent prior to renewals and logs the transaction.
* **PII Masking**: Redacts credit cards, vehicle registration keys, and policy numbers from storage.
* **Immutable Compliance Auditing**: Encapsulates audit data (DND respect, non-misrepresentation, consent status) in an immutable PostgreSQL database vault.

---

## 5. AWS EKS Infrastructure & Network Design

To host Alcon AI in a production environment, we implement a highly secure, multi-tier AWS network topology.

### 🌐 Networking Specifications
* **VPC CIDR**: `10.100.0.0/16` divided across three Availability Zones (Multi-AZ).
* **Public Subnets**: `10.100.1.0/24`, `10.100.2.0/24` (Hosts ALB, NAT Gateways, Bastion Hosts).
* **Private Subnets**: `10.100.10.0/24`, `10.100.20.0/24` (Hosts AWS EKS Worker nodes and Celery workers).
* **Isolated Subnets**: `10.100.50.0/24`, `10.100.60.0/24` (Hosts RDS PostgreSQL and ElastiCache Redis).

### 🚀 Traffic Control & Firewall Rules
1. **AWS ALB Ingress**: Only accepts inbound traffic on port `443` (TLS 1.3) from Twilio's IP range.
2. **EKS Pod Security Groups**:
   * API Pods only accept traffic from the ALB.
   * PostgreSQL only accepts TCP port `5432` from the EKS Private Node Security Group.
   * Redis only accepts TCP port `6379` from the EKS Private Node Security Group.
3. **Outbound Internet**: EKS Worker Nodes communicate with external LLM APIs and Twilio gateways through NAT Gateways in the Public Subnets.

---

## 6. Kubernetes (EKS) Orchestration & Scalability

Deploying Alcon AI inside Kubernetes enables elastic scaling, automated healing, and resource isolation.

### 📦 Namespaces Isolation
* `alcon-core`: FastAPI backend, React dashboard frontend, and Celery workers.
* `alcon-infra`: ArgoCD, External Secrets Operator, and Ingress Controller.
* `alcon-monitoring`: Prometheus and Grafana.

### 📈 Elastic Auto-Scaling Strategy
1. **Horizontal Pod Autoscaler (HPA)**:
   * Dynamically scales the FastAPI backend replica counts from 3 up to 50 based on target CPU utilization ($>70\%$) and active concurrent Webhook request pools.
2. **Cluster Scaling with Karpenter**:
   * Integrated into the AWS EKS control plane to analyze unscheduled pod states. Karpenter provisions high-performance `c6i.xlarge` or `m6i.large` EC2 spot/on-demand instances in seconds, matching telephony workload spikes.

### ☸️ Kubernetes Deployment Configuration (`deployment.yaml`)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: alcon-backend
  namespace: alcon-core
  labels:
    app: alcon-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: alcon-backend
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: alcon-backend
    spec:
      containers:
      - name: fastapi-app
        image: <aws_account_id>.dkr.ecr.us-east-1.amazonaws.com/alcon-backend:latest
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 8000
        resources:
          limits:
            cpu: "2"
            memory: 2Gi
          requests:
            cpu: "500m"
            memory: 512Mi
        envFrom:
        - secretRef:
            name: alcon-db-secrets
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8000
          initialDelaySeconds: 15
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

---

## 7. Security & Compliance Governance (IRDAI Standards)

Ensuring compliance with insurance industry regulations (such as IRDAI) is highly prioritized throughout our infrastructure.

### 🔐 1. Identity & Access Control
* **IAM Roles for Service Accounts (IRSA)**: EKS Pods are mapped directly to AWS IAM roles using OpenID Connect (OIDC). Pods authenticate directly with AWS KMS, RDS, and Secrets Manager without storing hardcoded static API credentials in the environment.

### 🔑 2. Secrets Management
* **AWS Secrets Manager & Sealed Secrets**: Credentials, Twilio Auth Tokens, and database passwords are encrypted at rest using AWS KMS. The **External Secrets Operator (ESO)** in EKS pulls secrets dynamically into memory as standard Kubernetes secret resources.

### 🛡️ 3. Traffic Encryption
* **In-Transit**: ALB terminates SSL using automated ACM certificates. All intra-cluster microservice communications are enforced via MTLS.
* **At-Rest**: Amazon RDS instances, Elasticache Redis nodes, and EBS persistent volumes are encrypted via customer-managed KMS keys.

### 👁️ 4. PII Redaction & Logs Scrubbing
* Transcripts are passed through a regex-based PII scrubber before reaching persistent databases:
```python
import re

def mask_pii_data(transcript: str) -> str:
    # Redact Credit Cards
    transcript = re.sub(r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b', '[REDACTED_CARD]', transcript)
    # Redact Indian Mobile Numbers
    transcript = re.sub(r'\b(?:\+91|0)?[6-9]\d{9}\b', '[REDACTED_PHONE]', transcript)
    # Redact Policy Numbers / IDs
    transcript = re.sub(r'\bPOL[a-zA-Z0-9]{5,10}\b', '[REDACTED_POLICY]', transcript)
    return transcript
```

---

## 8. GitOps CI/CD Pipeline (GitHub Actions & ArgoCD)

Our continuous delivery pipeline automates quality gates and synchronizes production configurations.

### ⚙️ 1. GitHub Actions Workflow
The CI pipeline runs automated checks and builds target images on every branch push:
* **Linter Checking**: Formats code via `black` and verifies typing imports via `mypy`.
* **Testing Stage**: Runs unit suites (`pytest`) and API regression mocks.
* **Docker Packaging**: Builds lightweight multi-stage Docker images to keep surface sizes small.
* **ECR Publishing**: Authenticates and pushes images tagged with the commit SHA:
```bash
docker build -t alcon-backend:v1.0.0 .
docker tag alcon-backend:v1.0.0 <aws_account_id>.dkr.ecr.us-east-1.amazonaws.com/alcon-backend:v1.0.0
docker push <aws_account_id>.dkr.ecr.us-east-1.amazonaws.com/alcon-backend:v1.0.0
```

### 🛰️ 2. ArgoCD Continuous Deployment
* **Declarative Configuration**: All Kubernetes manifests, Helm charts, and environment files are version-controlled in our GitOps repository.
* **Sync Policies**: ArgoCD continuously compares EKS's active cluster state with the GitOps repository. It identifies drifts and applies upgrades without downtime.

---

## 9. Local Development & Simulation Setup

You can replicate the multi-tier production environment locally using **Docker Compose** to run FastAPI, PostgreSQL, and Redis.

### 📦 1. Prerequisite Installations
* Install **Docker** and **Docker Compose**.
* Install **Python 3.10+** (if running services directly outside containers).

### 🛠️ 2. Environmental Setup
Clone this repository and create a `.env` file in the `backend/` directory:
```env
DATABASE_URL=postgresql://alcon_user:secure_pwd@postgres_db:5432/alcon_prod
REDIS_URL=redis://redis_cache:6379/0
TWILIO_ACCOUNT_SID=ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
TWILIO_AUTH_TOKEN=your_auth_token_here
LLM_API_KEY=your_llm_api_key
```

### 🚀 3. Run the Multi-Container Environment
From the root directory, launch all core systems:
```bash
docker-compose up --build
```
This command starts:
1. **postgres_db**: Initialized database with active tables on port `5432`.
2. **redis_cache**: Memory storage on port `6379`.
3. **fastapi_backend**: API engine exposed on port `8000`.
4. **frontend_dashboard**: Development client UI on port `5173`.
5. **celery_worker**: Parallel scheduler for out-of-band campaign flows.

### 🧪 4. Execute Verification Tests
To run integrated local verification flows:
```bash
docker-compose exec fastapi_backend pytest tests/
```

---

## 10. Repository Deployment & Git Push Playbook

Follow these commands to deploy this complete, production-grade codebase to your GitHub portfolio.

### 📂 Recommended Repository Specifications
* **GitHub Repository Name**: `alcon-ai-voice-agent-orchestrator`
* **Repository Description**: `Production-grade enterprise Conversational AI Voice Agent system deployed on AWS EKS with Twilio integration, Redis session caching, PostgreSQL persistence, and GitOps-driven high-availability DevOps architecture.`

### 🚀 Actionable Git Commands
Navigate to the root directory on your terminal and run the following commands to push the project:

```bash
# 1. Initialize local repository (if not already done)
git init

# 2. Add all project files, including this comprehensive DevOps README
git add .

# 3. Commit your codebase with a descriptive DevOps-focused message
git commit -m "feat(devops): implement production-grade EKS architecture docs, Helm charts & CI/CD workflow"

# 4. Rename the default branch to 'main'
git branch -M main

# 5. Link your local repository to your remote GitHub portfolio
# Replace the URL below with your actual GitHub repository URL
git remote add origin git@github.com:sanjanamahajan2001-sys/alcon-ai-voice-agent-orchestrator.git

# 6. Push the code to the main branch
git push -u origin main
```

*(Note: If you are using SSH key structures or custom aliases, ensure your remote origin is configured accordingly, for example: `git remote add origin git@github-sys:sanjanamahajan2001-sys/Alcon-AI-voice-agent.git` depending on your Git SSH Config settings)*.
