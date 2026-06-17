import pandas as pd
import matplotlib.pyplot as plt
import sys

# Usage:
#   python compare_autoscalers.py custom_log.csv hpa70_log.csv hpa90_log.csv

def load_log(path, label):
    df = pd.read_csv(path, parse_dates=["Timestamp"])
    df = df[df["P99_Latency"] != "N/A"]
    df["P99_Latency"] = df["P99_Latency"].astype(float)
    df["Replica_Count"] = df["Replica_Count"].astype(int)
    df["label"] = label
    return df

custom = load_log("autoscaler_log.csv", "Custom Autoscaler")
hpa70  = load_log("hpa70_log.csv",      "HPA 70% CPU")
hpa90  = load_log("hpa90_log.csv",      "HPA 90% CPU")

# === Plot 1: P99 Latency Comparison ===
plt.figure(figsize=(12, 5))
for df, name in [(custom, "Custom"), (hpa70, "HPA 70%"), (hpa90, "HPA 90%")]:
    plt.plot(df["Timestamp"], df["P99_Latency"], label=name)
plt.axhline(y=0.5, color='r', linestyle='--', label="Target (0.5s)")
plt.title("P99 Latency: Custom Autoscaler vs HPA")
plt.xlabel("Time")
plt.ylabel("P99 Latency (s)")
plt.legend()
plt.tight_layout()
plt.xticks(rotation=45)
plt.savefig("comparison_p99_latency.png")
plt.close()
print("[✓] Saved comparison_p99_latency.png")

# === Plot 2: Replica Count (CPU Cores) Comparison ===
plt.figure(figsize=(12, 5))
for df, name in [(custom, "Custom"), (hpa70, "HPA 70%"), (hpa90, "HPA 90%")]:
    plt.plot(df["Timestamp"], df["Replica_Count"], label=name)
plt.title("CPU Cores Used: Custom Autoscaler vs HPA")
plt.xlabel("Time")
plt.ylabel("Replica Count (= CPU cores, since limit=1)")
plt.legend()
plt.tight_layout()
plt.xticks(rotation=45)
plt.savefig("comparison_replicas.png")
plt.close()
print("[✓] Saved comparison_replicas.png")

# === Summary Table ===
print("\n=== Summary ===")
print(f"{'Metric':<30} {'Custom':>10} {'HPA 70%':>10} {'HPA 90%':>10}")
print("-" * 62)

datasets = [
    (load_log("custom_log.csv", "Custom"), "Custom"),
    (load_log("hpa70_log.csv", "HPA 70%"), "HPA 70%"),
    (load_log("hpa90_log.csv", "HPA 90%"), "HPA 90%")
]

print(f"{'Avg P99 Latency (s)':<30}", end="")
for df, _ in datasets:
    print(f"{df['P99_Latency'].mean():>10.3f}", end="")
print()

print(f"{'Max P99 Latency (s)':<30}", end="")
for df, _ in datasets:
    print(f"{df['P99_Latency'].max():>10.3f}", end="")
print()

print(f"{'Avg Replicas':<30}", end="")
for df, _ in datasets:
    print(f"{df['Replica_Count'].mean():>10.2f}", end="")
print()