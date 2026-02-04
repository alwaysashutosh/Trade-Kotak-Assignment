import asyncio
from typing import Optional, Dict, Any
from .client import KotakNeoClient
from .models import Trade, Order, OrderType, OrderStatus, TradeSide, TradeResult
import logging

logger = logging.getLogger(__name__)

class TradeExecutor:
    def __init__(self, client: KotakNeoClient):
        self.client = client
        self.active_orders: Dict[str, asyncio.Task] = {}
        self.trade_locks: Dict[str, asyncio.Lock] = {}
        
    async def execute_trade(self, 
                          symbol: str, 
                          side: TradeSide, 
                          quantity: int, 
                          entry_price: float,
                          stop_loss_points: float, 
                          target_points: float) -> TradeResult:
        try:
            if side == TradeSide.BUY:
                stop_loss_price = entry_price - stop_loss_points
                target_price = entry_price + target_points
            else:
                stop_loss_price = entry_price + stop_loss_points
                target_price = entry_price - target_points
            market_order = Order(
                order_id=None,
                symbol=symbol,
                order_type=OrderType.MARKET,
                side=side,
                quantity=quantity,
                price=entry_price
            )
            opposite_side = TradeSide.SELL if side == TradeSide.BUY else TradeSide.BUY
            stop_loss_order = Order(
                order_id=None,
                symbol=symbol,
                order_type=OrderType.STOP_LOSS,
                side=opposite_side,
                quantity=quantity,
                trigger_price=stop_loss_price,
                price=stop_loss_price
            )
            target_order = Order(
                order_id=None,
                symbol=symbol,
                order_type=OrderType.TARGET,
                side=opposite_side,
                quantity=quantity,
                trigger_price=target_price,
                price=target_price
            )
            market_order_id = await self.client.place_order(market_order)
            if not market_order_id:
                return TradeResult(success=False, message="Failed to place market order")
            market_order.order_id = market_order_id
            await asyncio.sleep(0.5)
            sl_order_id = await self.client.place_order(stop_loss_order)
            if not sl_order_id:
                return TradeResult(success=False, message="Failed to place stop loss order")
            stop_loss_order.order_id = sl_order_id
            target_order_id = await self.client.place_order(target_order)
            if not target_order_id:
                return TradeResult(success=False, message="Failed to place target order")
            target_order.order_id = target_order_id
            trade = Trade(
                trade_id=None,
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
        self.trade_locks[trade.trade_id] = asyncio.Lock()
        monitoring_task = asyncio.create_task(
            self._monitor_oco_orders(trade)
        )
        self.active_orders[trade.trade_id] = monitoring_task
        monitoring_task.add_done_callback(
            lambda t: self._cleanup_trade_resources(trade.trade_id)
        )
    
    async def _monitor_oco_orders(self, trade: Trade):
        logger.info(f"Starting order monitoring for trade {trade.trade_id}")
        while trade.active:
            sl_status = await self.client.get_order_status(trade.stop_loss_order.order_id)
            target_status = await self.client.get_order_status(trade.target_order.order_id)
            if sl_status is None or target_status is None:
                await asyncio.sleep(1)
                continue
            if sl_status.get('status') in ['COMPLETE', 'FILLED', 'EXECUTED']:
                logger.info(f"Stop loss order {trade.stop_loss_order.order_id} filled for trade {trade.trade_id}")
                if target_status.get('status') in ['PENDING', 'TRIGGER_PENDING', 'OPEN']:
                    cancel_result = await self.client.cancel_order(trade.target_order.order_id)
                    if cancel_result:
                        logger.info(f"Target order {trade.target_order.order_id} cancelled due to SL fill for trade {trade.trade_id}")
                    else:
                        logger.warning(f"Failed to cancel target order {trade.target_order.order_id}")
                trade.active = False
                break
            elif target_status.get('status') in ['COMPLETE', 'FILLED', 'EXECUTED']:
                logger.info(f"Target order {trade.target_order.order_id} filled for trade {trade.trade_id}")
                if sl_status.get('status') in ['PENDING', 'TRIGGER_PENDING', 'OPEN']:
                    cancel_result = await self.client.cancel_order(trade.stop_loss_order.order_id)
                    if cancel_result:
                        logger.info(f"Stop loss order {trade.stop_loss_order.order_id} cancelled due to target fill for trade {trade.trade_id}")
                    else:
                        logger.warning(f"Failed to cancel stop loss order {trade.stop_loss_order.order_id}")
                trade.active = False
                break
            await asyncio.sleep(1)
        logger.info(f"Order monitoring ended for trade {trade.trade_id}")
    
    def _cleanup_trade_resources(self, trade_id: str):
        if trade_id in self.active_orders:
            del self.active_orders[trade_id]
        if trade_id in self.trade_locks:
            del self.trade_locks[trade_id]
        logger.info(f"Cleaned up resources for trade {trade_id}")
    
    async def cancel_trade_orders(self, trade_id: str) -> bool:
        if trade_id in self.active_orders:
            task = self.active_orders[trade_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        return True
    
    async def get_trade_status(self, trade_id: str) -> Optional[Dict[str, Any]]:
        if trade_id not in self.active_orders:
            return None
        return {
            'trade_id': trade_id,
            'active': True,
            'status': 'MONITORING'
        }