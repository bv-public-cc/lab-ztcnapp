import os
import time
from flask import Flask, jsonify, request
import requests

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

def setup_tracing():
    service_name = os.getenv("OTEL_SERVICE_NAME", "otel-demo-app")
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector.telemetry.svc.cluster.local:4318")
    # OTLPSpanExporter for HTTP/protobuf expects full endpoint; it will POST to /v1/traces automatically in exporter
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=endpoint)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

setup_tracing()
tracer = trace.get_tracer(__name__)
app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()

@app.get("/healthz")
def healthz():
    return "ok", 200

@app.get("/")
def root():
    with tracer.start_as_current_span("root-handler"):
        # optional outgoing call to generate nested spans
        downstream = os.getenv("DOWNSTREAM_URL", "")
        if downstream:
            try:
                requests.get(downstream, timeout=1.5)
            except Exception:
                pass
        return jsonify({"service": os.getenv("OTEL_SERVICE_NAME","otel-demo-app"), "path": "/", "ts": int(time.time())})

@app.get("/work")
def work():
    ms = int(request.args.get("ms", "50"))
    with tracer.start_as_current_span("simulated-work"):
        time.sleep(max(ms, 0)/1000.0)
        return jsonify({"slept_ms": ms})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
