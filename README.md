# TU Cloud Project - Scalable Image Classification with Autoscaling

This project implements a cloud-based image inference system using Docker, Kubernetes, Redis, Prometheus, and Flask. It supports both custom autoscaling and Kubernetes HPA, and evaluates performance under varying workloads.

---

## Architecture

```
Client -> Dispatcher (port 5001) -> Redis Queue -> ML Model replica(s) (port 6001)
                |                                           |
      Prometheus metrics (:8000)              Prometheus metrics (:8001)
                |
      Autoscaler (reads Prometheus -> scales K8s replicas)
```

---

## Prerequisites

Install the following before starting:

| Tool           | Version | Install                                      |
|----------------|---------|----------------------------------------------|
| Python         | 3.9+    | https://python.org/downloads                 |
| Docker Desktop | Latest  | https://docker.com/products/docker-desktop   |
| Minikube       | Latest  | `brew install minikube` (Mac)                |
| kubectl        | Latest  | `brew install kubectl` (Mac)                 |

Verify installs:

```bash
python3 --version
docker --version
minikube version
kubectl version --client
```

---

## Setup Instructions

### Step 1 - Clone the Repository

```bash
git clone https://github.com/SatyaDewangan05/tu-cloud-project.git
cd tu-cloud-project
```

---

### Step 2 - Start Infrastructure

Make sure Docker Desktop is running first.

Start Redis:

```bash
docker run -d -p 6379:6379 redis
```

Start Prometheus (run from the project root directory):

```bash
docker run -d \
  -p 9090:9090 \
  --mount type=bind,source=$(pwd)/dispatcher/prometheus.yml,target=/etc/prometheus \
  prom/prometheus
```

Verify both containers are running:

```bash
docker ps
```

You should see both `redis` and `prom/prometheus` listed. Open the Prometheus UI at http://localhost:9090 to confirm.

---

### Step 3 - Run the ML Model Server

```bash
cd ml_model
python3 -m venv venv_model
source venv_model/bin/activate
pip install flask torch torchvision pillow prometheus-client opencv-python
python app.py
```

Expected output:
```
* Running on http://127.0.0.1:6001
```

Metrics available at: http://localhost:8001/metrics

---

### Step 4 - Run the Dispatcher

Open a new terminal:

```bash
cd dispatcher
python3 -m venv venv_disp
source venv_disp/bin/activate
pip install flask redis prometheus-client requests
python dispatcher_redis.py
```

Expected output:
```
Redis-based Dispatcher running on http://localhost:5001
```

Metrics available at: http://localhost:8000/metrics

---

### Step 5 - Test the System

Open a new terminal and send a test request. Replace the path with the absolute path to an image on your machine:

```bash
curl -X POST http://localhost:5001/query \
  -H "Content-Type: application/json" \
  -d '{"image": "/absolute/path/to/tu-cloud-project/ml_model/images/fire_truck.jpeg"}'
```

Expected response:

```json
{"message": "Queued"}
```

In the dispatcher terminal you should see:

```
[OK] Forwarded <request-id> to http://localhost:6001/ -> 200; Prediction: {"class": "fire truck", "confidence": 0.97}
```

---

### Step 6 - Deploy to Minikube (Kubernetes)

Start Minikube:

```bash
minikube start --cpus=4 --memory=6144
```

Verify it is running:

```bash
minikube status
```

Build the Docker image inside Minikube's Docker environment:

```bash
eval $(minikube docker-env)
cd ml_model
docker build -t inference-model .
```

Deploy Kubernetes resources from the project root:

```bash
cd ..
kubectl apply -f dispatcher/k8/inference-deployment.yaml
kubectl apply -f dispatcher/k8/inference-service.yaml
kubectl apply -f dispatcher/k8/hpa-70.yaml
```

Expose the service:

```bash
minikube service tu-cloud-project
kubectl port-forward deployment/tu-cloud-project 6001:6001 8001:8001
```

---

## Autoscaler Usage

Run from the dispatcher directory with the virtual environment active:

```bash
cd dispatcher
source venv_disp/bin/activate
python autoscaler_logger.py
```

To analyze logs and generate plots:

```bash
python analyze_autoscaler_log.py
```

This generates the following files in the dispatcher directory:

- `autoscaler_summary.csv`
- `p99_latency_plot.png`
- `queue_size_plot.png`
- `replica_count_plot.png`

---

## Load Testing

```bash
cd dispatcher/test
python test.py
```

Use `workload.txt` or `workload_heavy.txt` to simulate different requests-per-second loads.

---

## Kubernetes HPA Setup

Deploy HPA with a CPU target of 70%:

```bash
kubectl autoscale deployment tu-cloud-project --cpu-percent=70 --min=1 --max=10
```

Monitor HPA scaling decisions:

```bash
watch -n 5 kubectl get hpa
```

---

## Processes Reference

| Process             | Command                      | Port |
|---------------------|------------------------------|------|
| ML Model server     | `python app.py`              | 6001 |
| Dispatcher server   | `python dispatcher_redis.py` | 5001 |
| Redis               | Docker                       | 6379 |
| Prometheus          | Docker                       | 9090 |
| Minikube            | `minikube start`             | -    |

---

## Goals

- Achieve server-side latency under 0.5 seconds
- Demonstrate autoscaler responsiveness under load
- Compare HPA (70%, 90%) vs custom autoscaler

---

## Contact

For any help, reach out to your project supervisor or the contributor.