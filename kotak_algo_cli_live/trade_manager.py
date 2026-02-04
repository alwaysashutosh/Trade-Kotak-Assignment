import asyncio
from typing import Dict, List, Optional, Any
from .trade import TradeExecutor
from .models import Trade, TradeResult, TradeSide
import logging

logger = logging.getLogger(__name__)

class TradeManager:
    def __init__(self, trade_executor: TradeExecutor):
        self.trade_executor = trade_executor
        self.active_trades: Dict[str, Trade] = {}
        self.trade_lock = asyncio.Lock()
        self.ltp_streams: Dict[str, asyncio.Task] = {}
        self.stream_lock = asyncio.Lock()
        
    async def execute_new_trade(self, 
                              symbol: str, 
                              side: TradeSide, 
                              quantity: int, 
                              entry_price: float,
                              stop_loss_points: float, 
                              target_points: float) -> TradeResult:
        async with self.trade_lock:
            result = await self.trade_executor.execute_trade(
                symbol, side, quantity, entry_price, stop_loss_points, target_points
            )
            if result.success and result.trade_id:
                logger.info(f"Started trade {result.trade_id} for {symbol}")
            return result
    
    async def add_active_trade(self, trade: Trade):
        async with self.trade_lock:
            self.active_trades[trade.trade_id] = trade
            logger.info(f"Added trade {trade.trade_id} to active trades")
    
    async def remove_active_trade(self, trade_id: str):
        async with self.trade_lock:
            if trade_id in self.active_trades:
                del self.active_trades[trade_id]
                logger.info(f"Removed trade {trade_id} from active trades")
    
    async def get_active_trades_count(self) -> int:
        async with self.trade_lock:
            return len(self.active_trades)
    
    async def get_active_trades(self) -> List[Trade]:
        async with self.trade_lock:
            return list(self.active_trades.values())
    
    async def cancel_trade(self, trade_id: str) -> bool:
        result = await self.trade_executor.cancel_trade_orders(trade_id)
        if result:
            await self.remove_active_trade(trade_id)
        return result
    
    async def cancel_all_trades(self):
        async with self.trade_lock:
            trade_ids = list(self.active_trades.keys())
        for trade_id in trade_ids:
            await self.cancel_trade(trade_id)
    
    async def start_ltp_stream_for_symbol(self, symbol: str, callback_func):
        async with self.stream_lock:
            if symbol in self.ltp_streams:
                self.ltp_streams[symbol].cancel()
                try:
                    await self.ltp_streams[symbol]
                except asyncio.CancelledError:
                    pass
            stream_task = asyncio.create_task(
                self._run_ltp_stream(symbol, callback_func)
            )
            self.ltp_streams[symbol] = stream_task
    
    async def _run_ltp_stream(self, symbol: str, callback_func):
        try:
            await self.trade_executor.client.start_ltp_stream(symbol, callback_func)
        except Exception as e:
            logger.error(f"Error in LTP stream for {symbol}: {str(e)}")
    
    async def stop_ltp_stream_for_symbol(self, symbol: str):
        async with self.stream_lock:
            if symbol in self.ltp_streams:
                self.ltp_streams[symbol].cancel()
                try:
                    await self.ltp_streams[symbol]
                except asyncio.CancelledError:
                    pass
                del self.ltp_streams[symbol]
    
    async def stop_all_ltp_streams(self):
        async with self.stream_lock:
            symbols = list(self.ltp_streams.keys())
        for symbol in symbols:
            await self.stop_ltp_stream_for_symbol(symbol)
    
    async def get_overall_status(self) -> Dict[str, Any]:
        active_count = await self.get_active_trades_count()
        active_trades = await self.get_active_trades()
        return {
            'total_active_trades': active_count,
            'trades': [
                {
                    'trade_id': trade.trade_id,
                    'symbol': trade.symbol,
                    'side': trade.side.value,
                    'quantity': trade.quantity,
                    'entry_price': trade.entry_price,
                    'active': trade.active
                } for trade in active_trades
            ]
        }
    
    async def cleanup(self):
        logger.info("Cleaning up trade manager resources...")
        await self.cancel_all_trades()
        await self.stop_all_ltp_streams()
        logger.info("Trade manager cleanup completed")

class SingletonTradeManager:
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SingletonTradeManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not SingletonTradeManager._initialized:
            self.manager: Optional[TradeManager] = None
            SingletonTradeManager._initialized = True
    
    def set_manager(self, manager: TradeManager):
        self.manager = manager
    
    def get_manager(self) -> Optional[TradeManager]:
        return self.manager

trade_manager_singleton = SingletonTradeManager()