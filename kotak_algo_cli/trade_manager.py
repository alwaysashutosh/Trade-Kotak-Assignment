import asyncio
from typing import Dict, List, Optional, Any
try:
    from .trade import TradeExecutor
    from .models import Trade, TradeResult, TradeSide
except ImportError:
    # Fallback for direct execution
    from trade import TradeExecutor
    from models import Trade, TradeResult, TradeSide
import logging

logger = logging.getLogger(__name__)


class TradeManager:
    """
    Manages multiple concurrent trades with thread-safe operations.
    Tracks active trades, handles concurrent execution, and provides
    status monitoring across all active trades.
    """
    
    def __init__(self, trade_executor: TradeExecutor):
        """
        Initialize the trade manager.
        
        Args:
            trade_executor: TradeExecutor instance for executing trades
        """
        self.trade_executor = trade_executor
        self.active_trades: Dict[str, Trade] = {}
        self.trade_lock = asyncio.Lock()  # Global lock for trade operations
        self.ltp_streams: Dict[str, asyncio.Task] = {}  # Track active LTP streams
        self.stream_lock = asyncio.Lock()  # Lock for stream operations
        
    async def execute_new_trade(self, 
                              symbol: str, 
                              side: TradeSide, 
                              quantity: int, 
                              entry_price: float,
                              stop_loss_points: float, 
                              target_points: float) -> TradeResult:
        """
        Execute a new trade and add it to the active trades list.
        
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
        async with self.trade_lock:
            result = await self.trade_executor.execute_trade(
                symbol, side, quantity, entry_price, stop_loss_points, target_points
            )
            
            if result.success and result.trade_id:
                # We would need to maintain the trade object in a real implementation
                # For now, we'll just log that the trade was started
                logger.info(f"Started trade {result.trade_id} for {symbol}")
            
            return result
    
    async def add_active_trade(self, trade: Trade):
        """
        Add a trade to the active trades list.
        
        Args:
            trade: Trade object to add
        """
        async with self.trade_lock:
            self.active_trades[trade.trade_id] = trade
            logger.info(f"Added trade {trade.trade_id} to active trades")
    
    async def remove_active_trade(self, trade_id: str):
        """
        Remove a trade from the active trades list.
        
        Args:
            trade_id: ID of the trade to remove
        """
        async with self.trade_lock:
            if trade_id in self.active_trades:
                del self.active_trades[trade_id]
                logger.info(f"Removed trade {trade_id} from active trades")
    
    async def get_active_trades_count(self) -> int:
        """
        Get the number of currently active trades.
        
        Returns:
            int: Number of active trades
        """
        async with self.trade_lock:
            return len(self.active_trades)
    
    async def get_active_trades(self) -> List[Trade]:
        """
        Get a list of all active trades.
        
        Returns:
            List[Trade]: List of active trade objects
        """
        async with self.trade_lock:
            return list(self.active_trades.values())
    
    async def cancel_trade(self, trade_id: str) -> bool:
        """
        Cancel a specific trade by cancelling its orders.
        
        Args:
            trade_id: ID of the trade to cancel
            
        Returns:
            bool: True if cancellation successful, False otherwise
        """
        # Cancel the orders via the trade executor
        result = await self.trade_executor.cancel_trade_orders(trade_id)
        
        if result:
            # Remove from active trades
            await self.remove_active_trade(trade_id)
        
        return result
    
    async def cancel_all_trades(self):
        """
        Cancel all active trades.
        """
        async with self.trade_lock:
            trade_ids = list(self.active_trades.keys())
            
        for trade_id in trade_ids:
            await self.cancel_trade(trade_id)
    
    async def start_ltp_stream_for_symbol(self, symbol: str, callback_func):
        """
        Start an LTP stream for a specific symbol.
        
        Args:
            symbol: Symbol to stream LTP for
            callback_func: Function to call with each update
        """
        async with self.stream_lock:
            if symbol in self.ltp_streams:
                # Cancel existing stream if running
                self.ltp_streams[symbol].cancel()
                try:
                    await self.ltp_streams[symbol]
                except asyncio.CancelledError:
                    pass
            
            # Create a new stream task
            stream_task = asyncio.create_task(
                self._run_ltp_stream(symbol, callback_func)
            )
            self.ltp_streams[symbol] = stream_task
    
    async def _run_ltp_stream(self, symbol: str, callback_func):
        """
        Internal method to run the LTP stream.
        
        Args:
            symbol: Symbol to stream LTP for
            callback_func: Function to call with each update
        """
        try:
            await self.trade_executor.client.start_ltp_stream(symbol, callback_func)
        except Exception as e:
            logger.error(f"Error in LTP stream for {symbol}: {str(e)}")
    
    async def stop_ltp_stream_for_symbol(self, symbol: str):
        """
        Stop the LTP stream for a specific symbol.
        
        Args:
            symbol: Symbol to stop streaming for
        """
        async with self.stream_lock:
            if symbol in self.ltp_streams:
                self.ltp_streams[symbol].cancel()
                try:
                    await self.ltp_streams[symbol]
                except asyncio.CancelledError:
                    pass
                
                del self.ltp_streams[symbol]
    
    async def stop_all_ltp_streams(self):
        """
        Stop all active LTP streams.
        """
        async with self.stream_lock:
            symbols = list(self.ltp_streams.keys())
            
        for symbol in symbols:
            await self.stop_ltp_stream_for_symbol(symbol)
    
    async def get_overall_status(self) -> Dict[str, Any]:
        """
        Get the overall status of all managed trades.
        
        Returns:
            Dict: Status information about all trades
        """
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
        """
        Clean up all resources before shutdown.
        """
        logger.info("Cleaning up trade manager resources...")
        
        # Cancel all active trades
        await self.cancel_all_trades()
        
        # Stop all LTP streams
        await self.stop_all_ltp_streams()
        
        logger.info("Trade manager cleanup completed")


class SingletonTradeManager:
    """
    Singleton wrapper for TradeManager to ensure single instance across the application.
    """
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
        """
        Set the trade manager instance.
        
        Args:
            manager: TradeManager instance
        """
        self.manager = manager
    
    def get_manager(self) -> Optional[TradeManager]:
        """
        Get the trade manager instance.
        
        Returns:
            Optional[TradeManager]: The trade manager instance or None
        """
        return self.manager

# Global singleton instance
trade_manager_singleton = SingletonTradeManager()