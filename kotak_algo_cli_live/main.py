import asyncio
import sys
import signal
from typing import Optional
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
import logging

logger = logging.getLogger(__name__)

class KotakAlgoCLI:
    def __init__(self):
        self.client: Optional[KotakNeoClient] = None
        self.market_stream: Optional[MarketDataStream] = None
        self.trade_executor: Optional[TradeExecutor] = None
        self.trade_manager: Optional[TradeManager] = None
        self.running = True
        self.current_symbol = None
        
    async def initialize(self):
        print_info("Initializing Kotak Neo Trading CLI...")
        try:
            self.client = KotakNeoClient()
            auth_success = await self.client.authenticate()
            if not auth_success:
                print_error("Failed to authenticate with Kotak Neo API")
                return False
            print_success("Successfully authenticated with Kotak Neo API")
            self.market_stream = MarketDataStream(self.client)
            self.trade_executor = TradeExecutor(self.client)
            self.trade_manager = TradeManager(self.trade_executor)
            trade_manager_singleton.set_manager(self.trade_manager)
            print_success("All components initialized successfully")
            return True
        except Exception as e:
            print_error(f"Error initializing trading system: {str(e)}")
            return False
    
    async def run(self):
        print_info("Welcome to Kotak Neo Trading CLI!")
        print_info("Press Ctrl+C to exit the application")
        def signal_handler(signum, frame):
            print("\nReceived interrupt signal. Shutting down...")
            self.running = False
        signal.signal(signal.SIGINT, signal_handler)
        try:
            while self.running:
                symbol = await self.get_symbol_input()
                if not symbol:
                    continue
                await self.start_ltp_stream(symbol)
                trade_params = await self.get_trade_parameters()
                if not trade_params:
                    await self.stop_ltp_stream()
                    continue
                await self.execute_trade(symbol, *trade_params)
                await self.stop_ltp_stream()
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            await self.shutdown()
    
    async def get_symbol_input(self) -> Optional[str]:
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
                self.running = False
                return None
    
    async def start_ltp_stream(self, symbol: str):
        self.current_symbol = symbol
        self.ltp_task = asyncio.create_task(
            self.market_stream.start_ltp_stream(
                symbol, 
                update_callback=self.on_ltp_update
            )
        )
    
    async def stop_ltp_stream(self):
        if hasattr(self, 'ltp_task'):
            self.ltp_task.cancel()
            try:
                await self.ltp_task
            except asyncio.CancelledError:
                pass
        await self.market_stream.stop_ltp_stream()
        self.current_symbol = None
    
    async def on_ltp_update(self, market_data):
        pass
    
    async def get_trade_parameters(self) -> Optional[tuple]:
        try:
            while True:
                side_input = input("B/S (Buy/Sell): ").strip().upper()
                side = parse_trade_side(side_input)
                if side:
                    break
                else:
                    print_error("Invalid input. Please enter 'B' for Buy or 'S' for Sell.")
            while True:
                quantity_input = input("Quantity: ").strip()
                quantity = validate_quantity(quantity_input)
                if quantity:
                    break
                else:
                    print_error("Invalid quantity. Please enter a positive integer.")
            while True:
                sl_input = input("SL points: ").strip()
                sl_points = validate_positive_float(sl_input)
                if sl_points is not None:
                    break
                else:
                    print_error("Invalid SL points. Please enter a positive number.")
            while True:
                target_input = input("Target points: ").strip()
                target_points = validate_positive_float(target_input)
                if target_points is not None:
                    break
                else:
                    print_error("Invalid target points. Please enter a positive number.")
            current_ltp = await self.market_stream.get_current_ltp_for_symbol(self.current_symbol)
            if current_ltp is None:
                print_error("Could not get current LTP. Cannot proceed with trade.")
                return None
            return side, quantity, current_ltp, sl_points, target_points
        except EOFError:
            return None
    
    async def execute_trade(self, symbol: str, side: TradeSide, quantity: int, 
                           entry_price: float, sl_points: float, target_points: float):
        print_info(f"Executing trade: {symbol} {side.value} {quantity} @ {entry_price}")
        print_info(f"SL: {sl_points}, Target: {target_points}")
        result = await self.trade_manager.execute_new_trade(
            symbol, side, quantity, entry_price, sl_points, target_points
        )
        if result.success:
            print_success(result.message)
        else:
            print_error(result.message)
    
    async def shutdown(self):
        print_info("Shutting down Kotak Neo Trading CLI...")
        if self.market_stream:
            await self.market_stream.stop_ltp_stream()
        if self.trade_manager:
            await self.trade_manager.cleanup()
        print_info("Application shut down successfully")

async def main():
    cli = KotakAlgoCLI()
    init_success = await cli.initialize()
    if not init_success:
        print_error("Failed to initialize the application. Exiting.")
        sys.exit(1)
    await cli.run()

if __name__ == "__main__":
    asyncio.run(main())