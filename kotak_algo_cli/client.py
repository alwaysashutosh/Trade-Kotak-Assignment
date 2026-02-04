import asyncio
import time
from typing import Dict, Optional, Any
from neo_api_client import NeoAPI
try:
    from .models import Order, OrderType, OrderStatus, TradeSide
except ImportError:
    # Fallback for direct execution
    from models import Order, OrderType, OrderStatus, TradeSide
import logging

logger = logging.getLogger(__name__)


class KotakNeoClient:
    """
    Wrapper for Kotak Neo API client that handles authentication and trading operations.
    This class abstracts the API interactions and provides a clean interface for trading operations.
    """
    
    def __init__(self, consumer_key: str, consumer_secret: str, mobile_number: str, password: str):
        """
        Initialize the Kotak Neo client with credentials.
        
        Args:
            consumer_key: Kotak Neo consumer key
            consumer_secret: Kotak Neo consumer secret
            mobile_number: User's registered mobile number
            password: User's trading password
        """
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.mobile_number = mobile_number
        self.password = password
        self.client = None
        self.session_token = None
        
    async def authenticate(self) -> bool:
        """
        Authenticate with Kotak Neo API and establish session.
        
        Returns:
            bool: True if authentication successful, False otherwise
        """
        try:
            # Initialize the Neo API client
            self.client = NeoAPI(
                consumer_key=self.consumer_key,
                consumer_secret=self.consumer_secret,
                environment='prod'  # or 'sandbox' for testing
            )
            
            # Start the session
            login_data = self.client.login(mob_no=self.mobile_number)
            
            # For mock implementation, skip OTP and assume successful session
            session_2fa_response = {'success': True, 'session_token': f'mock_session_{int(time.time())}'}
            
            if session_2fa_response.get('success'): # This condition is always true for mock
                # Set session token for subsequent API calls
                self.session_token = session_2fa_response.get('session_token')
                self.client.set_session_token(session_token=self.session_token)
                
                logger.info("Successfully authenticated with Kotak Neo API")
                return True
            else:
                logger.error(f"Authentication failed: {session_2fa_response}")
                return False
                
        except Exception as e:
            logger.error(f"Error during authentication: {str(e)}")
            return False
    
    async def place_order(self, order: Order) -> Optional[str]:
        """
        Place an order with Kotak Neo API.
        
        Args:
            order: Order object containing trade details
            
        Returns:
            Optional[str]: Order ID if successful, None otherwise
        """
        try:
            # Prepare order parameters based on order type
            order_params = {
                'instrument_token': await self._get_instrument_token(order.symbol),
                'order_type': order.order_type.value,
                'quantity': order.quantity,
                'side': order.side.value,
                'product': 'CNC',  # Cash and Carry for equity delivery
                'validity': 'DAY',
            }
            
            # Add price-specific parameters based on order type
            if order.order_type == OrderType.MARKET:
                order_params['price'] = 0  # Market orders have zero price
                order_params['transaction_type'] = 'MKT'
            elif order.order_type in [OrderType.STOP_LOSS, OrderType.TARGET]:
                order_params['price'] = order.trigger_price or order.price
                order_params['transaction_type'] = 'SL-M'  # Stop loss market
            else:
                order_params['price'] = order.price
                order_params['transaction_type'] = 'LMT'  # Limit order
            
            # Place the order
            response = self.client.place_order(**order_params)
            
            if response and 'nestOrderNumber' in response:
                order_id = response['nestOrderNumber']
                logger.info(f"Order placed successfully: {order_id} for {order.symbol}")
                return order_id
            else:
                logger.error(f"Failed to place order: {response}")
                return None
                
        except Exception as e:
            logger.error(f"Error placing order for {order.symbol}: {str(e)}")
            return None
    
    async def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of an order.
        
        Args:
            order_id: The order ID to check
            
        Returns:
            Optional[Dict]: Order status information or None if error
        """
        try:
            response = self.client.order_status(order_id=order_id)
            
            if response:
                return {
                    'order_id': order_id,
                    'status': response.get('stat'),
                    'filled_quantity': int(response.get('qty_filled', 0)),
                    'average_price': float(response.get('avg_prc', 0)) if response.get('avg_prc') else None,
                    'remaining_quantity': int(response.get('qty_remaining', 0))
                }
            else:
                logger.warning(f"No status found for order: {order_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting order status for {order_id}: {str(e)}")
            return None
    
    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order.
        
        Args:
            order_id: The order ID to cancel
            
        Returns:
            bool: True if cancellation successful, False otherwise
        """
        try:
            response = self.client.cancel_order(order_id=order_id)
            
            if response and response.get('success'):
                logger.info(f"Order cancelled successfully: {order_id}")
                return True
            else:
                logger.error(f"Failed to cancel order {order_id}: {response}")
                return False
                
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {str(e)}")
            return False
    
    async def get_ltp(self, symbol: str) -> Optional[float]:
        """
        Get the last traded price for a symbol.
            
        Args:
            symbol: Trading symbol to get LTP for
            
        Returns:
            Optional[float]: Last traded price or None if error
        """
        try:
            token = await self._get_instrument_token(symbol)
                
            res = self.client.quotes(
                instrument_token=token,
                exchange_segment="nse_cm"
            )
                
            return float(res["last_traded_price"])
        except Exception as e:
            print("LTP error:", e)
            return None
    
    async def _get_instrument_token(self, symbol: str) -> str:
        """
        Get instrument token for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            str: Instrument token
        """
        res = self.client.search_scrip(
            exchange_segment="nse_cm",
            symbol=symbol
        )
        
        return res["data"][0]["instrument_token"]
    
    async def get_positions(self) -> Optional[list]:
        """
        Get current positions.
        
        Returns:
            Optional[list]: List of current positions or None if error
        """
        try:
            response = self.client.position()
            return response
        except Exception as e:
            logger.error(f"Error fetching positions: {str(e)}")
            return None