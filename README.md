# Cloud Computing Project 2026

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

| Tool | Minimum Version |
|---|---|
| Minikube | v1.38+ |
| kubectl | v1.36+ |
| Docker | v29+ |
| Python | v3.11+ |

**Mac/Linux:**
```bash
pip3 install requests pandas matplotlib
```

**Windows:**
```powershell
pip install requests pandas matplotlib
```

---

## Command Reference (Mac vs Windows)

| Task | Mac/Linux | Windows PowerShell |
|---|---|---|
| Point Docker to Minikube | `eval $(minikube docker-env)` | `minikube docker-env \| Invoke-Expression` |
| Run Python script | `python3 script.py` | `python script.py` |
| Install packages | `pip3 install` | `pip install` |
| Kill port process | `lsof -ti:5001 \| xargs kill -9` | `Stop-Process -Id (Get-NetTCPConnection -LocalPort 5001).OwningProcess -Force` |
| Open image file | `open file.png` | `start file.png` |
| Create CSV header | `echo "..." > file.csv` | `"..." \| Out-File -FilePath file.csv -Encoding utf8` |
| Copy file | `cp file1 file2` | `Copy-Item file1 file2` |
| Watch pods | `watch -n 5 kubectl get pods` | `while(1){kubectl get pods; Start-Sleep 5; Clear-Host}` |

---

## Step 1 — Start Minikube

```bash
minikube start --cpus=4 --memory=6144
minikube addons enable metrics-server
kubectl get nodes
```

Wait until node shows `STATUS = Ready`.

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

Build inference image:
```bash
cd ml_model
docker build -t resnet-infer .
cd ..
```

Build dispatcher image:
```bash
cd dispatcher
docker build -t dispatcher .
cd ..
```

Verify:
```bash
docker images
```

Both `resnet-infer` and `dispatcher` must appear in the list.

---

## Step 3 — Deploy to Kubernetes

```bash
kubectl apply -f dispatcher/k8/redis-deployment.yaml
kubectl apply -f dispatcher/k8/inference-deployment.yaml
kubectl apply -f dispatcher/k8/inference-service.yaml
kubectl apply -f dispatcher/k8/dispatcher-deployment.yaml
kubectl apply -f dispatcher/k8/prometheus-deployment.yaml
```

Wait for all pods:
```bash
kubectl get pods -w
```

Wait until all show `1/1 Running`, then Ctrl+C.

---

## Step 4 — Start Port Forwards

Open a dedicated terminal and keep it open throughout the session.

**Mac/Linux:**
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

**Windows** (run each in a separate terminal):
```powershell
kubectl port-forward service/dispatcher-service 5001:5001
```
```powershell
kubectl port-forward service/dispatcher-service 8000:8000
```
```powershell
kubectl port-forward service/tu-cloud-project 8001:8001
```
```powershell
kubectl port-forward service/prometheus-service 9090:9090
```

---

## Step 5 — Verify the Pipeline

**Mac/Linux:**
```bash
curl http://localhost:5001/query \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"image": "/app/images/fire_truck.jpeg"}'
```

**Windows:**
```powershell
Invoke-WebRequest -Uri http://localhost:5001/query -Method POST -ContentType "application/json" -Body '{"image": "/app/images/fire_truck.jpeg"}'
```

Expected response: `{"message": "Queued"}`

Verify Prometheus targets:

**Mac/Linux:**
```bash
curl http://localhost:9090/api/v1/targets | python3 -m json.tool | grep health
```

**Windows:**
```powershell
(Invoke-WebRequest http://localhost:9090/api/v1/targets).Content | python -m json.tool | Select-String "health"
```

Both targets must show `"health": "up"` before running any load test.

---

## Step 6 — Run Scenario A: Custom Autoscaler

**Terminal 1 — Autoscaler:**

Mac/Linux:
```bash
cd dispatcher
echo "Timestamp,P99_Latency,Queue_Size,Replica_Count" > autoscaler_log.csv
python3 autoscaler_logger.py
```

Windows:
```powershell
cd dispatcher
"Timestamp,P99_Latency,Queue_Size,Replica_Count" | Out-File -FilePath autoscaler_log.csv -Encoding utf8
python autoscaler_logger.py
```

**Terminal 2 — Load Test:**

Mac/Linux:
```bash
cd dispatcher/test && python3 test.py
```

Windows:
```powershell
cd dispatcher/test; python test.py
```

