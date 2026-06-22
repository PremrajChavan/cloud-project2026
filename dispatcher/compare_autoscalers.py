import pandas as pd
import matplotlib.pyplot as plt
from datetime import timedelta

def load_log(path, label):
    df = pd.read_csv(path, parse_dates=["Timestamp"])
    df = df[df["P99_Latency"] != "N/A"]
    df["P99_Latency"] = pd.to_numeric(df["P99_Latency"], errors='coerce')
    df = df.dropna(subset=["P99_Latency"])
    df["Replica_Count"] = df["Replica_Count"].astype(int)
    df["label"] = label
    return df

custom = load_log("custom_log.csv", "Custom Autoscaler")
hpa70  = load_log("hpa70_log.csv",  "HPA 70% CPU")
hpa90  = load_log("hpa90_log.csv",  "HPA 90% CPU")

# Normalize all to start at time zero for fair comparison
def normalize_time(df):
    df = df.copy()
    df["Timestamp"] = df["Timestamp"] - df["Timestamp"].iloc[0]
    df["Timestamp"] = df["Timestamp"].dt.total_seconds() / 60 
    return df

custom = normalize_time(custom)
hpa70  = normalize_time(hpa70)
hpa90  = normalize_time(hpa90)

# === Plot 1: P99 Latency Comparison ===
plt.figure(figsize=(12, 5))
plt.plot(custom["Timestamp"], custom["P99_Latency"], label="Custom Autoscaler", color="blue",   linewidth=2)
plt.plot(hpa70["Timestamp"],  hpa70["P99_Latency"],  label="HPA 70% CPU",       color="orange", linewidth=2)
plt.plot(hpa90["Timestamp"],  hpa90["P99_Latency"],  label="HPA 90% CPU",       color="green",  linewidth=2)
plt.axhline(y=0.5, color='r', linestyle='--', label="Target (0.5s)")
plt.title("P99 Latency: Custom Autoscaler vs HPA (time normalized to start)")
plt.xlabel("Time (minutes from start)")
plt.ylabel("P99 Latency (s)")
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("comparison_p99_latency.png", dpi=150)
plt.close()
print("[✓] Saved comparison_p99_latency.png")

# === Plot 2: Replica Count Comparison ===
plt.figure(figsize=(12, 5))
plt.plot(custom["Timestamp"], custom["Replica_Count"], label="Custom Autoscaler", color="blue",   linewidth=2)
plt.plot(hpa70["Timestamp"],  hpa70["Replica_Count"],  label="HPA 70% CPU",       color="orange", linewidth=2)
plt.plot(hpa90["Timestamp"],  hpa90["Replica_Count"],  label="HPA 90% CPU",       color="green",  linewidth=2)
plt.title("CPU Cores Used: Custom Autoscaler vs HPA (time normalized to start)")
plt.xlabel("Time (minutes from start)")
plt.ylabel("Replica Count (= CPU cores, since limit=1)")
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("comparison_replicas.png", dpi=150)
plt.close()
print("[✓] Saved comparison_replicas.png")

# === Summary Table ===
datasets = [
    (custom, "Custom"),
    (hpa70,  "HPA 70%"),
    (hpa90,  "HPA 90%")
]

print("\n=== Summary ===")
print(f"{'Metric':<30} {'Custom':>10} {'HPA 70%':>10} {'HPA 90%':>10}")
print("-" * 62)

print(f"{'Avg P99 Latency (s)':<30}", end="")
for df, _ in datasets:
    print(f"{df['P99_Latency'].mean():>10.3f}", end="")
print()

print(f"{'Max P99 Latency (s)':<30}", end="")
for df, _ in datasets:
    print(f"{df['P99_Latency'].max():>10.3f}", end="")
print()

print(f"{'Min P99 Latency (s)':<30}", end="")
for df, _ in datasets:
    print(f"{df['P99_Latency'].min():>10.3f}", end="")
print()

print(f"{'Avg Replicas':<30}", end="")
for df, _ in datasets:
    print(f"{df['Replica_Count'].mean():>10.2f}", end="")
print()

print(f"{'Max Replicas':<30}", end="")
for df, _ in datasets:
    print(f"{df['Replica_Count'].max():>10.2f}", end="")
print()
