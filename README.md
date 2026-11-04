# EC2 + Docker Compose deployment

This is a deployable reference project with a Next.js frontend, Python backend, and PostgreSQL database. Users can submit their name and favorite pet; entries are saved in PostgreSQL and displayed on the page. All application services run as Docker Compose containers on **one EC2 virtual machine**. Terraform provisions the host and its AWS networking; GitHub Actions deploys a source archive through private S3 and AWS Systems Manager (SSM). No SSH port is opened.

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

GitHub Actions --OIDC--> restricted AWS role
  |-- source archive -> private S3 bucket -> EC2
  `-- deployment command -> AWS Systems Manager -> EC2
```

Terraform also configures an EC2 instance role for SSM, artifact download, and reading the encrypted database password from Parameter Store. A static Elastic IP provides a stable DNS target. CloudWatch alarms cover EC2 CPU and instance status checks. HTTP is available initially; Caddy can issue and renew HTTPS certificates after a domain is configured.

## What this does and does not provide

- The `/api/submissions` API stores and lists name/favorite-pet entries. It creates its table automatically the first time entries are read or saved.
- The database is a PostgreSQL container on the same host, not RDS. Its Compose volume survives container restarts, but this single-VM design is **not highly available** and is not suitable for important data without tested off-host backups.
- A single EC2 host has no automatic horizontal scaling or failover. This is intentional for the requested EC2 + Compose deployment; ECS, EKS, and load balancers are not part of this design.
- App traffic is public on ports 80/443. Administration and deployments use SSM; do not add a public SSH rule.
- The database password is stored as an SSM SecureString by the deployment workflow. The Compose `.env` file on EC2 is mode `600` and must not be committed.
- CloudWatch alarms are visible in the AWS console; no notification destination is configured.

## Prerequisites

- An AWS account with permissions to create the Terraform resources in `infra/`.
- Terraform 1.6 or newer, AWS CLI v2, and Docker with the Compose v2 plugin for local use.
- A GitHub repository containing this project. The workflow deploys pushes to `main`.
- A GitHub Actions secret named `POSTGRES_PASSWORD`. Use a long random alphanumeric value; for example, generate one with `openssl rand -hex 32`.

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

Use the same owner and repository values for every Terraform command. Terraform creates a VPC, public subnet, internet gateway, security group, EC2 instance, SSM instance role, private artifact bucket, GitHub OIDC role, and CloudWatch alarms. The EC2 instance is an x86_64 `t3.medium` by default so there is memory for a Next.js container build. Change `instance_type` in a `terraform.tfvars` file if needed.

Save these outputs:

```sh
terraform output
```

Terraform creates an AWS GitHub OIDC provider. If your account already has that provider, import the existing provider into Terraform state or adapt the configuration to reuse it before applying.

### Configure GitHub Actions

In the repository's **Settings → Secrets and variables → Actions**, add:

**Secret**

- `POSTGRES_PASSWORD`: the random database password generated above.

**Repository variables**

- `AWS_ROLE_ARN`: Terraform output `github_actions_role_arn`.
- `AWS_REGION`: the region used for Terraform (default `ap-south-1`).
- `ARTIFACT_BUCKET`: Terraform output `artifact_bucket`.
- `EC2_INSTANCE_ID`: Terraform output `instance_id`.
- `APP_PASSWORD_PARAMETER_NAME`: Terraform output `app_password_parameter_name`.

The GitHub IAM trust policy is restricted to this repository's `main` branch. Pull requests run tests and Compose validation but do not deploy. A push to `main` packages the source, uploads it to the private bucket, stores the password as an SSM SecureString, then deploys through SSM. No long-lived AWS access key is needed.
Keep `POSTGRES_PASSWORD` stable after the first deployment; changing the SSM value alone does not change the password inside an already initialized PostgreSQL data volume.

Wait for the EC2 instance to finish its first-boot installation before the first deployment. Check **EC2 → Instances → Status checks** and **Systems Manager → Fleet Manager** if the workflow cannot reach the instance.

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
cd /opt/r2-assessment/releases/DEPLOYMENT_SHA
docker compose --project-name r2-assessment --env-file /opt/r2-assessment/.env ps
docker compose --project-name r2-assessment --env-file /opt/r2-assessment/.env logs --tail=100
```

The Compose project name is fixed so the PostgreSQL data volume remains stable across releases. Re-deploy the previous source revision through the same workflow if an application rollback is needed.

## Configure a domain and HTTPS

1. Create an `A` record for your domain pointing at Terraform's `public_ip` output. Allow DNS to propagate.
2. Connect to the instance using SSM and update `/opt/r2-assessment/.env`, replacing `SITE_ADDRESS=:80` with the domain name, for example `SITE_ADDRESS=app.example.com`.
3. From the active release directory, apply the Compose configuration:

   ```sh
   cd /opt/r2-assessment/releases/DEPLOYMENT_SHA
   docker compose --project-name r2-assessment --env-file /opt/r2-assessment/.env up -d
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
