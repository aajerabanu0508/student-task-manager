# Student Task Manager — Docker + GitHub Actions + AWS EC2

A beginner-friendly deployment project. The Flask app stores tasks in SQLite. Docker packages it, GitHub Actions runs tests, and successful pushes to `main` trigger deployment to an Ubuntu EC2 instance.

## Architecture

```text
Developer laptop
    |
    | git push origin main
    v
GitHub repository
    |
    v
GitHub Actions: install dependencies -> unit tests
    |
    | tests pass: SSH to EC2
    v
Ubuntu EC2: git pull -> docker compose build/recreate
    |
    v
Browser -> http://EC2_PUBLIC_IP/
```

This beginner version builds the Docker image on EC2. A later improvement is to build once in CI, push to a container registry, and deploy that immutable image.

## Repository structure

```text
student-task-manager/
├── app.py
├── requirements.txt
├── Dockerfile
├── compose.yaml
├── .dockerignore
├── .gitignore
├── templates/
│   └── index.html
├── tests/
│   └── test_app.py
└── .github/
    └── workflows/
        └── deploy.yml
```

## 1. Run locally

Requirements: Python 3.12+, Git, and Docker Desktop (if testing with Docker).

### Run with Python

Linux/macOS:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Windows PowerShell:
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`. Test health at `http://127.0.0.1:5000/health`.

### Run unit tests

```bash
python -m unittest discover -s tests -v
```

### Run with Docker Compose

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f web
```

Open `http://localhost/`. Stop the container without deleting task data:
```bash
docker compose down
```

The named volume `task_data` keeps SQLite data when the container is replaced. Do not run the Python and Docker versions against the same database path at the same time. On EC2, the first-deployment commands create a local `.env` file with a random `SECRET_KEY`; it is excluded from Git and should not be committed.

## 2. Create the GitHub repository

1. Create a repository named `student-task-manager` on GitHub.
2. For this beginner setup, make it **public** so EC2 can clone it without a deploy key. Never commit secrets or private keys.
3. In the project directory, run:

```bash
git init
git add .
git commit -m "Initial Student Task Manager application"
git branch -M main
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/student-task-manager.git
git push -u origin main
```

Replace `YOUR_GITHUB_USERNAME` with your GitHub username. If Git says the remote already exists, inspect it with `git remote -v` instead of adding it again.

## 3. Create or prepare an AWS EC2 instance

Use an Ubuntu Server LTS AMI. For a learning project, a small instance such as `t3.micro` may work, subject to account eligibility, region, and application load. Check AWS pricing before starting it.

### Security group inbound rules

| Type | Port | Source | Purpose |
|---|---:|---|---|
| SSH | 22 | Your current public IP `/32` | Administration and GitHub Actions SSH |
| HTTP | 80 | `0.0.0.0/0` | Public web app |

Restrict SSH to your IP where possible. GitHub-hosted runner IPs change, so this simple workflow requires SSH from the GitHub runner to be allowed by the instance's network rules. Do **not** solve this by exposing SSH to everyone permanently. For a more secure production setup, use a self-hosted runner with tight controls or AWS Systems Manager and remove public SSH access.

### Connect from your computer

Use the correct private key and username for your instance. For Ubuntu AMIs the username is usually `ubuntu`.

```bash
ssh -i /path/to/your-key.pem ubuntu@YOUR_EC2_PUBLIC_IP
```

If you use WSL and the PEM file is under `/mnt/c`, copy it into the Linux filesystem and restrict permissions:

```bash
mkdir -p ~/.ssh
cp /mnt/c/Users/YOUR_WINDOWS_USER/Downloads/your-key.pem ~/.ssh/ec2.pem
chmod 600 ~/.ssh/ec2.pem
ssh -i ~/.ssh/ec2.pem ubuntu@YOUR_EC2_PUBLIC_IP
```

Replace all example paths and the IP. Never upload the EC2 `.pem` file to GitHub.

## 4. Install Docker and Git on EC2

Run these commands **inside the EC2 SSH session**:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
```

Add Docker's official apt repository:

```bash
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

Install Docker Engine and Compose plugin:

```bash
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo docker --version
sudo docker compose version
```

Allow the `ubuntu` user to run Docker without `sudo`:

```bash
sudo usermod -aG docker "$USER"
```

Then **disconnect and reconnect** for the group membership to take effect. Verify:

```bash
docker ps
```

Note: membership in the `docker` group effectively grants root-level privileges. Only add trusted users.

## 5. Clone the project onto EC2

Run on EC2, replacing the repository URL:

```bash
sudo mkdir -p /opt/student-task-manager
sudo chown "$USER":"$USER" /opt/student-task-manager
git clone https://github.com/YOUR_GITHUB_USERNAME/student-task-manager.git /opt/student-task-manager
cd /opt/student-task-manager
# Create a strong app secret once; this local .env file is not committed to Git.
if [ ! -f .env ]; then printf 'SECRET_KEY=%s\n' "$(openssl rand -hex 32)" > .env; chmod 600 .env; fi
docker compose up -d --build
docker compose ps
```

If the directory already contains a Git repository, use `git -C /opt/student-task-manager pull --ff-only origin main` rather than cloning again.

Test from EC2:
```bash
curl -fsS http://127.0.0.1/health
```

