# Cloud Computing Project 2026
---

## Overview

This project implements a containerized machine learning inference service using ResNet18 on CPU, deployed on Minikube. It includes a custom autoscaler that dynamically scales inference replicas based on P99 latency and queue size, and compares its performance against Kubernetes Horizontal Pod Autoscaler (HPA) at 70% and 90% CPU targets.

---

## System Architecture

```
Load Tester --> Dispatcher (Flask + Redis) --> ML Inference Replicas (ResNet18)
                      |                               |
                 Prometheus <----- Metrics (port 8000, 8001)
                      |
                Custom Autoscaler (reads Prometheus, scales via kubectl)
```

**Components:**

- `ml_model/` — ResNet18 Flask inference service (port 6001), Prometheus metrics (port 8001)
- `dispatcher/` — Redis-backed request dispatcher with round-robin load balancing (port 5001), Prometheus metrics (port 8000)
- `dispatcher/autoscaler_logger.py` — Custom autoscaler running every 15 seconds
- `dispatcher/test/` — Load tester that replays a real workload pattern
- `dispatcher/k8/` — All Kubernetes YAML deployment files

---

## Prerequisites

Ensure the following are installed before proceeding:

| Tool | Minimum Version |
|---|---|
| Minikube | v1.38+ |
| kubectl | v1.36+ |
| Docker | v29+ |
| Python | v3.11+ |

Python packages required (for running autoscaler and analysis locally):

```bash
pip3 install requests pandas matplotlib  # Windows: pip install requests pandas matplotlib
```

**Windows Users:** Use these command replacements:

| Mac/Linux | Windows PowerShell |
|---|---|
| `eval $(minikube docker-env)` | `minikube docker-env | Invoke-Expression` |
| `python3 script.py` | `python script.py` |
| `pip3 install` | `pip install` |
| `lsof -ti:5001 \| xargs kill -9` | `Stop-Process -Id (Get-NetTCPConnection -LocalPort 5001).OwningProcess -Force` |
| `open file.png` | `start file.png` |
| `echo "..." > file.csv` | `"..." \| Out-File -FilePath file.csv` |
| `cp file1 file2` | `Copy-Item file1 file2` |

---

## Step 1 — Start Minikube

```bash
minikube start --cpus=4 --memory=6144
minikube addons enable metrics-server
kubectl get nodes
```

Wait until the node shows `STATUS = Ready` before proceeding.

---

## Step 2 — Build Docker Images Inside Minikube

**Mac/Linux:**
```bash
eval $(minikube docker-env)
```

**Windows:**
```powershell
minikube docker-env | Invoke-Expression
```

```bash
cd ml_model
docker build -t resnet-infer .
cd ..
```

Build the dispatcher image:

```bash
cd dispatcher
docker build -t dispatcher .
cd ..
```

Verify both images exist:

```bash
docker images | grep -E "resnet-infer|dispatcher"
```

---

## Step 3 — Deploy to Kubernetes

Apply all manifests in order:

```bash
kubectl apply -f dispatcher/k8/redis-deployment.yaml
kubectl apply -f dispatcher/k8/inference-deployment.yaml
kubectl apply -f dispatcher/k8/inference-service.yaml
kubectl apply -f dispatcher/k8/dispatcher-deployment.yaml
kubectl apply -f dispatcher/k8/prometheus-deployment.yaml
```

Wait for all pods to reach Running state:

```bash
kubectl get pods -w
```

Wait for all pods to show `1/1 Running`, then Ctrl+C.

---

## Step 4 — Start Port Forwards

**Mac/Linux** (Run the following in a dedicated terminal and keep it open throughout the session:):
```bash
lsof -ti:5001 | xargs kill -9 2>/dev/null; true
lsof -ti:8000 | xargs kill -9 2>/dev/null; true
lsof -ti:8001 | xargs kill -9 2>/dev/null; true
lsof -ti:9090 | xargs kill -9 2>/dev/null; true
kubectl port-forward service/dispatcher-service 5001:5001 &
kubectl port-forward service/dispatcher-service 8000:8000 &
kubectl port-forward service/tu-cloud-project 8001:8001 &
kubectl port-forward service/prometheus-service 9090:9090 &
```

**Windows** (four separate terminals):
```powershell
kubectl port-forward service/dispatcher-service 5001:5001
kubectl port-forward service/dispatcher-service 8000:8000
kubectl port-forward service/tu-cloud-project 8001:8001
kubectl port-forward service/prometheus-service 9090:9090
```

---

## Step 5 — Verify the Pipeline

Test that a request flows end-to-end:

```bash
curl http://localhost:5001/query \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"image": "/app/images/fire_truck.jpeg"}'
```

Expected response:

```json
{"message": "Queued"}
```

Verify Prometheus is scraping both services:

```bash
curl http://localhost:9090/api/v1/targets | python3 -m json.tool | grep health
```

Both targets must show `"health": "up"` before running any load test.

---

## Step 6 — Run Scenario A: Custom Autoscaler

Open three terminals:

**Terminal 1 — Autoscaler:**

