# Deployment & Demonstration Guide

## 1. Start Minikube

```bash
minikube start --cpus=4 --memory=6144
kubectl get nodes
```

---

## 2. Deploy Application Stack

```bash
kubectl apply -f dispatcher/k8/redis-deployment.yaml
kubectl apply -f dispatcher/k8/inference-deployment.yaml
kubectl apply -f dispatcher/k8/inference-service.yaml
kubectl apply -f dispatcher/k8/dispatcher-deployment.yaml
kubectl apply -f dispatcher/k8/prometheus-deployment.yaml
```

Monitor deployment:

```bash
kubectl get pods -w
```

Wait until all pods are `Running`.

---

## 3. Configure Port Forwarding

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

## 4. Verify Deployment

### Test Inference Pipeline

```bash
curl http://localhost:5001/query \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"image": "/app/images/fire_truck.jpeg"}'
```

Expected response:

```json
{"message":"Queued"}
```

### Verify Prometheus Targets

```bash
curl http://localhost:9090/api/v1/targets | python3 -m json.tool | grep health
```

Expected:

```text
"health": "up"
```

### Verify Running Pods

```bash
kubectl get pods
```

---

## 5. Start Custom Autoscaler Monitoring

**Terminal 1**

```bash
cd dispatcher
python3 autoscaler_logger.py
```

---

## 6. Generate Load

**Terminal 2**

```bash
cd dispatcher/test
python3 test.py
```

---

## 7. Monitor Scaling

**Terminal 3**

```bash
watch -n 5 kubectl get pods
```

Observe replicas scaling in real time.

---

## 8. Visualize Metrics in Prometheus

Open:

```text
http://localhost:9090
```

Query:

```promql
histogram_quantile(0.99, rate(inference_latency_seconds_bucket[1m]))
```

Switch to **Graph** view to display live P99 latency.

---

## 9. Analyze Results

```bash
cd dispatcher
python3 compare_autoscalers.py
python3 analyze_autoscaler_log.py
```

Open generated plots:

```bash
open comparison_p99_latency.png
open comparison_replicas.png
open autoscaler_performance_plot.png
open p99_latency_plot.png
open queue_size_plot.png
open replica_count_plot.png
```

---

## 10. Demonstrate Kubernetes HPA

```bash
kubectl autoscale deployment tu-cloud-project --cpu-percent=70 --min=1 --max=10

kubectl get hpa

watch -n 5 kubectl get hpa
```

---

# Demo Setup

| Terminal   | Purpose                |
| ---------- | ---------------------- |
| Terminal 1 | Custom autoscaler logs |
| Terminal 2 | Load generation        |
| Terminal 3 | Pod scaling monitor    |
| Browser    | Prometheus dashboard   |

---

# Key Takeaways

* Custom autoscaler uses **latency and queue length** as scaling signals.
* Maintains **sub-second response latency** under load.
* Achieves comparable performance with **fewer replicas than CPU-based HPA**.
* Entire infrastructure is deployed using **Kubernetes manifests**.
* Inference service runs on **CPU-only ResNet18**, without GPU acceleration.
