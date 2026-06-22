from flask import Flask, request, jsonify
import os
from model import get_prediction
from prometheus_client import Counter, Histogram, start_http_server

# Start Prometheus metrics server on port 8001
start_http_server(8001)

# Prometheus metrics
requests_total = Counter("inference_requests_total",
                         "Total inference requests")
inference_latency = Histogram(
    "inference_latency_seconds", "Latency of inference")

# Initialize the Flask app
app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
@inference_latency.time()
def index():
    requests_total.inc()
    image_path = None
    input = request.get_json()
    print('input: ', input)

    image_path = input['image']
    #  Check Path exists
    if not os.path.exists(image_path):
        return jsonify({"error": "File does not exist"}), 400

    try:
        result = get_prediction(image_path)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6001)
