# Deploying to AWS EC2 (step by step)

AWS free-tier terms change, so check the current offer when you sign up.
Accounts created after July 15, 2025 get credits (a free plan for up to 6 months,
credits valid 12 months) instead of the old 12-month free tier, and older accounts
keep the legacy free tier. Choose the Free plan at sign-up if offered.
**Set a billing alert first** (AWS Billing -> Budgets) and **stop or terminate
the instance** when you no longer need the demo running.

## 1. Push the project to GitHub
Create a repo named `url-shortener` and push this folder to the `main` branch.
Do NOT commit the `venv` folder (add a `.gitignore` with `venv/` and `__pycache__/`).

## 2. Launch an EC2 instance
- AMI: Ubuntu 24.04 LTS
- Instance type: a free-tier-eligible one (e.g. t2.micro / t3.micro, as shown in your console)
- Key pair: create one and download the `.pem` file (used only for your first login)
- Security group inbound rules:
  - SSH (22): source = **Anywhere (0.0.0.0/0)**. Needed because GitHub Actions
    connects from changing IP addresses, so "My IP" would block the deploy job.
    This is acceptable for a demo project because Ubuntu on EC2 only allows
    key-based login (no passwords). Never share your private keys.
  - Custom TCP (5000): source = Anywhere (this is the app)
  - Do NOT open 5432 (PostgreSQL) or 6379 (Redis) to the internet
  - Stricter alternatives (good interview talking points): AWS Systems Manager
    Session Manager, or a self-hosted GitHub runner.

## 3. Install Docker on the server
SSH in (`ssh -i your-key.pem ubuntu@<EC2_PUBLIC_IP>`), then:

    sudo apt update
    sudo apt install -y docker.io docker-compose-v2 git
    sudo usermod -aG docker ubuntu
    exit

Log in again so the group change applies.

## 3b. Add swap memory (recommended on small instances with ~1 GB RAM)
Building images plus PostgreSQL, Redis and 4 Gunicorn workers can run out of memory.

    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

If the app is still unstable, reduce `-w 4` to `-w 2` in the `Dockerfile`.

## 4. Clone and start the app (first time, manually)
**The repo must be public** for the `git clone` and `git pull` below to work
without a login. For a private repo, set up a GitHub deploy key on the server first.


    git clone https://github.com/<your-username>/url-shortener.git
    cd url-shortener
    docker compose up -d --build

Test: open `http://<EC2_PUBLIC_IP>:5000/` in a browser, or POST to `/shorten`.

## 5. Create a dedicated deploy key for GitHub Actions
On your own computer:

    ssh-keygen -t ed25519 -f deploy_key -N ""

- Append the contents of `deploy_key.pub` to `~/.ssh/authorized_keys` on the EC2 server.
- Keep `deploy_key` (the private key) secret. Never commit it.

## 6. Add GitHub repository secrets
Repo -> Settings -> Secrets and variables -> Actions -> New repository secret:

| Name | Value |
|------|-------|
| `EC2_HOST` | the EC2 public IP address |
| `EC2_USER` | `ubuntu` |
| `EC2_SSH_KEY` | the full contents of the `deploy_key` file |

## 7. Trigger the pipeline
Push any change to `main`. GitHub Actions will run the tests, check the Docker
build, then SSH into EC2, pull the latest code and rebuild the containers.
Check progress in the repo's **Actions** tab.

## Notes
- The public IP changes if you stop and start the instance (unless you attach an
  Elastic IP). If it changes, update the `EC2_HOST` secret.
- Production hardening ideas (good interview talking points): move DB passwords
  to a `.env` file or secrets manager, put Nginx in front with HTTPS, push the
  image to a registry (ECR) instead of building on the server.
