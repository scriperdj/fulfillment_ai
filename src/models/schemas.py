"""
Pydantic models and schemas for fulfillment_ai
Request/response validation
"""

from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class OrderBase(BaseModel):
    """Base order model"""
    order_id: str
    order_date: datetime
    ship_date: Optional[datetime] = None
    segment: str
    region: str
    product_category: str


class OrderCreate(OrderBase):
    """Create order request"""
    pass


class Order(OrderBase):
    """Order response"""
    status: str
    predicted_delay: Optional[float] = None
    risk_score: Optional[float] = None

    class Config:
        from_attributes = True


class KPIData(BaseModel):
    """KPI response"""
    metric_name: str
    value: float
    threshold: Optional[float] = None
    timestamp: datetime


class DeviationBase(BaseModel):
    """Base deviation model"""
    order_id: str
    deviation_type: str
    severity: str  # critical, warning, info
    reason: str


class DeviationCreate(DeviationBase):
    """Create deviation request"""
    pass


class Deviation(DeviationBase):
    """Deviation response"""
    id: str
    created_at: datetime
    status: str

    class Config:
        from_attributes = True


class AgentRequestBase(BaseModel):
    """Base agent request"""
    order_id: str
    deviation_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class AgentRequest(AgentRequestBase):
    """Agent request response"""
    id: str
    status: str
    created_at: datetime


class AgentResponse(BaseModel):
    """Agent response model"""
    id: str
    request_id: str
    status: str
    resolution_type: str  # email_draft, refund, reschedule
    output: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    version: str
