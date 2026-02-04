import sys
import re
from typing import Optional
try:
    from .models import TradeSide
except ImportError:
    # Fallback for direct execution
    from models import TradeSide
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


def validate_symbol(symbol: str) -> bool:
    """
    Validate trading symbol format.
    
    Args:
        symbol: Trading symbol to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    # Allow alphanumeric characters and common symbols like '&', '-', etc.
    # Typically Indian stock symbols are 1-10 characters
    pattern = r'^[A-Z][A-Z0-9\-&]*$'
    return bool(re.match(pattern, symbol.strip()))


def validate_quantity(quantity_str: str) -> Optional[int]:
    """
    Validate and convert quantity string to integer.
    
    Args:
        quantity_str: String representation of quantity
        
    Returns:
        Optional[int]: Validated quantity or None if invalid
    """
    try:
        quantity = int(quantity_str.strip())
        return quantity if quantity > 0 else None
    except ValueError:
        return None


def validate_positive_float(value_str: str) -> Optional[float]:
    """
    Validate and convert float string to positive float.
    
    Args:
        value_str: String representation of a float value
        
    Returns:
        Optional[float]: Validated float value or None if invalid
    """
    try:
        value = float(value_str.strip())
        return value if value >= 0 else None
    except ValueError:
        return None


def parse_trade_side(side_str: str) -> Optional[TradeSide]:
    """
    Parse trade side from string input.
    
    Args:
        side_str: String representation of trade side ('B' for BUY, 'S' for SELL)
        
    Returns:
        Optional[TradeSide]: Parsed trade side or None if invalid
    """
    side_str = side_str.strip().upper()
    if side_str in ['B', 'BUY']:
        return TradeSide.BUY
    elif side_str in ['S', 'SELL']:
        return TradeSide.SELL
    else:
        return None


def clear_screen():
    """
    Clear the terminal screen using ANSI escape codes.
    """
    sys.stdout.write('\033[2J\033[H')
    sys.stdout.flush()


def print_colored(text: str, color_code: str = '36'):
    """
    Print colored text using ANSI escape codes.
    
    Args:
        text: Text to print
        color_code: ANSI color code (default is cyan: 36)
    """
    print(f'\033[{color_code}m{text}\033[0m')


def print_success(message: str):
    """
    Print a success message in green.
    
    Args:
        message: Success message to print
    """
    print_colored(f'SUCCESS: {message}', '32')


def print_error(message: str):
    """
    Print an error message in red.
    
    Args:
        message: Error message to print
    """
    print_colored(f'ERROR: {message}', '31')


def print_warning(message: str):
    """
    Print a warning message in yellow.
    
    Args:
        message: Warning message to print
    """
    print_colored(f'WARNING: {message}', '33')


def print_info(message: str):
    """
    Print an info message in blue.
    
    Args:
        message: Info message to print
    """
    print_colored(f'INFO: {message}', '34')


def format_currency(amount: float) -> str:
    """
    Format currency amount with 2 decimal places.
    
    Args:
        amount: Amount to format
        
    Returns:
        str: Formatted currency string
    """
    return f"{amount:.2f}"


def format_percentage(value: float) -> str:
    """
    Format percentage value with 2 decimal places and % sign.
    
    Args:
        value: Percentage value to format
        
    Returns:
        str: Formatted percentage string
    """
    return f"{value:.2f}%"


def truncate_string(text: str, max_length: int) -> str:
    """
    Truncate string to specified length with ellipsis if needed.
    
    Args:
        text: String to truncate
        max_length: Maximum length of the string
        
    Returns:
        str: Truncated string
    """
    if len(text) <= max_length:
        return text
    else:
        return text[:max_length-3] + "..."

def get_input_with_default(prompt: str, default_value: str = "") -> str:
    """
    Get user input with an optional default value.
    
    Args:
        prompt: Prompt message
        default_value: Default value to return if user presses Enter
        
    Returns:
        str: User input or default value
    """
    user_input = input(prompt)
    return user_input if user_input.strip() != "" else default_value


def confirm_action(prompt: str) -> bool:
    """
    Ask user to confirm an action.
    
    Args:
        prompt: Confirmation prompt
        
    Returns:
        bool: True if confirmed, False otherwise
    """
    response = input(f"{prompt} (y/N): ").strip().lower()
    return response in ['y', 'yes']


def format_symbol_display(symbol: str, ltp: float) -> str:
    """
    Format symbol and LTP for display.
    
    Args:
        symbol: Trading symbol
        ltp: Last traded price
        
    Returns:
        str: Formatted display string
    """
    return f"{symbol} | LTP: {format_currency(ltp)}"