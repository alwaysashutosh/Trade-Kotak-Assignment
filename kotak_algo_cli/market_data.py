import asyncio
import sys
from typing import Callable, Optional
try:
    from .client import KotakNeoClient
    from .models import MarketData
except ImportError:
    # Fallback for direct execution
    from client import KotakNeoClient
    from models import MarketData
import logging

logger = logging.getLogger(__name__)


class MarketDataStream:
    """
    Handles live market data streaming with real-time LTP updates.
    Uses ANSI escape codes to update a single line in place without scrolling.
    """
    
    def __init__(self, client: KotakNeoClient):
        """
        Initialize the market data stream.
        
        Args:
            client: KotakNeoClient instance for API calls
        """
        self.client = client
        self.is_streaming = False
        self.current_symbol = None
        self.last_ltp = None
        
    async def start_ltp_stream(self, symbol: str, update_callback: Optional[Callable] = None):
        """
        Start live LTP streaming for a given symbol.
        Updates a single line in place with ANSI escape codes.
        
        Args:
            symbol: Trading symbol to stream LTP for
            update_callback: Optional callback function to call with each update
        """
        self.is_streaming = True
        self.current_symbol = symbol
        last_printed_length = 0
        
        try:
            while self.is_streaming:
                ltp = await self.client.get_ltp(symbol)
                
                if ltp is not None:
                    self.last_ltp = ltp
                    
                    # Create the display string
                    display_str = f"{symbol} | LTP: {ltp:.2f}"
                    
                    # Clear the current line and move cursor to beginning
                    sys.stdout.write('\r\033[K')
                    # Print the updated line
                    sys.stdout.write(display_str)
                    sys.stdout.flush()
                    
                    # Call the callback if provided
                    if update_callback:
                        await update_callback(MarketData(
                            symbol=symbol,
                            ltp=ltp,
                            change=0.0,  # Placeholder - calculate actual change
                            change_percent=0.0,  # Placeholder - calculate actual percentage
                            volume=0  # Placeholder - get actual volume if available
                        ))
                        
                # Wait for 1 second before next update
                await asyncio.sleep(1)
                
        except asyncio.CancelledError:
            logger.info("LTP stream cancelled")
        except Exception as e:
            logger.error(f"Error in LTP stream for {symbol}: {str(e)}")
        finally:
            # Clear the line when stopping
            sys.stdout.write('\r\033[K')
            sys.stdout.flush()
    
    async def get_current_ltp_for_symbol(self, symbol: str) -> Optional[float]:
        """
        Get the current LTP for a specific symbol without starting a stream.
        
        Args:
            symbol: Trading symbol to get LTP for
            
        Returns:
            Optional[float]: Current LTP or None if unavailable
        """
        ltp = await self.client.get_ltp(symbol)
        if ltp is not None:
            self.last_ltp = ltp
        return ltp
    
    async def stop_ltp_stream(self):
        """Stop the current LTP stream."""
        self.is_streaming = False
        # Clear the display line
        sys.stdout.write('\r\033[K')
        sys.stdout.flush()
    
    def get_current_ltp(self) -> Optional[float]:
        """
        Get the most recently fetched LTP.
        
        Returns:
            Optional[float]: Current LTP or None if not available
        """
        return self.last_ltp


async def display_single_symbol_ltp(client: KotakNeoClient, symbol: str):
    """
    Convenience function to display LTP for a single symbol in a continuous loop.
    
    Args:
        client: KotakNeoClient instance
        symbol: Trading symbol to monitor
    """
    stream = MarketDataStream(client)
    
    try:
        await stream.start_ltp_stream(symbol)
    except KeyboardInterrupt:
        await stream.stop_ltp_stream()
        print("\nLTP stream stopped.")


async def monitor_multiple_symbols(client: KotakNeoClient, symbols: list, display_limit: int = 1):
    """
    Monitor multiple symbols (though for this implementation we'll focus on one at a time
    as per the requirement of displaying on a single line).
    
    Args:
        client: KotakNeoClient instance
        symbols: List of symbols to monitor
        display_limit: Number of symbols to display simultaneously (currently only 1 supported)
    """
    if display_limit == 1 and len(symbols) > 0:
        # For this implementation, we'll just monitor the first symbol
        await display_single_symbol_ltp(client, symbols[0])
    else:
        # Alternative implementation for multiple symbols could go here
        # But per requirements, we focus on single symbol display
        pass