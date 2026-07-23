"""
Gateway Service - Main Application.

Thin routing layer: auth, correlation ID injection, service delegation.
No business logic - pure observability demonstration.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

import httpx
from fastapi import FastAPI, Header, HTTPException, Query, Request, Response
from opentelemetry.trace import StatusCode
from pydantic import BaseModel

from instrumentation import tracer, business_spans, compute_fibonacci


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Service URLs from environment
ORDERS_URL = os.getenv("ORDERS_URL", "http://orders:8000")
PAYMENTS_URL = os.getenv("PAYMENTS_URL", "http://payments:8000")

# HTTP client with timeout
http_client = httpx.AsyncClient(timeout=httpx.Timeout(5.0))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("Starting Gateway service")
    yield
    await http_client.aclose()
    logger.info("Shutting down Gateway service")


app = FastAPI(
    title="Gateway Service",
    version="0.1.0",
    description="Observability demo gateway - routing, auth, correlation",
    lifespan=lifespan,
)

# Auto-instrumentation: instrument the app instance directly.
# instrument_app() adds OpenTelemetryMiddleware to the existing app,
# bypassing the class-replacement mechanism entirely.
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
FastAPIInstrumentor().instrument_app(app)
HTTPXClientInstrumentor().instrument()


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "gateway"
    version: str = "0.1.0"


class OrderResponse(BaseModel):
    order_id: str
    items: list
    total: float


class PaymentResponse(BaseModel):
    payment_id: str
    amount: float
    status: str


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    return HealthResponse()


@app.get("/orders", response_model=list[OrderResponse])
async def get_orders(
    request: Request,
    x_correlation_id: Optional[str] = Header(None, alias="X-Correlation-ID"),
):
    """
    Get all orders - delegates to Orders service.
    
    Demonstrates:
    - Correlation ID propagation
    - Outbound HTTP tracing
    - Structured logging with traceID
    """
    correlation_id = x_correlation_id or request.headers.get("x-correlation-id", "none")
    logger.info("Fetching orders", extra={"correlation_id": correlation_id})
    
    with tracer.start_as_current_span("gateway.get_orders") as span:
        span.set_attribute("correlation_id", correlation_id)
        
        # Outbound call with tracing
        with business_spans.http_call("GET", f"{ORDERS_URL}/orders", "orders") as child_span:
            child_span.set_attribute("correlation_id", correlation_id)
            try:
                response = await http_client.get(f"{ORDERS_URL}/orders")
                child_span.set_attribute("http.status_code", response.status_code)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    raise HTTPException(status_code=404, detail="Orders not found")
                else:
                    raise HTTPException(status_code=response.status_code, detail="Orders service error")
                    
            except httpx.RequestError as e:
                logger.error("Orders service unavailable", extra={"error": str(e)})
                span.set_status(StatusCode.ERROR, str(e))
                span.record_exception(e)
                raise HTTPException(status_code=503, detail="Orders service unavailable")


@app.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    request: Request,
    x_correlation_id: Optional[str] = Header(None, alias="X-Correlation-ID"),
):
    """Get single order by ID."""
    correlation_id = x_correlation_id or request.headers.get("x-correlation-id", "none")
    logger.info("Fetching order", extra={"order_id": order_id, "correlation_id": correlation_id})
    
    with tracer.start_as_current_span("gateway.get_order") as span:
        span.set_attribute("order_id", order_id)
        span.set_attribute("correlation_id", correlation_id)
        
        with business_spans.http_call("GET", f"{ORDERS_URL}/orders/{order_id}", "orders") as child_span:
            child_span.set_attribute("order_id", order_id)
            child_span.set_attribute("correlation_id", correlation_id)
            
            try:
                response = await http_client.get(f"{ORDERS_URL}/orders/{order_id}")
                child_span.set_attribute("http.status_code", response.status_code)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    raise HTTPException(status_code=404, detail="Order not found")
                else:
                    raise HTTPException(status_code=response.status_code, detail="Orders service error")
                    
            except httpx.RequestError as e:
                logger.error("Orders service unavailable", extra={"error": str(e), "order_id": order_id})
                span.set_status(StatusCode.ERROR, str(e))
                span.record_exception(e)
                raise HTTPException(status_code=503, detail="Orders service unavailable")


@app.get("/payments", response_model=list[PaymentResponse])
async def get_payments(
    request: Request,
    x_correlation_id: Optional[str] = Header(None, alias="X-Correlation-ID"),
):
    """Get all payments - delegates to Payments service."""
    correlation_id = x_correlation_id or request.headers.get("x-correlation-id", "none")
    logger.info("Fetching payments", extra={"correlation_id": correlation_id})
    
    with tracer.start_as_current_span("gateway.get_payments") as span:
        span.set_attribute("correlation_id", correlation_id)
        
        with business_spans.http_call("GET", f"{PAYMENTS_URL}/payments", "payments") as child_span:
            child_span.set_attribute("correlation_id", correlation_id)
            try:
                response = await http_client.get(f"{PAYMENTS_URL}/payments")
                child_span.set_attribute("http.status_code", response.status_code)
                
                if response.status_code == 200:
                    return response.json()
                else:
                    raise HTTPException(status_code=response.status_code, detail="Payments service error")
                    
            except httpx.RequestError as e:
                logger.error("Payments service unavailable", extra={"error": str(e)})
                span.set_status(StatusCode.ERROR, str(e))
                span.record_exception(e)
                raise HTTPException(status_code=503, detail="Payments service unavailable")


@app.post("/checkout")
async def checkout(
    request: Request,
    x_correlation_id: Optional[str] = Header(None, alias="X-Correlation-ID"),
):
    """
    Simulate checkout flow: create order + payment.
    
    Demonstrates distributed trace across gateway → orders → payments.
    """
    correlation_id = x_correlation_id or request.headers.get("x-correlation-id", "none")
    logger.info("Processing checkout", extra={"correlation_id": correlation_id})
    
    with tracer.start_as_current_span("gateway.checkout") as span:
        span.set_attribute("correlation_id", correlation_id)
        
        # Create order
        with business_spans.http_call("POST", f"{ORDERS_URL}/orders", "orders") as order_span:
            order_span.set_attribute("correlation_id", correlation_id)
            try:
                order_response = await http_client.post(f"{ORDERS_URL}/orders", json={})
                order_span.set_attribute("http.status_code", order_response.status_code)
                
                if order_response.status_code != 201:
                    raise HTTPException(status_code=500, detail="Failed to create order")
                    
                order_data = order_response.json()
                order_id = order_data.get("order_id")
                span.set_attribute("order_id", order_id)
                
            except httpx.RequestError as e:
                logger.error("Failed to create order", extra={"error": str(e)})
                span.set_status(StatusCode.ERROR, str(e))
                span.record_exception(e)
                raise HTTPException(status_code=503, detail="Orders service unavailable")
        
        # Process payment
        with business_spans.http_call("POST", f"{PAYMENTS_URL}/payments", "payments") as payment_span:
            payment_span.set_attribute("correlation_id", correlation_id)
            payment_span.set_attribute("order_id", order_id)
            
            try:
                payment_response = await http_client.post(
                    f"{PAYMENTS_URL}/payments",
                    json={"order_id": order_id, "amount": 99.99}
                )
                payment_span.set_attribute("http.status_code", payment_response.status_code)
                
                if payment_response.status_code != 201:
                    raise HTTPException(status_code=500, detail="Failed to process payment")
                    
                payment_data = payment_response.json()
                payment_id = payment_data.get("payment_id")
                span.set_attribute("payment_id", payment_id)
                
            except httpx.RequestError as e:
                logger.error("Failed to process payment", extra={"error": str(e)})
                span.set_status(StatusCode.ERROR, str(e))
                span.record_exception(e)
                raise HTTPException(status_code=503, detail="Payments service unavailable")
        
        logger.info("Checkout completed", extra={
            "correlation_id": correlation_id,
            "order_id": order_id,
            "payment_id": payment_id
        })
        
        return {
            "checkout_id": f"chk_{order_id}_{payment_id}",
            "order_id": order_id,
            "payment_id": payment_id,
            "status": "completed"
        }


@app.get("/fibonacci")
async def fibonacci(n: int = Query(..., ge=0, le=90)):
    result = compute_fibonacci(n)
    return {"n": n, "result": result}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)