```bash
cd dispatcher
echo "Timestamp,P99_Latency,Queue_Size,Replica_Count" > autoscaler_log.csv
python3 autoscaler_logger.py
```

**Terminal 2:**
```bash
cd dispatcher/test && python3 test.py
```

**Terminal 3:**
```bash
watch -n 5 kubectl get pods
```

When load test reaches Second 630, stop autoscaler (Ctrl+C):
```bash
cp dispatcher/autoscaler_log.csv dispatcher/custom_log.csv
```

---

## Step 7 — Run Scenario B: HPA at 70% CPU

```bash
kubectl scale deployment tu-cloud-project --replicas=1
kubectl autoscale deployment tu-cloud-project --cpu-percent=70 --min=1 --max=10
echo "Timestamp,P99_Latency,Queue_Size,Replica_Count" > dispatcher/autoscaler_log.csv
```

**Terminal 1:**

```bash
cd dispatcher && python3 autoscaler_logger.py
```

**Terminal 2:**

```bash
cd dispatcher/test && python3 test.py
```

When done:

```bash
cp dispatcher/autoscaler_log.csv dispatcher/hpa70_log.csv
kubectl delete hpa tu-cloud-project
```

---

## Step 8 — Run Scenario C: HPA at 90% CPU

```bash
kubectl scale deployment tu-cloud-project --replicas=1
kubectl autoscale deployment tu-cloud-project --cpu-percent=90 --min=1 --max=10
echo "Timestamp,P99_Latency,Queue_Size,Replica_Count" > dispatcher/autoscaler_log.csv
```

**Terminal 1:**

```bash
cd dispatcher && python3 autoscaler_logger.py
```

**Terminal 2:**

```bash
cd dispatcher/test && python3 test.py
```

When done:

```bash
cp dispatcher/autoscaler_log.csv dispatcher/hpa90_log.csv
kubectl delete hpa tu-cloud-project
```

---

## Step 9 — Generate Comparison Results

```bash
cd dispatcher
python3 compare_autoscalers.py
python3 analyze_autoscaler_log.py
```

Open the generated plots:
**Mac:** `open comparison_p99_latency.png`
**Windows:** `start comparison_p99_latency.png`

---

## Pre-recorded Results

| File | Description |
|---|---|
| `custom_log.csv` | Custom autoscaler run log |
| `hpa70_log.csv` | HPA 70% CPU run log |
| `hpa90_log.csv` | HPA 90% CPU run log |
| `comparison_p99_latency.png` | P99 latency comparison |
| `comparison_replicas.png` | Replica count comparison |
| `autoscaler_performance_plot.png` | Custom autoscaler time-series |

To view without re-running:
```bash
cd dispatcher && python3 compare_autoscalers.py
```

---

## Autoscaler Scaling Rules

| Condition | Action |
|---|---|
| P99 > 0.5s (SLO violated) | Scale up aggressively (+2 or queue/50) |
| Queue > 100 | Scale up by 2 replicas (proactive) |
| Queue > 20 | Scale up by 1 replica (proactive) |
| Queue = 0 | Scale down by 1 replica |
| Otherwise | No scaling needed |

---

## Prometheus Queries

Open `http://localhost:9090`:

| Metric | Query |
|---|---|
| P99 Latency | `histogram_quantile(0.99, rate(inference_latency_seconds_bucket[1m]))` |
| Queue Size | `dispatcher_queue_size` |
| Total Requests | `dispatcher_requests_total` |
| Forwarded Requests | `dispatcher_requests_forwarded` |

---

## Results Summary

| Metric | Custom Autoscaler | HPA 70% | HPA 90% |
|---|---|---|---|
| Avg P99 Latency | 0.248s | 0.265s | 0.248s |
| Max P99 Latency | 0.456s | 0.406s | 0.456s |
| Avg Replicas Used | 2.78 | 2.81 | 2.83 |
| Latency Target Met | Yes (< 0.5s) | Yes (< 0.5s) | Yes (< 0.5s) |

The custom autoscaler reacts directly to latency and queue depth, outperforming CPU-based HPA under bursty workloads.

---

## Troubleshooting

**Autoscaler shows stale latency values with empty queue:**

This is residual Prometheus data from a previous run. Flush Redis and wait 2 minutes before starting:

```bash
kubectl exec deployment/redis -- redis-cli flushall
kubectl scale deployment tu-cloud-project --replicas=1
```

**Pods stuck in Pending state:**

```bash
kubectl describe pod <pod-name>
```

Most common cause: forgot to run `eval $(minikube docker-env)` before building images.

**Prometheus targets showing DOWN:**

```bash
kubectl get pods | grep prometheus
kubectl logs deployment/prometheus --tail=20
```

Restart port-forwards if they died.

**Autoscaler showing N/A for all metrics:**

Prometheus is not scraping yet. Verify targets are UP:

```bash
curl http://localhost:9090/api/v1/targets | python3 -m json.tool | grep health
```

**Port already in use:**

Mac: `lsof -ti:<port> | xargs kill -9`

Windows: `Stop-Process -Id (Get-NetTCPConnection -LocalPort <port>).OwningProcess -Force`