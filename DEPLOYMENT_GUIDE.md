# PaymentMate AI - Cloud Deployment Guide

**Version:** 1.0
**Last Updated:** December 3, 2025

---

## Table of Contents

1. [Overview](#overview)
2. [Pre-Deployment Checklist](#pre-deployment-checklist)
3. [AWS ECS Deployment](#aws-ecs-deployment)
4. [Google Cloud Run Deployment](#google-cloud-run-deployment)
5. [Kubernetes Deployment](#kubernetes-deployment)
6. [Environment Variables](#environment-variables)
7. [Monitoring & Logging](#monitoring--logging)
8. [Security Best Practices](#security-best-practices)
9. [Scaling Strategy](#scaling-strategy)
10. [Troubleshooting](#troubleshooting)

---

## Overview

This guide provides step-by-step instructions for deploying PaymentMate AI fraud detection system to cloud platforms. The system consists of three containerized services:

- **Backend**: FastAPI application with ML model (Python 3.11)
- **Frontend**: React dashboard served by nginx
- **Redis**: Feature store for velocity calculations (optional)

**Architecture:**
```
Internet → Load Balancer → Frontend (nginx) → Backend (FastAPI) → Redis
                                    ↓
                              External Clients
```

---

## Pre-Deployment Checklist

### ✅ Before Deploying

- [ ] All Docker images build successfully locally
- [ ] `docker-compose up` runs without errors
- [ ] All tests pass (backend unit tests, frontend build)
- [ ] Environment variables documented in `.env.example`
- [ ] Model artifact (`fraud_model.pkl`) is available
- [ ] API documentation reviewed (`/docs` endpoint)
- [ ] Security review completed (secrets, CORS, authentication)
- [ ] Performance testing completed (latency < 100ms)
- [ ] Backup and rollback strategy defined

### 📦 Required Resources

- Container registry account (ECR, GCR, Docker Hub)
- Cloud platform account (AWS, GCP, or Kubernetes cluster)
- Domain name (optional, for custom URLs)
- SSL certificate (for HTTPS, recommended)
- Monitoring/logging setup (CloudWatch, Stackdriver, ELK)

---

## AWS ECS Deployment

### Architecture

```
┌─────────────────────────────────────────────────┐
│                 Application Load Balancer        │
│                (public, HTTPS)                   │
└────────────┬────────────────────┬────────────────┘
             │                    │
    ┌────────▼────────┐  ┌────────▼────────┐
    │  Frontend Task  │  │  Backend Task   │
    │  (Fargate)      │  │  (Fargate)      │
    │  Port 80        │  │  Port 8000      │
    └─────────────────┘  └────────┬────────┘
                                  │
                         ┌────────▼────────┐
                         │  ElastiCache    │
                         │  (Redis)        │
                         └─────────────────┘
```

### Step 1: Push Images to ECR

```bash
# Authenticate Docker to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-east-1.amazonaws.com

# Create ECR repositories
aws ecr create-repository --repository-name paymentmate-backend --region us-east-1
aws ecr create-repository --repository-name paymentmate-frontend --region us-east-1

# Tag images
docker tag paymentmate-ai-backend:latest 123456789012.dkr.ecr.us-east-1.amazonaws.com/paymentmate-backend:latest
docker tag paymentmate-ai-frontend:latest 123456789012.dkr.ecr.us-east-1.amazonaws.com/paymentmate-frontend:latest

# Push images
docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/paymentmate-backend:latest
docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/paymentmate-frontend:latest
```

### Step 2: Create ElastiCache Redis Cluster

```bash
aws elasticache create-cache-cluster \
  --cache-cluster-id paymentmate-redis \
  --cache-node-type cache.t3.micro \
  --engine redis \
  --num-cache-nodes 1 \
  --region us-east-1

# Get Redis endpoint
aws elasticache describe-cache-clusters \
  --cache-cluster-id paymentmate-redis \
  --show-cache-node-info \
  --query 'CacheClusters[0].CacheNodes[0].Endpoint.Address' \
  --output text
```

### Step 3: Create ECS Task Definitions

**Backend Task Definition:** `backend-task-definition.json`

```json
{
  "family": "paymentmate-backend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::123456789012:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "backend",
      "image": "123456789012.dkr.ecr.us-east-1.amazonaws.com/paymentmate-backend:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "API_HOST", "value": "0.0.0.0"},
        {"name": "API_PORT", "value": "8000"},
        {"name": "FEATURE_STORE_TYPE", "value": "redis"},
        {"name": "REDIS_URL", "value": "redis://paymentmate-redis.abc123.0001.use1.cache.amazonaws.com:6379"},
        {"name": "LOG_LEVEL", "value": "INFO"},
        {"name": "LOG_FORMAT", "value": "json"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/paymentmate-backend",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "python -c 'import requests; requests.get(\"http://localhost:8000/health\", timeout=5)' || exit 1"],
        "interval": 30,
        "timeout": 10,
        "retries": 3,
        "startPeriod": 15
      }
    }
  ]
}
```

**Frontend Task Definition:** `frontend-task-definition.json`

```json
{
  "family": "paymentmate-frontend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::123456789012:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "frontend",
      "image": "123456789012.dkr.ecr.us-east-1.amazonaws.com/paymentmate-frontend:latest",
      "portMappings": [
        {
          "containerPort": 80,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "VITE_API_BASE_URL", "value": "https://api.example.com"},
        {"name": "VITE_API_VERSION", "value": "v1"},
        {"name": "VITE_POLL_INTERVAL", "value": "5000"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/paymentmate-frontend",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "wget --quiet --tries=1 --spider http://localhost:80/health || exit 1"],
        "interval": 30,
        "timeout": 10,
        "retries": 3,
        "startPeriod": 10
      }
    }
  ]
}
```

### Step 4: Register Task Definitions

```bash
aws ecs register-task-definition --cli-input-json file://backend-task-definition.json
aws ecs register-task-definition --cli-input-json file://frontend-task-definition.json
```

### Step 5: Create ECS Cluster

```bash
aws ecs create-cluster --cluster-name paymentmate-cluster --region us-east-1
```

### Step 6: Create ECS Services

```bash
# Backend service
aws ecs create-service \
  --cluster paymentmate-cluster \
  --service-name paymentmate-backend \
  --task-definition paymentmate-backend \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-12345678,subnet-87654321],securityGroups=[sg-12345678],assignPublicIp=ENABLED}" \
  --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/backend-tg/1234567890abcdef,containerName=backend,containerPort=8000"

# Frontend service
aws ecs create-service \
  --cluster paymentmate-cluster \
  --service-name paymentmate-frontend \
  --task-definition paymentmate-frontend \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-12345678,subnet-87654321],securityGroups=[sg-12345678],assignPublicIp=ENABLED}" \
  --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/frontend-tg/abcdef1234567890,containerName=frontend,containerPort=80"
```

### Step 7: Configure Application Load Balancer

1. Create Application Load Balancer in AWS Console
2. Create target groups for backend (port 8000) and frontend (port 80)
3. Configure listener rules:
   - `/api/*` → Backend target group
   - `/` → Frontend target group
4. Enable HTTPS with ACM certificate (recommended)

### AWS Cost Estimate

**Monthly estimate for small deployment:**
- ECS Fargate (2 backend + 2 frontend tasks): ~$60/month
- ElastiCache Redis (cache.t3.micro): ~$15/month
- Application Load Balancer: ~$20/month
- Data transfer (50GB): ~$5/month
- **Total: ~$100/month**

---

## Google Cloud Run Deployment

### Architecture

```
┌─────────────────────────────────────────────┐
│        Google Cloud Load Balancer           │
│           (managed, HTTPS)                  │
└────────────┬────────────────┬───────────────┘
             │                │
    ┌────────▼────────┐  ┌───▼──────────┐
    │  Frontend       │  │  Backend     │
    │  (Cloud Run)    │  │  (Cloud Run) │
    │  Serverless     │  │  Serverless  │
    └─────────────────┘  └───────┬──────┘
                                 │
                        ┌────────▼────────┐
                        │  Memorystore    │
                        │  (Redis)        │
                        └─────────────────┘
```

### Step 1: Push Images to GCR

```bash
# Configure Docker for GCR
gcloud auth configure-docker

# Tag images
docker tag paymentmate-ai-backend:latest gcr.io/my-project/paymentmate-backend:latest
docker tag paymentmate-ai-frontend:latest gcr.io/my-project/paymentmate-frontend:latest

# Push images
docker push gcr.io/my-project/paymentmate-backend:latest
docker push gcr.io/my-project/paymentmate-frontend:latest
```

### Step 2: Create Memorystore Redis Instance

```bash
gcloud redis instances create paymentmate-redis \
  --size=1 \
  --region=us-central1 \
  --tier=basic \
  --redis-version=redis_7_0

# Get Redis host
gcloud redis instances describe paymentmate-redis --region=us-central1 --format='get(host)'
```

### Step 3: Deploy Backend to Cloud Run

```bash
gcloud run deploy paymentmate-backend \
  --image gcr.io/my-project/paymentmate-backend:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8000 \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 1 \
  --max-instances 10 \
  --set-env-vars API_HOST=0.0.0.0,API_PORT=8000,FEATURE_STORE_TYPE=redis,REDIS_URL=redis://10.0.0.3:6379,LOG_LEVEL=INFO,LOG_FORMAT=json \
  --vpc-connector projects/my-project/locations/us-central1/connectors/redis-connector
```

### Step 4: Deploy Frontend to Cloud Run

```bash
gcloud run deploy paymentmate-frontend \
  --image gcr.io/my-project/paymentmate-frontend:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 80 \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 1 \
  --max-instances 5 \
  --set-env-vars VITE_API_BASE_URL=https://paymentmate-backend-abc123-uc.a.run.app,VITE_API_VERSION=v1,VITE_POLL_INTERVAL=5000
```

### Step 5: Configure Load Balancer (Optional)

For custom domain and unified endpoint:

```bash
# Create backend services
gcloud compute backend-services create frontend-backend \
  --global \
  --protocol=HTTP

gcloud compute backend-services create backend-api \
  --global \
  --protocol=HTTP

# Create URL map
gcloud compute url-maps create paymentmate-lb \
  --default-service=frontend-backend

# Add path matcher for /api/*
gcloud compute url-maps add-path-matcher paymentmate-lb \
  --path-matcher-name=api-matcher \
  --default-service=frontend-backend \
  --path-rules="/api/*=backend-api"
```

### GCP Cost Estimate

**Monthly estimate for small deployment:**
- Cloud Run (backend + frontend, 1M requests): ~$25/month
- Memorystore Redis (basic tier, 1GB): ~$35/month
- Load Balancer (optional): ~$20/month
- **Total: ~$60-80/month**

---

## Kubernetes Deployment

### Architecture

```
┌─────────────────────────────────────────────┐
│          Ingress Controller                 │
│          (nginx/traefik)                    │
└────────────┬────────────────┬───────────────┘
             │                │
    ┌────────▼────────┐  ┌───▼──────────┐
    │  Frontend       │  │  Backend     │
    │  Deployment     │  │  Deployment  │
    │  (3 replicas)   │  │  (3 replicas)│
    └─────────────────┘  └───────┬──────┘
                                 │
                        ┌────────▼────────┐
                        │  Redis          │
                        │  StatefulSet    │
                        └─────────────────┘
```

### Kubernetes Manifests

**Namespace:** `paymentmate-namespace.yaml`

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: paymentmate
```

**Redis:** `redis-deployment.yaml`

```yaml
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: paymentmate
spec:
  ports:
  - port: 6379
    targetPort: 6379
  selector:
    app: redis
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: paymentmate
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        args:
          - redis-server
          - --maxmemory
          - 256mb
          - --maxmemory-policy
          - allkeys-lru
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          exec:
            command:
            - redis-cli
            - ping
          initialDelaySeconds: 5
          periodSeconds: 10
```

**Backend:** `backend-deployment.yaml`

```yaml
apiVersion: v1
kind: Service
metadata:
  name: backend
  namespace: paymentmate
spec:
  type: ClusterIP
  ports:
  - port: 8000
    targetPort: 8000
  selector:
    app: backend
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: paymentmate
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: paymentmate-ai-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: API_HOST
          value: "0.0.0.0"
        - name: API_PORT
          value: "8000"
        - name: FEATURE_STORE_TYPE
          value: "redis"
        - name: REDIS_URL
          value: "redis://redis:6379"
        - name: LOG_LEVEL
          value: "INFO"
        - name: LOG_FORMAT
          value: "json"
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 15
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
```

**Frontend:** `frontend-deployment.yaml`

```yaml
apiVersion: v1
kind: Service
metadata:
  name: frontend
  namespace: paymentmate
spec:
  type: ClusterIP
  ports:
  - port: 80
    targetPort: 80
  selector:
    app: frontend
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: paymentmate
spec:
  replicas: 2
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
      - name: frontend
        image: paymentmate-ai-frontend:latest
        ports:
        - containerPort: 80
        env:
        - name: VITE_API_BASE_URL
          value: "http://backend:8000"
        - name: VITE_API_VERSION
          value: "v1"
        - name: VITE_POLL_INTERVAL
          value: "5000"
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 80
          initialDelaySeconds: 5
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 80
          initialDelaySeconds: 3
          periodSeconds: 10
```

**Ingress:** `ingress.yaml`

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: paymentmate-ingress
  namespace: paymentmate
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - paymentmate.example.com
    secretName: paymentmate-tls
  rules:
  - host: paymentmate.example.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: backend
            port:
              number: 8000
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend
            port:
              number: 80
```

### Deploy to Kubernetes

```bash
# Apply all manifests
kubectl apply -f paymentmate-namespace.yaml
kubectl apply -f redis-deployment.yaml
kubectl apply -f backend-deployment.yaml
kubectl apply -f frontend-deployment.yaml
kubectl apply -f ingress.yaml

# Check deployment status
kubectl get pods -n paymentmate
kubectl get services -n paymentmate
kubectl get ingress -n paymentmate

# View logs
kubectl logs -f deployment/backend -n paymentmate
kubectl logs -f deployment/frontend -n paymentmate
```

---

## Environment Variables

### Backend Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `API_HOST` | Host to bind API server | `0.0.0.0` | No |
| `API_PORT` | Port for API server | `8000` | No |
| `API_RELOAD` | Enable auto-reload (dev only) | `false` | No |
| `MODEL_PATH` | Path to model file | `models/fraud_model.pkl` | No |
| `MODEL_VERSION` | Model version identifier | `v1.0.0` | No |
| `FEATURE_STORE_TYPE` | Feature store type (`memory` or `redis`) | `memory` | No |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379` | If using Redis |
| `LOG_LEVEL` | Logging level | `INFO` | No |
| `LOG_FORMAT` | Log format (`text` or `json`) | `json` | No |
| `CORS_ORIGINS` | Allowed CORS origins (comma-separated) | `*` | No |

### Frontend Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `VITE_API_BASE_URL` | Backend API URL | `http://localhost:8000` | No |
| `VITE_API_VERSION` | API version | `v1` | No |
| `VITE_POLL_INTERVAL` | Dashboard polling interval (ms) | `2000` | No |
| `VITE_DEBUG` | Enable debug logging | `false` | No |

---

## Monitoring & Logging

### Structured Logging

Backend uses JSON structured logging for easy parsing:

```json
{
  "timestamp": "2025-12-03T12:00:00.000Z",
  "level": "INFO",
  "message": "Transaction scored",
  "transaction_id": "txn_123456",
  "user_id": 1234,
  "fraud_score": 0.85,
  "decision": "FLAG",
  "latency_ms": 23.5
}
```

### Recommended Monitoring Tools

**AWS:**
- CloudWatch Logs for log aggregation
- CloudWatch Metrics for performance monitoring
- X-Ray for distributed tracing

**GCP:**
- Cloud Logging (formerly Stackdriver)
- Cloud Monitoring for metrics
- Cloud Trace for request tracing

**Kubernetes:**
- Prometheus + Grafana for metrics
- ELK/EFK stack for logs
- Jaeger for distributed tracing

### Key Metrics to Monitor

- **Latency**: P50, P95, P99 response times (target: <100ms)
- **Throughput**: Requests per second
- **Error rate**: 5xx errors, 4xx errors
- **Model performance**: Precision, recall, F1 score
- **Resource usage**: CPU, memory, Redis memory
- **Health checks**: Service availability

---

## Security Best Practices

### 1. Secrets Management

**Do NOT hardcode secrets in environment variables!**

**AWS:** Use AWS Secrets Manager
```bash
aws secretsmanager create-secret \
  --name paymentmate/redis-url \
  --secret-string "redis://prod-redis.abc123.cache.amazonaws.com:6379"
```

**GCP:** Use Secret Manager
```bash
gcloud secrets create redis-url --data-file=redis-url.txt
```

**Kubernetes:** Use Secrets
```bash
kubectl create secret generic paymentmate-secrets \
  --from-literal=redis-url=redis://redis:6379 \
  -n paymentmate
```

### 2. Network Security

- Use VPC/private subnets for backend and Redis
- Expose only frontend via load balancer
- Configure security groups/firewall rules (allow only necessary ports)
- Enable encryption in transit (TLS/SSL)

### 3. Container Security

- Scan images for vulnerabilities (Trivy, Clair)
- Run containers as non-root users (already implemented)
- Keep base images updated
- Use minimal base images (alpine)

### 4. API Security

- Implement rate limiting (prevent abuse)
- Add authentication (API keys, OAuth2)
- Enable CORS with specific origins (not `*`)
- Validate all inputs (Pydantic already does this)
- Add request signing for sensitive operations

### 5. Data Security

- Encrypt data at rest (Redis encryption, EBS encryption)
- Encrypt data in transit (HTTPS, TLS for Redis)
- Implement data retention policies
- Anonymize PII in logs

---

## Scaling Strategy

### Horizontal Scaling

**Backend:**
- Scale based on CPU usage (target: 70%)
- Scale based on request queue length
- Recommended: 2-10 instances for production

**Frontend:**
- Scale based on request count
- Recommended: 2-5 instances (nginx is very efficient)

**Redis:**
- For <10K users: Single instance (cache.t3.micro / 1GB)
- For 10K-100K users: Larger instance (cache.t3.medium / 3.09GB)
- For >100K users: Redis Cluster with sharding

### Vertical Scaling

**Backend resource requirements:**
- Minimum: 512MB RAM, 0.5 CPU
- Recommended: 1GB RAM, 1 CPU
- High load: 2GB RAM, 2 CPU

### Auto-scaling Configuration

**AWS ECS:**
```bash
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/paymentmate-cluster/paymentmate-backend \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 2 \
  --max-capacity 10

aws application-autoscaling put-scaling-policy \
  --policy-name backend-cpu-scaling \
  --service-namespace ecs \
  --resource-id service/paymentmate-cluster/paymentmate-backend \
  --scalable-dimension ecs:service:DesiredCount \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration \
    '{"TargetValue":70.0,"PredefinedMetricSpecification":{"PredefinedMetricType":"ECSServiceAverageCPUUtilization"}}'
```

**Kubernetes HPA:**
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
  namespace: paymentmate
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

---

## Troubleshooting

### Backend Won't Start

**Symptom:** Container crashes immediately

**Diagnosis:**
```bash
# View container logs
docker logs <container-id>
# or
kubectl logs deployment/backend -n paymentmate
```

**Common causes:**
1. Model file missing → Check `MODEL_PATH` and volume mounts
2. Redis connection failed → Verify `REDIS_URL` and network connectivity
3. Port already in use → Change `API_PORT` or fix port conflict
4. Memory limit too low → Increase container memory limit

### High Latency

**Symptom:** Response times >100ms

**Diagnosis:**
```bash
# Check backend logs for timing breakdown
grep "latency_ms" logs.json | jq '.latency_ms'

# Check Redis latency
redis-cli --latency
```

**Solutions:**
1. **Slow features**: Optimize velocity/behavioral feature calculations
2. **Slow Redis**: Increase Redis instance size or use connection pooling
3. **Slow model**: Re-train with fewer features or use model quantization
4. **Network latency**: Deploy backend and Redis in same region/AZ

### Memory Leaks

**Symptom:** Container memory usage increases over time

**Diagnosis:**
```bash
# Monitor memory usage
docker stats <container-id>

# Check Python memory usage
import tracemalloc
tracemalloc.start()
# ... run code ...
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')
```

**Solutions:**
1. Implement connection pooling for Redis
2. Clear feature store TTL properly
3. Limit history buffer size (currently 100 transactions)
4. Restart containers periodically (not ideal, but temporary fix)

### CORS Errors

**Symptom:** Browser shows CORS policy errors

**Diagnosis:**
```
Access to fetch at 'http://backend:8000/api/v1/transaction/score' from origin 'http://frontend' has been blocked by CORS policy
```

**Solutions:**
1. Update `CORS_ORIGINS` to include frontend domain
2. For production: Use specific origins, not `*`
3. Example: `CORS_ORIGINS=https://fraud-dashboard.example.com,https://www.example.com`

---

## Rollback Strategy

### AWS ECS

```bash
# List task definition revisions
aws ecs list-task-definitions --family-prefix paymentmate-backend

# Rollback to previous revision
aws ecs update-service \
  --cluster paymentmate-cluster \
  --service paymentmate-backend \
  --task-definition paymentmate-backend:5  # previous revision
```

### Google Cloud Run

```bash
# List revisions
gcloud run revisions list --service paymentmate-backend

# Rollback to specific revision
gcloud run services update-traffic paymentmate-backend \
  --to-revisions=paymentmate-backend-00005-abc=100
```

### Kubernetes

```bash
# Rollback deployment
kubectl rollout undo deployment/backend -n paymentmate

# Rollback to specific revision
kubectl rollout undo deployment/backend --to-revision=3 -n paymentmate

# Check rollout status
kubectl rollout status deployment/backend -n paymentmate
```

---

## Disaster Recovery

### Backup Strategy

**Model artifacts:**
- Store trained models in S3/GCS with versioning enabled
- Tag models with version and training date
- Keep last 10 model versions for rollback

**Redis data:**
- Enable Redis persistence (AOF or RDB snapshots)
- For AWS ElastiCache: Enable automatic backups
- For GCP Memorystore: Enable snapshot backups
- Backup frequency: Daily (feature data is ephemeral, can be rebuilt)

**Configuration:**
- Version control all deployment manifests (git)
- Use infrastructure-as-code (Terraform, CloudFormation)
- Document environment variables in `.env.example`

### Recovery Procedures

**Scenario 1: Model performance degrades**
1. Check metrics dashboard for precision/recall drop
2. Rollback to previous model version
3. Investigate data drift or feature issues
4. Re-train model with recent data

**Scenario 2: Service outage**
1. Check health checks and container logs
2. Verify Redis connectivity
3. Scale up healthy instances
4. Rollback to previous deployment if needed

**Scenario 3: Redis data loss**
1. Restart backend with `FEATURE_STORE_TYPE=memory` temporarily
2. Restore Redis from latest snapshot
3. Switch backend back to Redis
4. Verify feature calculations are working

---

## Production Checklist

### Before Go-Live

- [ ] Load testing completed (1000+ TPS)
- [ ] Security scan passed (no critical vulnerabilities)
- [ ] SSL/TLS certificates configured
- [ ] Monitoring and alerting configured
- [ ] Log aggregation working
- [ ] Backup and restore tested
- [ ] Rollback procedure documented and tested
- [ ] On-call rotation established
- [ ] Runbook created for common issues
- [ ] Rate limiting configured
- [ ] Auto-scaling tested
- [ ] Disaster recovery plan documented
- [ ] Data retention policy implemented
- [ ] Compliance requirements met (GDPR, PCI-DSS)

### Post-Deployment

- [ ] Monitor metrics for first 24 hours
- [ ] Verify model performance matches test environment
- [ ] Check error rates and latency
- [ ] Confirm auto-scaling triggers correctly
- [ ] Validate log aggregation working
- [ ] Test alerting system
- [ ] Conduct post-mortem if issues occurred

---

## Support & Resources

**Documentation:**
- API Documentation: `http://<backend-url>/docs`
- Project README: [README.md](README.md)
- Architecture Diagrams: [ml/Project Explanation - Technical.md](ml/Project Explanation - Technical.md)

**Cloud Provider Docs:**
- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Kubernetes Documentation](https://kubernetes.io/docs/)

**Troubleshooting:**
- Check logs first: `docker-compose logs -f` or cloud provider logs
- Review [TROUBLESHOOTING.md](TROUBLESHOOTING.md) (if available)
- GitHub Issues: [Report a bug](https://github.com/your-repo/issues)

---

**Last Updated:** December 3, 2025
**Maintained By:** PaymentMate AI DevOps Team
