import asyncio
import sys
from typing import Callable, Optional
from .client import KotakNeoClient
from .models import MarketData
import logging

logger = logging.getLogger(__name__)

class MarketDataStream:
    def __init__(self, client: KotakNeoClient):
        self.client = client
        self.is_streaming = False
        self.current_symbol = None
        self.last_ltp = None
        
    async def start_ltp_stream(self, symbol: str, update_callback: Optional[Callable] = None):
        self.is_streaming = True
        self.current_symbol = symbol
        last_printed_length = 0
        try:
            while self.is_streaming:
                ltp = await self.client.get_ltp(symbol)
                if ltp is not None:
                    self.last_ltp = ltp
                    display_str = f"{symbol} | LTP: {ltp:.2f}"
                    sys.stdout.write('\r\033[K')
                    sys.stdout.write(display_str)
                    sys.stdout.flush()
                    if update_callback:
                        await update_callback(MarketData(
                            symbol=symbol,
                            ltp=ltp,
                            change=0.0,
                            change_percent=0.0,
                            volume=0
                        ))
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("LTP stream cancelled")
        except Exception as e:
            logger.error(f"Error in LTP stream for {symbol}: {str(e)}")
        finally:
            sys.stdout.write('\r\033[K')
            sys.stdout.flush()
    
    async def get_current_ltp_for_symbol(self, symbol: str) -> Optional[float]:
        ltp = await self.client.get_ltp(symbol)
        if ltp is not None:
            self.last_ltp = ltp
        return ltp
    
    async def stop_ltp_stream(self):
        self.is_streaming = False
        sys.stdout.write('\r\033[K')
        sys.stdout.flush()
    
    def get_current_ltp(self) -> Optional[float]:
        return self.last_ltp

async def display_single_symbol_ltp(client: KotakNeoClient, symbol: str):
    stream = MarketDataStream(client)
    try:
        await stream.start_ltp_stream(symbol)
    except KeyboardInterrupt:
        await stream.stop_ltp_stream()
        print("\nLTP stream stopped.")

async def monitor_multiple_symbols(client: KotakNeoClient, symbols: list, display_limit: int = 1):
    if display_limit == 1 and len(symbols) > 0:
        await display_single_symbol_ltp(client, symbols[0])
    else:
        pass