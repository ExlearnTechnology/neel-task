# EC2 + Docker Compose deployment

This is a deployable reference project with a Next.js frontend, Python backend, and PostgreSQL database. Users can submit their name and favorite pet; entries are saved in PostgreSQL and displayed on the page. All application services run as Docker Compose containers on **one EC2 virtual machine**. GitHub Actions pushes application images to Amazon ECR and uses AWS Systems Manager (SSM) to deploy them to EC2. No SSH port is opened.

## Architecture

```text
Browser
  | HTTP/HTTPS
  v
EC2 (Amazon Linux 2023; public subnet; ports 80/443 only)
  Caddy container
    |-- /       -> Next.js container
    |-- /api/*  -> FastAPI container -> PostgreSQL container
                                    PostgreSQL data -> encrypted EBS-backed Docker volume

GitHub Actions --IAM access key secrets--> restricted AWS identity
  |-- build and push API/frontend images -> Amazon ECR
  `-- deployment command -> AWS Systems Manager -> EC2 pulls images from ECR
```

Terraform also configures an EC2 instance role for SSM and access to deployment resources. A static Elastic IP provides a stable DNS target. CloudWatch alarms cover EC2 CPU and instance status checks. HTTP is available initially; Caddy can issue and renew HTTPS certificates after a domain is configured.

## What this does and does not provide

- The `/api/submissions` API stores and lists name/favorite-pet entries. It creates its table automatically the first time entries are read or saved.
- The database is a PostgreSQL container on the same host, not RDS. Its Compose volume survives container restarts, but this single-VM design is **not highly available** and is not suitable for important data without tested off-host backups.
- A single EC2 host has no automatic horizontal scaling or failover. This is intentional for the requested EC2 + Compose deployment; ECS, EKS, and load balancers are not part of this design.
- App traffic is public on ports 80/443. Administration and deployments use SSM; do not add a public SSH rule.
- The Compose `.env` file on EC2 holds the database password, is mode `600`, and must not be committed. The deployment workflow refreshes it from Parameter Store.
- CloudWatch alarms are visible in the AWS console; no notification destination is configured.

## Deploy to a manually created EC2 instance

The GitHub Actions workflow builds the API and frontend Docker images, pushes them to ECR, then uses SSM to make EC2 pull and run them. It defaults to region `ap-south-1`; set `EC2_INSTANCE_ID` to `i-03ddcc7c09466e1e2`. It uses `/opt/r2-assessment` with Compose project name `r2-assessment`. The EC2 instance must already be SSM-managed and have Docker Compose, AWS CLI, an instance profile with ECR pull access and permission to read the database password SecureString from Parameter Store. The workflow writes the parameter value to `/opt/r2-assessment/.env` with restrictive permissions. Keep the Parameter Store value unchanged for an initialized PostgreSQL data volume.

Create one private ECR repository (for example, `neel-task`) in `ap-south-1`. Create a dedicated IAM user for GitHub Actions (without console access) and grant only ECR authentication/image-push permissions for this repository and SSM `SendCommand` to the EC2 instance using `AWS-RunShellScript`, plus `ssm:GetCommandInvocation`. Create an access key for this user and store both key values as GitHub Actions secrets. Long-lived IAM user keys are less secure than OIDC: rotate them regularly, never commit them, and revoke them immediately if exposed.

In the repository's **Settings → Secrets and variables → Actions → Secrets**, add:

- `AWS_ACCESS_KEY_ID`: access key ID for the dedicated IAM user.
- `AWS_SECRET_ACCESS_KEY`: secret access key for the dedicated IAM user.

Under **Variables**, add:

- `ECR_REPOSITORY`: the ECR repository name (for example, `neel-task`).
- `EC2_INSTANCE_ID`: `i-03ddcc7c09466e1e2`.
- `APP_PASSWORD_PARAMETER_NAME`: the full SSM Parameter Store name for the database `SecureString` (for example, `/neel-task/prod/db-password`).
- `AWS_REGION`: `ap-south-1` (optional; this is the workflow default).

The EC2 instance profile needs ECR pull permissions (for example, `AmazonEC2ContainerRegistryReadOnly`), SSM managed-instance permissions, and `ssm:GetParameter` plus any required `kms:Decrypt` permission for the password parameter. The workflow updates `/opt/r2-assessment/compose.yaml` and `Caddyfile`, retrieves the password from Parameter Store, and keeps the Compose project name so the existing database volume is reused. If your running Compose project or directory differs, update the deployment paths/project name in `.github/workflows/deploy.yml` before deploying.

Push or merge a commit to `main` to deploy. This workflow does not run on pull requests.

## Prerequisites

- An AWS account with permissions to create the Terraform resources in `infra/`.
- Terraform 1.6 or newer, AWS CLI v2, and Docker with the Compose v2 plugin for local use.
- A GitHub repository containing this project. The workflow deploys pushes to `main`.

## Provision EC2 and AWS resources

From the repository root:

```sh
cd infra
terraform init
terraform fmt -check
terraform validate
terraform plan -var="github_owner=YOUR_GITHUB_OWNER" -var="github_repo=YOUR_REPOSITORY"
terraform apply -var="github_owner=YOUR_GITHUB_OWNER" -var="github_repo=YOUR_REPOSITORY"
```

Use the same owner and repository values for every Terraform command. Terraform creates a VPC, public subnet, internet gateway, security group, EC2 instance, SSM instance role, private artifact bucket, GitHub OIDC role, and CloudWatch alarms. The EC2 instance is an x86_64 `t3.medium` by default so there is memory for a Next.js container build. Change `instance_type` in a `terraform.tfvars` file if needed. The Terraform-created GitHub role needs an ECR push policy, and the EC2 role needs ECR pull access, before they can be used by this workflow.

Save these outputs:

```sh
terraform output
```

Terraform creates an AWS GitHub OIDC provider. If your account already has that provider, import the existing provider into Terraform state or adapt the configuration to reuse it before applying.

The deployment workflow uses the GitHub Actions IAM user credentials to push images and send the SSM deployment command. The EC2 instance needs ECR pull permissions. See [Deploy to a manually created EC2 instance](#deploy-to-a-manually-created-ec2-instance) for the GitHub secrets, variables, and requirements.

## Deploy and verify

Push a tested commit to `main`. GitHub Actions waits for SSM's deployment command and fails the job if the command fails. Open the `application_url` Terraform output, then verify the API and database:

```sh
curl http://EC2_PUBLIC_IP/api/health
```

Expected response:

```json
{"status":"ok","database":"connected"}
```

For host-side troubleshooting, use **Systems Manager → Run Command** with `AWS-RunShellScript`, or start an SSM session and run:

```sh
cd /opt/r2-assessment
docker compose --project-name r2-assessment --env-file .env --env-file deploy.env ps
docker compose --project-name r2-assessment --env-file .env --env-file deploy.env logs --tail=100
```

The Compose project name is fixed so the PostgreSQL data volume remains stable across deployments. Re-deploy the previous source revision through the same workflow if an application rollback is needed.

## Configure a domain and HTTPS

1. Create an `A` record for your domain pointing at Terraform's `public_ip` output. Allow DNS to propagate.
2. Connect to the instance using SSM and update `/opt/r2-assessment/.env`, replacing `SITE_ADDRESS=:80` with the domain name, for example `SITE_ADDRESS=app.example.com`.
3. From the application directory, apply the Compose configuration:

   ```sh
   cd /opt/r2-assessment
   docker compose --project-name r2-assessment --env-file .env --env-file deploy.env up -d
   ```

Caddy will obtain and renew the certificate automatically. Keep ports 80 and 443 reachable from the internet for certificate issuance and renewal. The deployment workflow preserves `SITE_ADDRESS` while refreshing the SSM-backed password value; do not change that value without also rotating the password in PostgreSQL.

## Local run

Copy `.env.example` to `.env`, replace the sample password, then run from the project root:

```powershell
Copy-Item .env.example .env
```

```sh
cp .env.example .env
docker compose up --build -d
docker compose ps
```

Open `http://localhost` to submit and view entries. The API is also available at `http://localhost/api/submissions`; database health is at `http://localhost/api/health`. Stop the services with `docker compose down`; the named database volume is retained. To delete local database data as well, use `docker compose down --volumes`.

## Infrastructure lifecycle and cost

Review the Terraform plan before applying changes. Back up PostgreSQL before destroying the instance: its data volume is deleted with the EC2 instance. Remove the out-of-band SSM password before destroying the AWS resources:

```sh
aws ssm delete-parameter --name "$(terraform -chdir=infra output -raw app_password_parameter_name)"
terraform -chdir=infra destroy -var="github_owner=YOUR_GITHUB_OWNER" -var="github_repo=YOUR_REPOSITORY"
```

The artifact bucket is dedicated to deployment archives and is emptied by Terraform during destroy. The EC2 instance, EBS volume, Elastic IP, detailed monitoring, S3 storage, and CloudWatch alarms incur AWS charges while provisioned.
