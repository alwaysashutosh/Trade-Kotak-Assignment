# Kotak Neo Live Trading CLI

Production-ready asynchronous trading CLI for Kotak Neo API with real market data and live order execution.

## Features

- Real-time LTP streaming with ANSI single-line display
- OCO (One-Cancels-Other) order execution logic
- Live order placement with Kotak Neo API
- Safety DEMO mode to prevent accidental live trading
- Asynchronous architecture for non-blocking operations
- Environment-based configuration

## Prerequisites

- Python 3.8+
- Kotak Neo API credentials
- `neo_api_client` Python package

## Installation

1. Install the required package:
```bash
pip install neo_api_client
```

2. Clone or copy the `kotak_algo_cli_live` directory to your project

## Configuration

Create a `.env` file in the `kotak_algo_cli_live` directory with your credentials:

```env
KOTAK_CONSUMER_KEY=your_consumer_key_here
KOTAK_CONSUMER_SECRET=your_consumer_secret_here
KOTAK_MOBILE=+91xxxxxxxxxx
KOTAK_PASSWORD=your_trading_password
DEMO_MODE=true
```

### Environment Variables

- `KOTAK_CONSUMER_KEY`: Your Kotak Neo API consumer key
- `KOTAK_CONSUMER_SECRET`: Your Kotak Neo API consumer secret
- `KOTAK_MOBILE`: Your registered mobile number with country code
- `KOTAK_PASSWORD`: Your trading account password
- `DEMO_MODE`: Set to `true` for safe testing, `false` for live trading

## Usage

Run the CLI application:

```bash
cd kotak_algo_cli_live
python main.py
```

### Safety Mode

The application includes a safety DEMO mode:
- When `DEMO_MODE=true`: Orders are simulated and logged only
- When `DEMO_MODE=false`: Real orders are placed on the exchange
- Default is `true` to prevent accidental live trading

### CLI Workflow

1. Application initializes and prompts for OTP authentication
2. Enter trading symbol when prompted
3. LTP stream starts showing real-time prices
4. Enter trade parameters:
   - B/S (Buy/Sell)
   - Quantity
   - SL points (Stop Loss)
   - Target points (Profit Target)
5. System executes OCO trade with market order + SL + Target
6. Orders are monitored in background with automatic cancellation logic

## Architecture

### Core Components

- **client.py**: Kotak Neo API wrapper with authentication and trading operations
- **main.py**: Main CLI application orchestrator
- **market_data.py**: Real-time LTP streaming with ANSI display
- **trade.py**: OCO trade execution logic
- **trade_manager.py**: Trade lifecycle management
- **models.py**: Data classes and enumerations
- **utils.py**: Helper functions and validation

### Key Features

- **Asynchronous Design**: Uses `asyncio` for non-blocking operations
- **OCO Logic**: Automatic order cancellation when one leg executes
- **Real-time Data**: Live LTP streaming via Kotak Neo API
- **Error Handling**: Comprehensive exception handling and logging
- **Safety First**: DEMO mode prevents accidental live trading

## Order Types

- **MARKET**: Immediate execution at best available price
- **STOP_LOSS**: Trigger-based order that becomes market when price reached
- **TARGET**: Profit-taking order that becomes market when target price reached

## Authentication Flow

1. Initialize NeoAPI client with credentials
2. Login with mobile number
3. User enters OTP received on mobile
4. Session token established for subsequent API calls
5. Application shows current mode (DEMO/LIVE)

## Logging

The application uses Python's logging module with INFO level by default. Logs include:
- Authentication status
- Order placement details
- Trade execution results
- Error conditions
- DEMO mode indicators

## Security

- Credentials loaded from environment variables (not hardcoded)
- No sensitive data stored in source code
- OTP-based 2FA authentication required
- DEMO mode prevents accidental live trading

## Error Handling

- Invalid symbols are rejected with clear error messages
- API connection failures are gracefully handled
- Order placement errors are logged and reported
- LTP stream automatically reconnects on failures

## Example Output

```
INFO: Initializing Kotak Neo Trading CLI...
INFO: Initiating login with mobile number...

OTP has been sent to mobile number: +91xxxxxxxxxx
Please enter the OTP received: 123456

=== AUTHENTICATED IN DEMO MODE ===
Session token: demo_session_token...

INFO: Successfully authenticated with Kotak Neo API in DEMO MODE
INFO: All components initialized successfully

Which symbol to enter? (or 'quit' to exit): RELIANCE
RELIANCE | LTP: 2450.50
B/S (Buy/Sell): B
Quantity: 10
SL points: 20
Target points: 30

INFO: Executing trade: RELIANCE BUY 10 @ 2450.5
INFO: SL: 20, Target: 30
DEMO MODE: Would place order MARKET BUY 10 shares of RELIANCE at Market
INFO: Demo order ID: DEMO_1234567890_RELIANCE
SUCCESS: Trade placed successfully. Orders: DEMO_1234567890_RELIANCE, SL: DEMO_1234567891_RELIANCE, Target: DEMO_1234567892_RELIANCE
```

## Troubleshooting

### Common Issues

1. **Authentication Failure**: Check your credentials and OTP
2. **Invalid Symbol**: Ensure symbol format matches exchange requirements
3. **API Connection**: Verify internet connectivity and API status
4. **Order Rejection**: Check quantity limits and account permissions

### Getting Help

- Check logs for detailed error messages
- Verify all environment variables are set correctly
- Ensure `neo_api_client` package is properly installed
- Contact Kotak Neo API support for credential issues