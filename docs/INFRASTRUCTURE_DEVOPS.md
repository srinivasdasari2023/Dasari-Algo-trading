# Infrastructure & DevOps – CapitalGuard Algo Trader

**Terraform | CI/CD | Environments | Secrets | Cost Guardrails**

---

## 1. Terraform Structure

```
infra/
├── terraform/
│   ├── environments/
│   │   ├── dev/
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   └── terraform.tfvars
│   │   ├── staging/
│   │   │   └── ...
│   │   └── prod/
│   │       └── ...
│   ├── modules/
│   │   ├── network/       # VPC, subnets, security groups
│   │   ├── compute/       # ECS/EKS or VM (per choice)
│   │   ├── database/      # RDS PostgreSQL
│   │   ├── cache/         # ElastiCache Redis
│   │   ├── secrets/       # Secrets Manager / Vault refs
│   │   └── monitoring/    # Log group, alarms, optional dashboard
│   ├── backend.tf        # S3 + DynamoDB for state
│   └── versions.tf       # provider constraints
├── docker/
│   ├── Dockerfile.api
│   ├── Dockerfile.market
│   ├── Dockerfile.signal
│   ├── Dockerfile.risk
│   └── Dockerfile.order
└── scripts/
    └── backup_db.sh
```

- **State**: Remote state in S3 with DynamoDB lock; separate state per environment.
- **Modules**: Parameterized (env, instance sizes, retention); no hardcoded credentials.

---

## 2. CI/CD Pipelines

### 2.1 Build & Test (on every PR and push to main)

- **Backend (Python)**  
  - Checkout → Install deps (poetry/pip) → Lint (ruff/black) → Unit tests (pytest) → Build Docker images (tag with short SHA).  
  - No deploy on PR; deploy on merge to main (or to release branch).

- **Web (Next.js)**  
  - Install → Lint → Type check → Unit/component tests → Build.  
  - Optional: E2E in pipeline or scheduled.

- **Mobile (React Native)**  
  - Install → Lint → Type check → Build (Android/iOS).  
  - Optional: Detox/E2E in nightly or release branch.

### 2.2 Deploy

- **Dev**: Auto-deploy on merge to `develop` (or main with path filter).  
- **Staging**: Deploy on merge to `release/*` or manual approval.  
- **Prod**: Manual approval or tag-based (`v*`); optional blue-green or canary.

### 2.3 Pipeline Files (skeleton)

- `.github/workflows/backend.yml` – backend test + Docker build.  
- `.github/workflows/web.yml` – web test + build.  
- `.github/workflows/mobile.yml` – mobile build (and test if present).  
- `.github/workflows/deploy-dev.yml` – deploy to dev.  
- `.github/workflows/deploy-staging.yml` – deploy to staging (with approval).  
- `.github/workflows/deploy-prod.yml` – deploy to prod (with approval/tag).

---

## 3. Environment Isolation

| Env    | Purpose              | Data                    | Broker              |
|--------|----------------------|-------------------------|---------------------|
| Local  | Dev on laptop        | Mock/sample or dev DB   | Sandbox/mock        |
| Dev    | Integration, QA      | Synthetic / copy subset | Upstox sandbox      |
| Staging| Pre-prod, UAT        | Anonymized or copy      | Upstox sandbox      |
| Prod   | Live trading         | Real                    | Upstox production   |

- Separate Terraform workspaces or directories per env; separate DB and Redis per env.  
- No prod secrets in dev/staging; use different Upstox app credentials per env.

---

## 4. Secrets & Backups

- **Secrets**: No hardcoded credentials. Use env vars or a vault (e.g. AWS Secrets Manager, HashiCorp Vault). Terraform references secret ARNs/paths; applications read at runtime. Rotate broker tokens and DB credentials per policy.  
- **Backups**:  
  - **PostgreSQL**: Automated daily backups; retention per env (e.g. 7 days dev, 30 days prod). Point-in-time recovery where required.  
  - **Redis**: Optional RDB snapshots for state recovery; treat Redis as cache/session—reconstruct from DB where possible.  
- **Audit logs**: Retained per compliance; stored in durable storage (e.g. S3) and optionally in DB.

---

## 5. Cost Guardrails

- **Resource sizing**: Right-size RDS and Redis for dev/staging; prod sized for market-hours load.  
- **Alerts**: Billing alerts at 50%, 80%, 100% of monthly budget; optional auto-stop non-prod outside market hours.  
- **Review**: Quarterly review of Terraform and running resources; remove unused volumes and snapshots.

---

*Document owner: Cloud & DevOps Architect.*
