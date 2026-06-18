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
pip install requests pandas matplotlib
```
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

All images must be built inside Minikube's Docker daemon so Kubernetes can find them without a registry.

```bash
eval $(minikube docker-env)
```

Build the inference image:

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

Expected output:

```
NAME                                READY   STATUS    RESTARTS   AGE
dispatcher-xxxx                     1/1     Running   0          30s
prometheus-xxxx                     1/1     Running   0          30s
redis-xxxx                          1/1     Running   0          30s
tu-cloud-project-xxxx               1/1     Running   0          30s
```

Press Ctrl+C once all pods show `1/1 Running`.

---

## Step 4 — Start Port Forwards

Run the following in a dedicated terminal and keep it open throughout the session:

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

**Terminal 2 — Load Test:**

```bash
cd dispatcher/test
python3 test.py
```

**Terminal 3 — Watch Pods Scale:**

```bash
watch -n 5 kubectl get pods
```

When the load test reaches Second 630, stop the autoscaler with Ctrl+C and save the log:

```bash
cp dispatcher/autoscaler_log.csv dispatcher/custom_log.csv
```

---

## Step 7 — Run Scenario B: HPA at 70% CPU

```bash
kubectl scale deployment tu-cloud-project --replicas=1
kubectl autoscale deployment tu-cloud-project --cpu-percent=70 --min=1 --max=10
kubectl get hpa
```

Reset the log and run the load test again:

```bash
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
kubectl get hpa
```

Reset the log and run again:

```bash
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

```bash
open comparison_p99_latency.png
open comparison_replicas.png
open autoscaler_performance_plot.png
open p99_latency_plot.png
open queue_size_plot.png
open replica_count_plot.png
```

---

## Pre-recorded Results

The following log files and plots are included in the repository from a completed run and can be viewed without re-running the experiments:

| File | Description |
|---|---|
| `custom_log.csv` | Custom autoscaler run log |
| `hpa70_log.csv` | HPA 70% CPU run log |
| `hpa90_log.csv` | HPA 90% CPU run log |
| `comparison_p99_latency.png` | P99 latency comparison across all three |
| `comparison_replicas.png` | Replica count comparison across all three |
| `autoscaler_performance_plot.png` | Custom autoscaler time-series |
| `p99_latency_plot.png` | P99 latency over time |
| `queue_size_plot.png` | Queue size over time |
| `replica_count_plot.png` | Replica count over time |

To view results directly without running experiments:

```bash
cd dispatcher
python3 compare_autoscalers.py
```

---

## Autoscaler Terminal Output Format

The autoscaler prints a live table every 15 seconds:

```
Timestamp              P99 Latency   Queue Size   Replicas   Action
--------------------------------------------------------------------------------------------
2026-06-18T00:28:53         0.480s           13          1   SCALE UP -> 2 replicas
2026-06-18T00:29:09         0.640s            2          2   SCALE UP -> 3 replicas
2026-06-18T00:29:25         0.650s            1          3   SCALE UP -> 4 replicas
2026-06-18T00:30:12         0.250s            3          5   No scaling needed
2026-06-18T00:30:28         0.250s            3          5   No scaling needed
2026-06-18T00:32:03         0.250s           12          5   SCALE UP -> 6 replicas
```

**Scaling rules:**

| Condition | Action |
|---|---|
| P99 > 0.5s OR Queue > 10 | Scale up by 1 replica (max 10) |
| P99 < 0.2s AND Queue < 3 | Scale down by 1 replica (min 1) |
| Otherwise | No scaling needed |

---

## Prometheus Queries

Open `http://localhost:9090` and run these queries:

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
| Avg P99 Latency | 0.248s | 0.258s | 0.248s |
| Max P99 Latency | 0.249s | 0.406s | 0.249s |
| Avg Replicas Used | 2.46 | 3.13 | 2.46 |
| Latency Target Met | Yes (< 0.5s) | Yes (< 0.5s) | Yes (< 0.5s) |

**Key findings:**

- The custom autoscaler matches HPA-90% performance while using fewer resources than HPA-70%.
- HPA-70% over-provisions replicas without a corresponding latency benefit.
- The custom autoscaler responds directly to latency and queue depth, making it more adaptive than CPU-based HPA.

---

## Troubleshooting

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

```bash
lsof -ti:<port> | xargs kill -9
```

---