**Terminal 3 — Watch Pods:**

Mac/Linux:
```bash
watch -n 5 kubectl get pods
```

Windows:
```powershell
while(1){kubectl get pods; Start-Sleep 5; Clear-Host}
```

When load test reaches Second 630, stop autoscaler (Ctrl+C) and save log:

Mac/Linux:
```bash
cp dispatcher/autoscaler_log.csv dispatcher/custom_log.csv
```

Windows:
```powershell
Copy-Item dispatcher/autoscaler_log.csv dispatcher/custom_log.csv
```

---

## Step 7 — Run Scenario B: HPA at 70% CPU

```bash
kubectl scale deployment tu-cloud-project --replicas=1
kubectl autoscale deployment tu-cloud-project --cpu-percent=70 --min=1 --max=10
kubectl get hpa
```

Reset log:

Mac/Linux:
```bash
echo "Timestamp,P99_Latency,Queue_Size,Replica_Count" > dispatcher/autoscaler_log.csv
```

Windows:
```powershell
"Timestamp,P99_Latency,Queue_Size,Replica_Count" | Out-File -FilePath dispatcher/autoscaler_log.csv -Encoding utf8
```

Run Terminal 1 and Terminal 2 as in Step 6. When done:

Mac/Linux:
```bash
cp dispatcher/autoscaler_log.csv dispatcher/hpa70_log.csv
```

Windows:
```powershell
Copy-Item dispatcher/autoscaler_log.csv dispatcher/hpa70_log.csv
```

```bash
kubectl delete hpa tu-cloud-project
```

---

## Step 8 — Run Scenario C: HPA at 90% CPU

```bash
kubectl scale deployment tu-cloud-project --replicas=1
kubectl autoscale deployment tu-cloud-project --cpu-percent=90 --min=1 --max=10
kubectl get hpa
```

Reset log and run Terminal 1 and Terminal 2 as in Step 6. When done:

Mac/Linux:
```bash
cp dispatcher/autoscaler_log.csv dispatcher/hpa90_log.csv
```

Windows:
```powershell
Copy-Item dispatcher/autoscaler_log.csv dispatcher/hpa90_log.csv
```

```bash
kubectl delete hpa tu-cloud-project
```

---

## Step 9 — Generate Comparison Results

Mac/Linux:
```bash
cd dispatcher
python3 compare_autoscalers.py
python3 analyze_autoscaler_log.py
open comparison_p99_latency.png
open comparison_replicas.png
```

Windows:
```powershell
cd dispatcher
python compare_autoscalers.py
python analyze_autoscaler_log.py
start comparison_p99_latency.png
start comparison_replicas.png
```

---

## Pre-recorded Results

The following files are included and can be viewed without re-running experiments:

| File | Description |
|---|---|
| `custom_log.csv` | Custom autoscaler run log |
| `hpa70_log.csv` | HPA 70% CPU run log |
| `hpa90_log.csv` | HPA 90% CPU run log |
| `comparison_p99_latency.png` | P99 latency comparison |
| `comparison_replicas.png` | Replica count comparison |
| `autoscaler_performance_plot.png` | Custom autoscaler time-series |
| `p99_latency_plot.png` | P99 latency over time |
| `queue_size_plot.png` | Queue size over time |
| `replica_count_plot.png` | Replica count over time |

To regenerate plots from saved logs:

Mac/Linux:
```bash
cd dispatcher && python3 compare_autoscalers.py
```

Windows:
```powershell
cd dispatcher; python compare_autoscalers.py
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

Open `http://localhost:9090` in browser:

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

**Stale latency values with empty queue:**
```bash
kubectl exec deployment/redis -- redis-cli flushall
kubectl scale deployment tu-cloud-project --replicas=1
```

**Pods stuck in Pending:** Forgot to point Docker to Minikube before building images (Step 2).

**Prometheus targets DOWN:** Restart port-forwards (Step 4).

**Autoscaler showing N/A:**

Mac/Linux:
```bash
curl http://localhost:9090/api/v1/targets | python3 -m json.tool | grep health
```

Windows:
```powershell
(Invoke-WebRequest http://localhost:9090/api/v1/targets).Content | python -m json.tool | Select-String "health"
```

**Port already in use:**

Mac/Linux: `lsof -ti:<port> | xargs kill -9`

Windows: `Stop-Process -Id (Get-NetTCPConnection -LocalPort <port>).OwningProcess -Force`