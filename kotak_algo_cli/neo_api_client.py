"""
Mock implementation of the Kotak Neo API client for demonstration purposes.
This simulates the actual API without requiring the real client library.
"""

import time
import random
from typing import Dict, Any, Optional


class NeoAPI:
    """
    Mock NeoAPI client for demonstration purposes.
    In a real implementation, this would connect to the actual Kotak Neo API.
    """
    
    def __init__(self, consumer_key: str, consumer_secret: str, environment: str = 'prod'):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.environment = environment
        self.session_token = None
        self.orders = {}
        self.order_counter = 1000000  # Starting counter for mock order IDs
        
    def login(self, mob_no: str):
        """
        Mock login function.
        """
        print(f"Mock login initiated for mobile: {mob_no}")
        # Simulate successful login
        return {
            'success': True,
            'session_token': f'mock_session_token_for_{mob_no}_{int(time.time())}',
            'message': 'Login successful (mock)'
        }
    
    def set_session_token(self, session_token: str):
        """
        Set the session token for subsequent API calls.
        """
        self.session_token = session_token
        print(f"Session token set: {session_token[:20]}...")
        
    def place_order(self, **kwargs):
        """
        Mock place_order function.
        """
        # Generate a mock order ID
        self.order_counter += 1
        order_id = f"MKT{int(time.time())}{self.order_counter}"
        
        # Store order details
        self.orders[order_id] = {
            'order_id': order_id,
            'status': 'OPEN',
            'details': kwargs
        }
        
        print(f"Mock order placed: {order_id} for {kwargs.get('instrument_token', 'N/A')}")
        
        return {
            'nestOrderNumber': order_id,
            'status': 'success',
            'message': 'Order placed successfully (mock)'
        }
    
    def order_status(self, order_id: str):
        """
        Mock order_status function.
        """
        if order_id in self.orders:
            # Randomly simulate order status changes for demo
            possible_statuses = ['OPEN', 'PARTIAL', 'COMPLETE']
            status = random.choice(possible_statuses)
            
            # Update the stored status
            self.orders[order_id]['status'] = status
            
            return {
                'nestOrderNumber': order_id,
                'stat': status,
                'qty_filled': random.randint(0, self.orders[order_id]['details'].get('quantity', 0)),
                'qty_remaining': random.randint(0, self.orders[order_id]['details'].get('quantity', 0)),
                'avg_prc': round(random.uniform(100, 2000), 2),  # Mock average price
                'message': 'Status retrieved successfully (mock)'
            }
        else:
            return {
                'error': f'Order {order_id} not found',
                'stat': 'NOT_FOUND'
            }
    
    def cancel_order(self, order_id: str):
        """
        Mock cancel_order function.
        """
        if order_id in self.orders:
            self.orders[order_id]['status'] = 'CANCELLED'
            print(f"Mock order cancelled: {order_id}")
            
            return {
                'success': True,
                'message': f'Order {order_id} cancelled successfully (mock)'
            }
        else:
            return {
                'success': False,
                'message': f'Order {order_id} not found for cancellation'
            }
    
    def fetch_market_data(self, feed_type: str, instrument_token: str):
        """
        Mock fetch_market_data function.
        """
        # Generate mock market data
        ltp = round(random.uniform(100, 2000), 2)
        
        return {
            'data': {
                'last_traded_price': ltp,
                'change': round(random.uniform(-10, 10), 2),
                'percent_change': round(random.uniform(-5, 5), 2),
                'volume': random.randint(1000, 100000)
            },
            'instrument_token': instrument_token,
            'timestamp': time.time()
        }
    
    def position(self):
        """
        Mock position function.
        """
        return {
            'positions': [],
            'message': 'Positions retrieved successfully (mock)'
        }
    
    def session_2fa(self, OTP: str):
        """
        Mock 2FA session function.
        """
        return {
            'success': True,
            'session_token': f'mock_session_token_2fa_{int(time.time())}',
            'message': '2FA session established successfully (mock)'
        }
    
    def search_scrip(self, exchange_segment: str, symbol: str):
        """
        Mock search scrip function.
        """
        return {
            'data': [
                {
                    'instrument_token': f'{symbol.upper()}_INSTR_TOKEN',
                    'exchange_segment': exchange_segment,
                    'symbol': symbol
                }
            ],
            'message': 'Scrip search successful (mock)'
        }
    
    def quotes(self, instrument_token: str, exchange_segment: str):
        """
        Mock quotes function.
        """
        return {
            'last_traded_price': round(random.uniform(100, 2000), 2),
            'instrument_token': instrument_token,
            'exchange_segment': exchange_segment,
            'message': 'Quotes retrieved successfully (mock)'
        }