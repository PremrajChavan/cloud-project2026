import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import requests
import time
import subprocess
import csv
import os
from datetime import datetime

PROM_URL = "http://localhost:9090"
DEPLOYMENT_NAME = "tu-cloud-project"
NAMESPACE = "default"
MIN_REPLICAS = 1
MAX_REPLICAS = 10
SCALE_INTERVAL = 15 
CSV_PATH = "autoscaler_log.csv"

# === Prometheus Query ===
def query_prometheus(promql):
    try:
        res = requests.get(f"{PROM_URL}/api/v1/query", params={"query": promql})
        result = res.json()['data']['result']
        if not result:
            return None
        return float(result[0]['value'][1])
    except Exception as e:
        return None

# === Scaling Logic ===
def compute_target_replicas(p99_latency, queue_size, current_replicas):
    if queue_size is None:
        queue_size = 0

    if queue_size == 0:
        return max(current_replicas - 1, MIN_REPLICAS)

    if p99_latency is not None and p99_latency > 0.5:
        needed = max(current_replicas + 2, current_replicas + int(queue_size / 50))
        return min(needed, MAX_REPLICAS)

    if queue_size > 100:
        return min(current_replicas + 2, MAX_REPLICAS)

    if queue_size > 20:
        return min(current_replicas + 1, MAX_REPLICAS)

    return current_replicas

# === Get Replica Count ===
def get_current_replicas():
    output = subprocess.check_output(
        ["kubectl", "get", "deployment", DEPLOYMENT_NAME,
         "-n", NAMESPACE, "-o", "jsonpath={.spec.replicas}"]
    )
    return int(output.decode())

# === Scale Deployment ===
def scale_to_replicas(n):
    subprocess.run(
        ["kubectl", "scale", "deployment", DEPLOYMENT_NAME,
         "-n", NAMESPACE, f"--replicas={n}"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

# === Setup CSV Logger ===
if not os.path.exists(CSV_PATH):
    with open(CSV_PATH, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "P99_Latency", "Queue_Size", "Replica_Count"])

# === Print Table Header ===
def print_header():
    print()
    print(f"{'Timestamp':<22} {'P99 Latency':>12} {'Queue Size':>12} {'Replicas':>10} {'Action':<30}")
    print("-" * 92)

def print_row(timestamp, p99, queue, replicas, action):
    p99_str   = f"{p99:.3f}s" if p99 is not None and str(p99) != 'nan' else "N/A"
    queue_str = str(int(queue)) if queue is not None else "N/A"
    print(f"{timestamp:<22} {p99_str:>12} {queue_str:>12} {replicas:>10} {action:<30}")

# === Generate Visuals ===
def generate_visuals(csv_path):
    try:
        df = pd.read_csv(csv_path, parse_dates=["Timestamp"])
        df = df[df["P99_Latency"] != "N/A"]
        df["P99_Latency"] = pd.to_numeric(df["P99_Latency"], errors='coerce')
        df = df.dropna(subset=["P99_Latency"])
        df["Queue_Size"] = pd.to_numeric(df["Queue_Size"], errors='coerce').fillna(0).astype(int)
        df["Replica_Count"] = df["Replica_Count"].astype(int)

        summary = {
            "Average P99 Latency (s)": round(df["P99_Latency"].mean(), 4),
            "Max P99 Latency (s)":     round(df["P99_Latency"].max(), 4),
            "Min P99 Latency (s)":     round(df["P99_Latency"].min(), 4),
            "Average Queue Size":      round(df["Queue_Size"].mean(), 2),
            "Max Queue Size":          df["Queue_Size"].max(),
            "Average Replica Count":   round(df["Replica_Count"].mean(), 2),
            "Max Replica Count":       df["Replica_Count"].max(),
            "Min Replica Count":       df["Replica_Count"].min()
        }
        summary_df = pd.DataFrame(summary.items(), columns=["Metric", "Value"])
        summary_df.to_csv("autoscaler_summary.csv", index=False)

        plt.figure(figsize=(10, 4))
        plt.plot(df["Timestamp"], df["P99_Latency"], marker='o')
        plt.title("P99 Latency Over Time")
        plt.xlabel("Time")
        plt.ylabel("Latency (s)")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig("p99_latency_plot.png")
        plt.close()

        plt.figure(figsize=(10, 4))
        plt.plot(df["Timestamp"], df["Replica_Count"], marker='s', color="green")
        plt.title("Replica Count Over Time")
        plt.xlabel("Time")
        plt.ylabel("Replicas")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig("replica_count_plot.png")
        plt.close()

        plt.figure(figsize=(10, 4))
        plt.plot(df["Timestamp"], df["Queue_Size"], marker='x', color="red")
        plt.title("Queue Size Over Time")
        plt.xlabel("Time")
        plt.ylabel("Queue Size")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig("queue_size_plot.png")
        plt.close()

    except Exception as e:
        print(f"[!] Error generating plots: {e}")

# === Print header once at start ===
print_header()
row_count = 0

# === Main Loop ===
while True:
    try:
        p99_latency = query_prometheus(
            "histogram_quantile(0.99, rate(inference_latency_seconds_bucket[30s]))"
        )
        queue_size    = query_prometheus("dispatcher_queue_size")
        current_replicas = get_current_replicas()
        timestamp     = datetime.now().isoformat(timespec='seconds')

        new_replicas  = compute_target_replicas(p99_latency, queue_size, current_replicas)

        if new_replicas > current_replicas:
            action = f"SCALE UP -> {new_replicas} replicas"
            scale_to_replicas(new_replicas)
        elif new_replicas < current_replicas:
            action = f"SCALE DOWN -> {new_replicas} replicas"
            scale_to_replicas(new_replicas)
        else:
            action = "No scaling needed"

        print_row(timestamp, p99_latency, queue_size, current_replicas, action)

        # Re-print header every 20 rows for readability
        row_count += 1
        if row_count % 20 == 0:
            print_header()

        # Log to CSV
        with open(CSV_PATH, mode='a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                timestamp,
                p99_latency if p99_latency is not None else "N/A",
                queue_size  if queue_size  is not None else "N/A",
                current_replicas
            ])

        generate_visuals(CSV_PATH)

    except Exception as e:
        print(f"[!] Error: {e}")

    time.sleep(SCALE_INTERVAL)