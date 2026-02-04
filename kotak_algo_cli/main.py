import asyncio
import sys
import signal
from typing import Optional
try:
    from .client import KotakNeoClient
    from .market_data import MarketDataStream
    from .trade import TradeExecutor
    from .trade_manager import TradeManager, trade_manager_singleton
    from .models import TradeSide
    from .utils import (
        validate_symbol, validate_quantity, validate_positive_float, 
        parse_trade_side, print_error, print_success, print_info,
        format_symbol_display
    )
except ImportError:
    # Fallback for direct execution
    from client import KotakNeoClient
    from market_data import MarketDataStream
    from trade import TradeExecutor
    from trade_manager import TradeManager, trade_manager_singleton
    from models import TradeSide
    from utils import (
        validate_symbol, validate_quantity, validate_positive_float, 
        parse_trade_side, print_error, print_success, print_info,
        format_symbol_display
    )
import logging

logger = logging.getLogger(__name__)


class KotakAlgoCLI:
    """
    Main CLI class that orchestrates the trading system.
    Handles user input, market data streaming, and trade execution.
    """
    
    def __init__(self):
        """Initialize the CLI application."""
        self.client: Optional[KotakNeoClient] = None
        self.market_stream: Optional[MarketDataStream] = None
        self.trade_executor: Optional[TradeExecutor] = None
        self.trade_manager: Optional[TradeManager] = None
        self.running = True
        self.current_symbol = None
        
    async def initialize(self):
        """Initialize all components of the trading system."""
        print_info("Initializing Kotak Neo Trading CLI...")
        
        # Initialize the API client with credentials
        # In a real implementation, these would come from environment/config
        try:
            # For demo purposes, using placeholder credentials
            # In production, these should be loaded securely
            self.client = KotakNeoClient(
                consumer_key="KOTAK_CONSUMER_KEY",
                consumer_secret="KOTAK_CONSUMER_SECRET", 
                mobile_number="KOTAK_MOBILE",
                password="KOTAK_PASSWORD"
            )
            
            # Authenticate with the API
            auth_success = await self.client.authenticate()
            if not auth_success:
                print_error("Failed to authenticate with Kotak Neo API")
                return False
                
            print_success("Successfully authenticated with Kotak Neo API")
            
            # Initialize market data streamer
            self.market_stream = MarketDataStream(self.client)
            
            # Initialize trade executor
            self.trade_executor = TradeExecutor(self.client)
            
            # Initialize trade manager
            self.trade_manager = TradeManager(self.trade_executor)
            
            # Register the trade manager with the singleton
            trade_manager_singleton.set_manager(self.trade_manager)
            
            print_success("All components initialized successfully")
            return True
            
        except Exception as e:
            print_error(f"Error initializing trading system: {str(e)}")
            return False
    
    async def run(self):
        """Main application loop."""
        print_info("Welcome to Kotak Neo Trading CLI!")
        print_info("Press Ctrl+C to exit the application")
        
        # Set up signal handler for graceful shutdown
        def signal_handler(signum, frame):
            print("\nReceived interrupt signal. Shutting down...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        
        try:
            while self.running:
                # Get symbol from user
                symbol = await self.get_symbol_input()
                if not symbol:
                    continue
                
                # Start LTP stream for the symbol
                await self.start_ltp_stream(symbol)
                
                # Get trade parameters from user
                trade_params = await self.get_trade_parameters()
                if not trade_params:
                    await self.stop_ltp_stream()
                    continue
                
                # Execute the trade
                await self.execute_trade(symbol, *trade_params)
                
                # Stop the LTP stream after trade execution
                await self.stop_ltp_stream()
                
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            await self.shutdown()
    
    async def get_symbol_input(self) -> Optional[str]:
        """Prompt user for trading symbol."""
        while self.running:
            try:
                symbol_input = input("\nWhich symbol to enter? (or 'quit' to exit): ").strip().upper()
                
                if symbol_input.lower() in ['quit', 'exit', 'q']:
                    self.running = False
                    return None
                
                if validate_symbol(symbol_input):
                    return symbol_input
                else:
                    print_error("Invalid symbol format. Please enter a valid symbol (e.g., RELIANCE).")
            except EOFError:
                # Handle case where input stream is closed
                self.running = False
                return None
    
    async def start_ltp_stream(self, symbol: str):
        """Start live LTP stream for the given symbol."""
        self.current_symbol = symbol
        
        # Create a task for the LTP stream
        self.ltp_task = asyncio.create_task(
            self.market_stream.start_ltp_stream(
                symbol, 
                update_callback=self.on_ltp_update
            )
        )
    
    async def stop_ltp_stream(self):
        """Stop the current LTP stream."""
        if hasattr(self, 'ltp_task'):
            self.ltp_task.cancel()
            try:
                await self.ltp_task
            except asyncio.CancelledError:
                pass
        
        await self.market_stream.stop_ltp_stream()
        self.current_symbol = None
    
    async def on_ltp_update(self, market_data):
        """Callback for LTP updates."""
        # This is called by the market stream, but we don't need to do anything special here
        # The market stream already handles the display
        pass
    
    async def get_trade_parameters(self) -> Optional[tuple]:
        """Prompt user for trade parameters."""
        try:
            # Get trade side
            while True:
                side_input = input("B/S (Buy/Sell): ").strip().upper()
                side = parse_trade_side(side_input)
                if side:
                    break
                else:
                    print_error("Invalid input. Please enter 'B' for Buy or 'S' for Sell.")
            
            # Get quantity
            while True:
                quantity_input = input("Quantity: ").strip()
                quantity = validate_quantity(quantity_input)
                if quantity:
                    break
                else:
                    print_error("Invalid quantity. Please enter a positive integer.")
            
            # Get stop loss points
            while True:
                sl_input = input("SL points: ").strip()
                sl_points = validate_positive_float(sl_input)
                if sl_points is not None:
                    break
                else:
                    print_error("Invalid SL points. Please enter a positive number.")
            
            # Get target points
            while True:
                target_input = input("Target points: ").strip()
                target_points = validate_positive_float(target_input)
                if target_points is not None:
                    break
                else:
                    print_error("Invalid target points. Please enter a positive number.")
            
            # Get current LTP as entry price
            current_ltp = await self.market_stream.get_current_ltp_for_symbol(self.current_symbol)
            if current_ltp is None:
                print_error("Could not get current LTP. Cannot proceed with trade.")
                return None
            
            return side, quantity, current_ltp, sl_points, target_points
            
        except EOFError:
            # Handle case where input stream is closed
            return None
    
    async def execute_trade(self, symbol: str, side: TradeSide, quantity: int, 
                           entry_price: float, sl_points: float, target_points: float):
        """Execute a trade with the given parameters."""
        print_info(f"Executing trade: {symbol} {side.value} {quantity} @ {entry_price}")
        print_info(f"SL: {sl_points}, Target: {target_points}")
        
        # Execute the trade via the trade manager
        result = await self.trade_manager.execute_new_trade(
            symbol, side, quantity, entry_price, sl_points, target_points
        )
        
        if result.success:
            print_success(result.message)
        else:
            print_error(result.message)
    
    async def shutdown(self):
        """Gracefully shut down the application."""
        print_info("Shutting down Kotak Neo Trading CLI...")
        
        # Stop the LTP stream if running
        if self.market_stream:
            await self.market_stream.stop_ltp_stream()
        
        # Clean up trade manager resources
        if self.trade_manager:
            await self.trade_manager.cleanup()
        
        print_info("Application shut down successfully")


async def main():
    """Entry point for the application."""
    cli = KotakAlgoCLI()
    
    # Initialize the application
    init_success = await cli.initialize()
    if not init_success:
        print_error("Failed to initialize the application. Exiting.")
        sys.exit(1)
    
    # Run the application
    await cli.run()


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())