Expected response:
```json
{"status":"ok"}
```

Open `http://YOUR_EC2_PUBLIC_IP/` in your browser. The security group must allow inbound TCP/80.

## 6. Configure GitHub Actions secrets

In your GitHub repository, open **Settings → Secrets and variables → Actions → New repository secret**.

Create these three secrets:

| Secret name | Value |
|---|---|
| `EC2_HOST` | EC2 public IPv4 address or DNS name |
| `EC2_USER` | `ubuntu` for standard Ubuntu AMIs |
| `EC2_SSH_KEY` | Full contents of a private key that is authorized to log in as `EC2_USER` |

### Recommended SSH key approach

For this beginner lab, you can use the private key that already connects to the instance. A better long-term approach is a separate deployment key with limited scope and a planned rotation. Never paste a private key into chat, commit it, or print it in CI logs.

On your **local computer**, display the private key only in your own terminal and copy its entire content into the GitHub secret:

```bash
cat ~/.ssh/ec2.pem
```

The secret should retain the complete multi-line key, including its `BEGIN ... PRIVATE KEY` and `END ... PRIVATE KEY` lines. Do not Base64-encode it for this workflow. The workflow writes the secret directly to a file and validates it with `ssh-keygen`; this avoids the common malformed-key / `libcrypto` error caused by mixing raw and Base64 key formats.

The matching public key must be present in the EC2 user's `~/.ssh/authorized_keys`. If the existing key successfully logs you in, this is already configured.

### Host key note

The workflow uses `ssh-keyscan` to learn the host key on first connection for simplicity. For production, verify the host-key fingerprint independently and pin it rather than trusting an unverified first connection.

## 7. Understand the GitHub Actions workflow

File: `.github/workflows/deploy.yml`

1. A push to `main` starts the workflow.
2. GitHub Actions checks out the repository.
3. It installs Python dependencies and runs unit tests.
4. Deployment waits for tests to pass.
5. The runner connects to EC2 over SSH.
6. EC2 pulls the latest `main` commit.
7. Docker Compose rebuilds the image and replaces the running container.
8. The named volume preserves the SQLite database across container replacements.

The workflow deploys only from `main`. `workflow_dispatch` also allows a manual run from the Actions tab.

## 8. Make a change and verify automatic deployment

Edit the page text in `templates/index.html`, then:

```bash
git add .
git commit -m "Update task manager page"
git push origin main
```

Go to the repository's **Actions** tab and inspect the workflow run. After it succeeds, refresh the EC2 website. If tests fail, the deploy job is skipped.

## 9. Troubleshooting

### Workflow fails with `Permission denied (publickey)`

- Check `EC2_HOST`, `EC2_USER`, and the private key secret.
- Confirm the public key corresponding to that private key is in the EC2 user's `~/.ssh/authorized_keys`.
- Confirm inbound TCP/22 permits the runner's source. GitHub-hosted runner addresses change; use a secure, controlled runner or Systems Manager for production.
- Do not switch between raw and Base64 key handling. This workflow expects a raw, multiline private key.

### Workflow fails with `ssh-keygen ... invalid format` or `libcrypto`

- The secret may be truncated, copied incompletely, or stored in the wrong format.
- Re-copy the full original private key, including header/footer, into `EC2_SSH_KEY`.
- Validate locally with `ssh-keygen -y -f ~/.ssh/ec2.pem`.
- Do not print the secret in workflow logs.

### Docker command says permission denied

Reconnect after adding the user to the `docker` group, or use `sudo docker ...` as a temporary diagnostic.

### Website is unreachable

On EC2:
```bash
docker compose ps
docker compose logs --tail=100 web
curl -v http://127.0.0.1/health
sudo ss -lntp | grep ':80'
```

Then check that the EC2 security group permits inbound TCP/80 and that you are using the current public IP.

### Deployment says `git pull` cannot fast-forward

Avoid editing files directly on EC2. Make changes locally and push them to GitHub. Investigate local changes on EC2 before discarding anything; do not blindly run `git reset --hard`.

### Tasks disappeared

The SQLite database should persist in the named Docker volume. Check it with:
```bash
docker volume ls
docker inspect student-task-manager
```
Do not run `docker compose down -v`, because `-v` deletes named volumes and their stored data.

## 10. Production improvements

This is a learning project, not a hardened production architecture. Before real users or sensitive data:

- Terminate HTTPS with a reverse proxy or load balancer and use a valid certificate.
- Use AWS Systems Manager Session Manager or a controlled deployment runner instead of broad SSH ingress.
- Use a production database service such as Amazon RDS if the app needs concurrent writes, managed backups, and stronger recovery guarantees.
- Add automated database backups and test restores.
- Pin Python dependencies and GitHub Actions to reviewed versions/commit SHAs.
- Add deployment health checks, rollback procedures, monitoring, log retention, and alerts.
- Run vulnerability scans and avoid putting secrets in source control.
- Consider building an immutable image in CI and deploying it from a container registry rather than building on the EC2 host.

## Useful commands

```bash
# Current containers
docker compose ps

# Application logs
docker compose logs -f web

# Rebuild/restart manually
docker compose up -d --build

# Health check
curl -fsS http://127.0.0.1/health

# Stop the application (data volume remains)
docker compose down
```
