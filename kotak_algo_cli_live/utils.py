import sys
import re
from typing import Optional
from .models import TradeSide
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def validate_symbol(symbol: str) -> bool:
    pattern = r'^[A-Z][A-Z0-9\-&]*$'
    return bool(re.match(pattern, symbol.strip()))

def validate_quantity(quantity_str: str) -> Optional[int]:
    try:
        quantity = int(quantity_str.strip())
        return quantity if quantity > 0 else None
    except ValueError:
        return None

def validate_positive_float(value_str: str) -> Optional[float]:
    try:
        value = float(value_str.strip())
        return value if value >= 0 else None
    except ValueError:
        return None

def parse_trade_side(side_str: str) -> Optional[TradeSide]:
    side_str = side_str.strip().upper()
    if side_str in ['B', 'BUY']:
        return TradeSide.BUY
    elif side_str in ['S', 'SELL']:
        return TradeSide.SELL
    else:
        return None

def clear_screen():
    sys.stdout.write('\033[2J\033[H')
    sys.stdout.flush()

def print_colored(text: str, color_code: str = '36'):
    print(f'\033[{color_code}m{text}\033[0m')

def print_success(message: str):
    print_colored(f'SUCCESS: {message}', '32')

def print_error(message: str):
    print_colored(f'ERROR: {message}', '31')

def print_warning(message: str):
    print_colored(f'WARNING: {message}', '33')

def print_info(message: str):
    print_colored(f'INFO: {message}', '34')

def format_currency(amount: float) -> str:
    return f"{amount:.2f}"

def format_percentage(value: float) -> str:
    return f"{value:.2f}%"

def truncate_string(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    else:
        return text[:max_length-3] + "..."

def get_input_with_default(prompt: str, default_value: str = "") -> str:
    user_input = input(prompt)
    return user_input if user_input.strip() != "" else default_value

def confirm_action(prompt: str) -> bool:
    response = input(f"{prompt} (y/N): ").strip().lower()
    return response in ['y', 'yes']

def format_symbol_display(symbol: str, ltp: float) -> str:
    return f"{symbol} | LTP: {format_currency(ltp)}"