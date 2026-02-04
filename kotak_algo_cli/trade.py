import asyncio
from typing import Optional, Dict, Any
try:
    from .client import KotakNeoClient
    from .models import Trade, Order, OrderType, OrderStatus, TradeSide, TradeResult
except ImportError:
    # Fallback for direct execution
    from client import KotakNeoClient
    from models import Trade, Order, OrderType, OrderStatus, TradeSide, TradeResult
import logging

logger = logging.getLogger(__name__)


class TradeExecutor:
    """
    Handles trade execution with OCO (One-Cancels-Other) logic.
    Places market orders along with stop-loss and target orders,
    and manages the OCO behavior where if one order executes,
    the other gets cancelled.
    """
    
    def __init__(self, client: KotakNeoClient):
        """
        Initialize the trade executor.
        
        Args:
            client: KotakNeoClient instance for API operations
        """
        self.client = client
        self.active_orders: Dict[str, asyncio.Task] = {}  # Track active monitoring tasks
        self.trade_locks: Dict[str, asyncio.Lock] = {}  # Per-trade locks
        
    async def execute_trade(self, 
                          symbol: str, 
                          side: TradeSide, 
                          quantity: int, 
                          entry_price: float,
                          stop_loss_points: float, 
                          target_points: float) -> TradeResult:
        """
        Execute a trade with OCO orders.
        
        Args:
            symbol: Trading symbol
            side: Trade side (BUY/SELL)
            quantity: Number of shares/contracts
            entry_price: Entry price for the trade
            stop_loss_points: Points for stop loss from entry
            target_points: Points for target from entry
            
        Returns:
            TradeResult: Result of the trade execution
        """
        try:
            # Calculate stop loss and target prices based on entry price
            if side == TradeSide.BUY:
                stop_loss_price = entry_price - stop_loss_points
                target_price = entry_price + target_points
            else:  # SELL
                stop_loss_price = entry_price + stop_loss_points
                target_price = entry_price - target_points
            
            # Create orders
            market_order = Order(
                order_id=None,  # Will be assigned by API
                symbol=symbol,
                order_type=OrderType.MARKET,
                side=side,
                quantity=quantity,
                price=entry_price
            )
            
            # Determine the opposite side for exit orders
            opposite_side = TradeSide.SELL if side == TradeSide.BUY else TradeSide.BUY
            
            stop_loss_order = Order(
                order_id=None,
                symbol=symbol,
                order_type=OrderType.STOP_LOSS,
                side=opposite_side,  # Opposite side for exit orders
                quantity=quantity,
                trigger_price=stop_loss_price,
                price=stop_loss_price  # For stop loss market orders
            )
            
            target_order = Order(
                order_id=None,
                symbol=symbol,
                order_type=OrderType.TARGET,
                side=opposite_side,  # Opposite side for exit orders
                quantity=quantity,
                trigger_price=target_price,
                price=target_price
            )
            
            # Place the market order first
            market_order_id = await self.client.place_order(market_order)
            if not market_order_id:
                return TradeResult(success=False, message="Failed to place market order")
            
            market_order.order_id = market_order_id
            
            # Wait briefly to ensure market order is processed
            await asyncio.sleep(0.5)
            
            # Place stop loss order
            sl_order_id = await self.client.place_order(stop_loss_order)
            if not sl_order_id:
                return TradeResult(success=False, message="Failed to place stop loss order")
            
            stop_loss_order.order_id = sl_order_id
            
            # Place target order
            target_order_id = await self.client.place_order(target_order)
            if not target_order_id:
                return TradeResult(success=False, message="Failed to place target order")
            
            target_order.order_id = target_order_id
            
            # Create the trade object
            trade = Trade(
                trade_id=None,  # Will be auto-generated
                symbol=symbol,
                side=side,
                quantity=quantity,
                entry_price=entry_price,
                stop_loss_points=stop_loss_points,
                target_points=target_points,
                market_order=market_order,
                stop_loss_order=stop_loss_order,
                target_order=target_order
            )
            
            # Start monitoring the orders in the background
            await self.start_order_monitoring(trade)
            
            return TradeResult(
                success=True,
                message=f"Trade placed successfully. Orders: {market_order_id}, SL: {sl_order_id}, Target: {target_order_id}",
                trade_id=trade.trade_id,
                order_ids=[market_order_id, sl_order_id, target_order_id]
            )
            
        except Exception as e:
            logger.error(f"Error executing trade for {symbol}: {str(e)}")
            return TradeResult(success=False, message=f"Error executing trade: {str(e)}")
    
    async def start_order_monitoring(self, trade: Trade):
        """
        Start monitoring orders in the background with OCO logic.
        
        Args:
            trade: Trade object containing the orders to monitor
        """
        # Create a lock for this trade to protect shared state
        self.trade_locks[trade.trade_id] = asyncio.Lock()
        
        # Create a task to monitor the stop loss and target orders
        monitoring_task = asyncio.create_task(
            self._monitor_oco_orders(trade)
        )
        
        # Store the monitoring task
        self.active_orders[trade.trade_id] = monitoring_task
        
        # Handle task completion
        monitoring_task.add_done_callback(
            lambda t: self._cleanup_trade_resources(trade.trade_id)
        )
    
    async def _monitor_oco_orders(self, trade: Trade):
        """
        Monitor stop loss and target orders with OCO logic.
        
        Args:
            trade: Trade object to monitor
        """
        logger.info(f"Starting order monitoring for trade {trade.trade_id}")
        
        # Continue monitoring until both orders are filled or cancelled
        while trade.active:
            # Check if both orders are completed (either filled or cancelled)
            sl_status = await self.client.get_order_status(trade.stop_loss_order.order_id)
            target_status = await self.client.get_order_status(trade.target_order.order_id)
            
            # If we couldn't get status, continue monitoring
            if sl_status is None or target_status is None:
                await asyncio.sleep(1)  # Poll every second
                continue
            
            # Check if stop loss order is filled
            if sl_status.get('status') in ['COMPLETE', 'FILLED', 'EXECUTED']:
                logger.info(f"Stop loss order {trade.stop_loss_order.order_id} filled for trade {trade.trade_id}")
                
                # Cancel the target order (OCO logic)
                if target_status.get('status') in ['PENDING', 'TRIGGER_PENDING', 'OPEN']:
                    cancel_result = await self.client.cancel_order(trade.target_order.order_id)
                    if cancel_result:
                        logger.info(f"Target order {trade.target_order.order_id} cancelled due to SL fill for trade {trade.trade_id}")
                    else:
                        logger.warning(f"Failed to cancel target order {trade.target_order.order_id}")
                
                # Mark trade as inactive
                trade.active = False
                break
            
            # Check if target order is filled
            elif target_status.get('status') in ['COMPLETE', 'FILLED', 'EXECUTED']:
                logger.info(f"Target order {trade.target_order.order_id} filled for trade {trade.trade_id}")
                
                # Cancel the stop loss order (OCO logic)
                if sl_status.get('status') in ['PENDING', 'TRIGGER_PENDING', 'OPEN']:
                    cancel_result = await self.client.cancel_order(trade.stop_loss_order.order_id)
                    if cancel_result:
                        logger.info(f"Stop loss order {trade.stop_loss_order.order_id} cancelled due to target fill for trade {trade.trade_id}")
                    else:
                        logger.warning(f"Failed to cancel stop loss order {trade.stop_loss_order.order_id}")
                
                # Mark trade as inactive
                trade.active = False
                break
            
            # Continue monitoring
            await asyncio.sleep(1)  # Poll every second
        
        logger.info(f"Order monitoring ended for trade {trade.trade_id}")
    
    def _cleanup_trade_resources(self, trade_id: str):
        """
        Clean up resources associated with a completed trade.
        
        Args:
            trade_id: ID of the trade to clean up
        """
        # Remove the monitoring task
        if trade_id in self.active_orders:
            del self.active_orders[trade_id]
        
        # Remove the trade lock
        if trade_id in self.trade_locks:
            del self.trade_locks[trade_id]
        
        logger.info(f"Cleaned up resources for trade {trade_id}")
    
    async def cancel_trade_orders(self, trade_id: str) -> bool:
        """
        Cancel all orders associated with a trade.
        
        Args:
            trade_id: ID of the trade to cancel
            
        Returns:
            bool: True if cancellation successful, False otherwise
        """
        # Get the monitoring task if it exists
        if trade_id in self.active_orders:
            task = self.active_orders[trade_id]
            task.cancel()
            
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Note: In a real implementation, you'd also need to keep references to order IDs
        # to cancel them individually via the API. This is a simplified approach.
        
        return True
    
    async def get_trade_status(self, trade_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a specific trade.
        
        Args:
            trade_id: ID of the trade to check
            
        Returns:
            Optional[Dict]: Trade status information or None if not found
        """
        if trade_id not in self.active_orders:
            return None
        
        # Check the status of individual orders
        # This would require keeping more state in a real implementation
        return {
            'trade_id': trade_id,
            'active': True,  # Simplified - would check actual order statuses in real implementation
            'status': 'MONITORING'
        }

