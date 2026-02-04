import asyncio
import time
import os
from typing import Dict, Optional, Any
from neo_api_client import NeoAPI
from .models import Order, OrderType, OrderStatus, TradeSide
import logging

logger = logging.getLogger(__name__)

class KotakNeoClient:
    def __init__(self):
        self.consumer_key = os.getenv("KOTAK_CONSUMER_KEY")
        self.consumer_secret = os.getenv("KOTAK_CONSUMER_SECRET")
        self.mobile_number = os.getenv("KOTAK_MOBILE")
        self.password = os.getenv("KOTAK_PASSWORD")
        self.demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true"
        self.client = None
        self.session_token = None
        if not all([self.consumer_key, self.consumer_secret, self.mobile_number, self.password]):
            raise ValueError("Missing required environment variables. Please check .env file.")

    async def authenticate(self) -> bool:
        try:
            self.client = NeoAPI(
                consumer_key=self.consumer_key,
                consumer_secret=self.consumer_secret,
                environment='prod'
            )
            logger.info("Initiating login with mobile number...")
            login_response = self.client.login(mob_no=self.mobile_number)
            if not login_response or not login_response.get('success'):
                logger.error(f"Login failed: {login_response}")
                return False
            print(f"\nOTP has been sent to mobile number: {self.mobile_number}")
            otp = input("Please enter the OTP received: ").strip()
            if not otp:
                logger.error("OTP cannot be empty")
                return False
            logger.info("Completing 2FA authentication...")
            session_2fa_response = self.client.session_2fa(OTP=otp)
            if session_2fa_response and session_2fa_response.get('success'):
                self.session_token = session_2fa_response.get('session_token')
                self.client.set_session_token(session_token=self.session_token)
                mode_str = "DEMO" if self.demo_mode else "LIVE"
                logger.info(f"Successfully authenticated with Kotak Neo API in {mode_str} mode")
                print(f"\n=== AUTHENTICATED IN {mode_str} MODE ===")
                print(f"Session token: {self.session_token[:20]}...")
                return True
            else:
                logger.error(f"2FA authentication failed: {session_2fa_response}")
                return False
        except Exception as e:
            logger.error(f"Error during authentication: {str(e)}")
            return False

    async def place_order(self, order: Order) -> Optional[str]:
        try:
            instrument_token = await self._get_instrument_token(order.symbol)
            if not instrument_token:
                logger.error(f"Failed to get instrument token for {order.symbol}")
                return None
            order_params = {
                'instrument_token': instrument_token,
                'order_type': order.order_type.value,
                'quantity': order.quantity,
                'side': order.side.value,
                'product': 'CNC',
                'validity': 'DAY',
            }
            if order.order_type == OrderType.MARKET:
                order_params['price'] = 0
                order_params['transaction_type'] = 'MKT'
            elif order.order_type in [OrderType.STOP_LOSS, OrderType.TARGET]:
                order_params['price'] = order.trigger_price or order.price
                order_params['transaction_type'] = 'SL-M'
            else:
                order_params['price'] = order.price
                order_params['transaction_type'] = 'LMT'
            if self.demo_mode:
                logger.info(f"DEMO MODE: Would place order {order.order_type.value} {order.side.value} "
                           f"{order.quantity} shares of {order.symbol} at {order_params.get('price') or 'Market'}")
                demo_order_id = f"DEMO_{int(time.time())}_{order.symbol}"
                logger.info(f"Demo order ID: {demo_order_id}")
                return demo_order_id
            logger.info(f"Placing real order: {order.side.value} {order.quantity} {order.symbol}")
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
        try:
            if self.demo_mode:
                logger.info(f"DEMO MODE: Would cancel order {order_id}")
                logger.info(f"Demo cancellation confirmed for order: {order_id}")
                return True
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

    async def _get_instrument_token(self, symbol: str) -> Optional[str]:
        try:
            res = self.client.search_scrip(
                exchange_segment="nse_cm",
                symbol=symbol
            )
            if res and "data" in res and len(res["data"]) > 0:
                token = res["data"][0]["instrument_token"]
                logger.debug(f"Instrument token for {symbol}: {token}")
                return token
            else:
                logger.error(f"No instrument found for symbol: {symbol}")
                return None
        except Exception as e:
            logger.error(f"Error getting instrument token for {symbol}: {str(e)}")
            return None

    async def get_positions(self) -> Optional[list]:
        try:
            response = self.client.position()
            return response
        except Exception as e:
            logger.error(f"Error fetching positions: {str(e)}")
            return None