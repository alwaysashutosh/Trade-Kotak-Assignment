from dataclasses import dataclass
from enum import Enum
from typing import Optional
import uuid
from datetime import datetime

class OrderStatus(Enum):
    PENDING = "pending"
    TRIGGER_PENDING = "trigger_pending"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    TARGET = "TARGET"

class TradeSide(Enum):
    BUY = "BUY"
    SELL = "SELL"

@dataclass
class Order:
    order_id: str
    symbol: str
    order_type: OrderType
    side: TradeSide
    quantity: int
    price: Optional[float] = None
    trigger_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    average_price: Optional[float] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.order_id is None:
            self.order_id = str(uuid.uuid4())

@dataclass
class Trade:
    trade_id: str
    symbol: str
    side: TradeSide
    quantity: int
    entry_price: float
    stop_loss_points: float
    target_points: float
    market_order: Order
    stop_loss_order: Order
    target_order: Order
    created_at: datetime = None
    active: bool = True
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.trade_id is None:
            self.trade_id = str(uuid.uuid4())

@dataclass
class MarketData:
    symbol: str
    ltp: float
    change: float
    change_percent: float
    volume: int
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

@dataclass
class TradeResult:
    success: bool
    message: str
    trade_id: Optional[str] = None
    order_ids: Optional[list] = None