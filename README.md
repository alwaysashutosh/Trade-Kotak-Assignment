# Kotak Neo Algo Trading


---

## 📂 Project Structure

This repository contains two main directories, each serving a specific purpose:

### 1. `kotak_algo_cli` (Development & Testing)
This is your **sandbox**. Use this folder for development, reliable backtesting, and simulation. It is designed to be a safe space where you can:
- Test API connections without risking real capital.
- Debug your trading logic and OCO (One-Cancels-Other) order flows.
- Experiment with the CLI interface.

**Key Characteristic:** Contains placeholders for credentials and robust error handling for standalone execution.

### 2. `kotak_algo_cli_live` (Live Trading)
This is the **production-ready** module. Use this folder when you are ready to trade with real money. It features:
- **Real-time Market Data:** Streams live LTP (Last Traded Price) directly from Kotak Neo.
- **Live Order Execution:** Places actual orders on the exchange.
- **Safety DEMO Mode:** A built-in safety switch (`DEMO_MODE=true`) that lets you dry-run the "Live" system before flipping the switch to real trading.

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.8+**
- **Kotak Neo API Credentials:** You will need your Consumer Key, Secret, and Trading Password.
- **Neo API Client:**
  ```bash
  pip install neo_api_client
  ```

### Configuration

For the **Live** module (`kotak_algo_cli_live`), you must configure your environment variables. create a `.env` file inside the `kotak_algo_cli_live` directory:

```env
KOTAK_CONSUMER_KEY=your_consumer_key
KOTAK_CONSUMER_SECRET=your_consumer_secret
KOTAK_MOBILE=+919876543210
KOTAK_PASSWORD=your_trading_password
DEMO_MODE=true  # Set to 'false' ONLY when ready for real money
```

> **⚠️ CAUTION:** Never commit your `.env` file or credentials to version control.

---

## 💻 Usage

### Running the Live Trader
1. Navigate to the live directory:
   ```bash
   cd kotak_algo_cli_live
   ```
2. Run the entry point (ensure you are running it as a module if needed, or directly if supported):
   ```bash
   python main.py
   ```
3. Follow the CLI prompts to authenticated (OTP will be sent to your mobile).

### Live Workflow
1. **Enter Symbol:** Type the valid trading symbol (e.g., `RELIANCE`).
2. **Stream Data:** Watch the real-time price stream.
3. **Place Order:**
   - Choose **B** (Buy) or **S** (Sell).
   - Enter **Quantity**.
   - Set **Stop Loss (SL)** and **Target** points.
4. **Execution:** The system places an OCO order (Entry + SL + Target) and monitors it.

---

## 🛡️ Safety Features

- **DEMO_MODE:** In the live folder, if `DEMO_MODE` is set to `true`, the system simulates orders and prints them to the console instead of sending them to the exchange.
- **Input Validation:** Prevents fat-finger errors by validating symbols and quantities before submission.
- **Graceful Shutdown:** Handles `Ctrl+C` to cleanly stop data streams and close sessions.

---

## ⚠️ Disclaimer

*Algorithmic trading involves significant risk. This software is provided "as is" without warranty of any kind. Please test thoroughly in DEMO mode before trading with real capital. The authors are not responsible for any financial losses incurred.*
