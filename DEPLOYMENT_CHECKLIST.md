# MedVerify Production Deployment Checklist

## Pre-Deployment

- [ ] Domain `medverify.pk` registered and DNS configured
- [ ] Server provisioned (Ubuntu 22.04 LTS, 2+ CPU, 4GB+ RAM, 50GB+ SSD)
- [ ] Static IP assigned to server
- [ ] SSH access configured
- [ ] Docker and Docker Compose installed

## Server Setup

```bash
# 1. SSH to server
ssh root@<server-ip>

# 2. Configure UFW firewall
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable

# 3. Clone repository
git clone <repo-url> /opt/medverify
cd /opt/medverify

# 4. Create .env from template
cp .env.production .env
nano .env  # Fill in all secrets
```

## SSL Certificate

```bash
# 5. Install Certbot and obtain certificate
apt install certbot python3-certbot-nginx
certbot certonly --nginx -d medverify.pk
```

## Database Setup

```bash
# 6. Start database container
docker compose -f docker-compose.prod.yml up -d postgres redis

# 7. Wait for database to be ready
docker compose -f docker-compose.prod.yml exec postgres pg_isready -U medverify

# 8. Run migrations
docker compose -f docker-compose.prod.yml exec backend python -m medverify.db.cli migrate

# 9. Create production admin
docker compose -f docker-compose.prod.yml exec backend python scripts/seed_admin.py

# 10. Remove demo data
docker compose -f docker-compose.prod.yml exec backend python -m medverify.db.cleanup
```

## Application Deployment

```bash
# 11. Copy SSL certificates
mkdir -p frontend/certs
cp /etc/letsencrypt/live/medverify.pk/fullchain.pem frontend/certs/
cp /etc/letsencrypt/live/medverify.pk/privkey.pem frontend/certs/

# 12. Start all services
docker compose -f docker-compose.prod.yml --profile with-ssl up -d
```

## Post-Deployment Verification

- [ ] `curl https://medverify.pk/health` returns `{"status":"ok"}`
- [ ] `curl https://medverify.pk/health/ready` returns `{"status":"ready"}`
- [ ] `curl https://medverify.pk/metrics` returns Prometheus metrics
- [ ] Admin login at `https://medverify.pk/docs` works
- [ ] QR code verification flow functional
- [ ] SSL certificate valid (green lock in browser)
- [ ] No CORS errors in browser console

## Monitoring Setup

```bash
# Optional: Start monitoring stack
docker compose -f monitoring/docker-compose.monitoring.yml --profile monitoring up -d
```

## Backup Verification

```bash
# Test backup script
./scripts/backup.sh
ls -la /backups/
```

## Rollback Plan

```bash
# To rollback to previous version
git pull origin main
docker compose -f docker-compose.prod.yml build backend
docker compose -f docker-compose.prod.yml up -d backend

# Emergency database restore
gunzip < /backups/medverify_YYYYMMDD_HHMMSS.sql.gz | psql -U medverify -h localhost -d medverify
```
