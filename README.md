# Meshtastic-AI (Alpha v0.4.1) - (Available through GIT pull until ready for full release)

![image](https://github.com/user-attachments/assets/7250e722-3f7e-49f2-9439-9b8ad75a1981)

**Meshtastic-AI** (MESH-AI for short) is an experimental project that bridges [Meshtastic](https://meshtastic.org/) LoRa mesh networks with powerful AI chatbots. This release builds on the previous Alpha v0.3.0 version by introducing a major WebUI overhaul, enhanced error handling with UTC‑based logging, refined command processing (including case‑insensitivity), and expanded integrations for emergency notifications via Twilio, SMTP email, and Discord. You can choose between local models (LM Studio, Ollama), OpenAI, or even integrate with Home Assistant for off‑grid AI assistance.

> **Disclaimer:**  
> This project is **NOT ASSOCIATED** with the official Meshtastic Project. It is provided solely as an extension to add AI and advanced features to your Meshtastic network.  
>  
> **Alpha Software Warning:**  
> This version is still in alpha. It may be unstable or incomplete. Please avoid relying on it for mission‑critical tasks or emergencies. Always have backup communication methods available and use responsibly.  
>  
> *I am one robot using other robots to write this code. Some features are still untested in the field. Check the GitHub issues for fixes or feedback!*

---

## Features

- **Multiple AI Providers**  
  - Support for **Local** models (LM Studio, Ollama), **OpenAI**, and even **Home Assistant** integration.
- **Home Assistant Integration**  
  - Seamlessly forward messages from a designated channel to Home Assistant’s conversation API. Optionally secure the integration using a PIN.
- **Advanced Slash Commands**  
  - Built‑in commands: `/about`, `/ping`, `/test`, `/help`, `/motd`, `/ai` (aliases: `/bot`, `/query`, `/data`), `/emergency` (or `/911`), `/whereami` plus custom commands via `commands_config.json`.
  - Commands are now case‑insensitive for improved mobile usability.
- **Emergency Alerts**  
  - Trigger alerts that are sent via **Twilio SMS**, **SMTP Email**, and, if enabled, **Discord**.
  - Emergency notifications include GPS coordinates, UTC timestamps, and user messages.
- **Enhanced REST API & WebUI Dashboard**  
  - A modern three‑column layout showing broadcast messages, direct messages, and available nodes.
  - Additional endpoints include `/messages`, `/nodes`, `/connection_status`, `/logs`, `/send`, `/ui_send`, and a new `/discord_webhook` for inbound Discord messages.
  - UI customization through settings such as theme color, hue rotation, and custom sounds.
- **Improved Message Chunking & Routing**  
  - Automatically splits long AI responses into configurable chunks with delays to reduce radio congestion.
  - Configurable flags control whether the bot replies to broadcast channels and/or direct messages.
- **Robust Error Handling & Logging**  
  - Uses UTC‑based timestamps with an auto‑truncating script log file (keeping the last 100 lines if the file grows beyond 100 MB).
  - Enhanced error detection (including specific OSError codes) and graceful reconnection using threaded exception hooks.
- **Discord Integration Enhancements**  
  - Route messages to and from Discord.
  - New configuration options and a dedicated `/discord_webhook` endpoint allow for inbound Discord message processing.
- **Windows‑Focused - Linux compatability confirmed!  Thanks Milo Oh!
  - Official support for Windows environments with installation guides; instructions for Linux/macOS are coming soon.

---

## Changelog

## 1. Changelog: v0.1 → v0.2.2

- **Expanded Configuration & JSON Files**  
   - **New `config.json` fields**  
     - Added `debug` toggle for verbose debugging.  
     - Added options for multiple AI providers (`lmstudio`, `openai`, `ollama`), including timeouts and endpoints.  
     - Introduced **Home Assistant** integration toggles (`home_assistant_enabled`, `home_assistant_channel_index`, secure pin, etc.).  
     - Implemented **Twilio** and **SMTP** settings for emergency alerts (including phone number, email, and credentials).  
     - Added **Discord** webhook configuration toggles (e.g., `enable_discord`, `discord_send_emergency`, etc.).  
     - Several new user-configurable parameters to control message chunking (`chunk_size`, `max_ai_chunks`, and `chunk_delay`) to reduce radio congestion.  
- **Support for Multiple AI Providers**  
   - **Local Language Models** (LM Studio, Ollama) and **OpenAI** (GPT-3.5, etc.) can be selected via `ai_provider`.  
   - Behavior is routed depending on which provider you specify in `config.json`.
- **Home Assistant Integration**  
   - Option to route messages on a dedicated channel directly to Home Assistant’s conversation API.  
   - **Security PIN** requirement can be enabled, preventing unauthorized control of Home Assistant.  
- **Improved Command Handling**  
   - Replaced single-purpose code with a new, flexible **commands system** loaded from `commands_config.json`.  
   - Users can define custom commands that either have direct string responses or prompt an AI.  
   - Built-in commands now include `/ping`, `/test`, `/emergency`, `/whereami`, `/help`, `/motd`, and more.  
- **Emergency Alert System**  
   - `/emergency` (or `/911`) triggers optional Twilio SMS, SMTP email, and/or Discord alerts.  
   - Retrieves node GPS coordinates (if available) to include location in alerts.  
- **Improved Message Chunking & Throttling**  
   - Long AI responses are split into multiple smaller segments (configurable via `chunk_size` & `max_ai_chunks`).  
   - Delays (`chunk_delay`) between chunks to avoid flooding the mesh network.  
- **REST API Endpoints** (via built-in Flask server)  
   - `GET /messages`: Returns the last 100 messages in JSON.  
   - `GET /dashboard`: Displays a simple HTML dashboard showing the recently received messages.  
   - `POST /send`: Manually send messages to nodes (direct or broadcast) from external scripts or tools.  
- **Improved Logging and File Structure**  
   - **`messages.log`** for persistent logging of all incoming messages, commands, and emergencies.  
   - Distinct JSON config files: `config.json`, `commands_config.json`, and `motd.json`.  
- **Refined Startup & Script Structure**  
   - A new `Run Mesh-AI - Windows.bat` script for straightforward Windows startup.  
   - Added disclaimers for alpha usage throughout the code.  
   - Streamlined reconnection and exception handling logic with more robust error-handling.  
- **General Stability & Code Quality Enhancements**  
   - Thorough refactoring of the code to be more modular and maintainable.  
   - Better debugging hooks, improved concurrency handling, and safer resource cleanup.  

### Changelog: v0.2.2 → v0.3.0 (from the original Main Branch README)
- **WebUI Overhaul:**  
  - Redesigned three‑column dashboard showing channel messages, direct messages, and node list.
  - New send‑message form with toggleable modes (broadcast vs. direct), dynamic character counting, and message chunk preview.
- **Improved Error Handling & Stability:**  
  - Redirected stdout/stderr to a persistent `script.log` file with auto‑truncation.
  - Added a connection monitor thread to detect disconnections and trigger automatic reconnects.
  - Implemented a thread exception hook for better error logging.
- **Enhanced Message Routing & AI Response Options:**  
  - Added configuration flags (`reply_in_channels` and `reply_in_directs`) to control AI responses.
  - Increased maximum message chunks (default up to 5) for longer responses.
  - Updated slash command processing (e.g., added `/about`) and support for custom commands.
- **Expanded API Endpoints:**  
  - New endpoints: `/nodes`, updated `/connection_status`, and `/ui_send`.
- **Additional Improvements:**  
  - Robust Home Assistant integration and basic emergency alert enhancements.

### New Updates in v0.3.0 → v0.4.0
- **Logging & Timestamps:**  
  - Shift to UTC‑based timestamps and enhanced log management.
- **Discord Integration:**  
  - Added configuration for inbound/outbound Discord message routing.
  - Introduced a new `/discord_webhook` endpoint for processing messages from Discord.
- **Emergency Notifications:**  
  - Expanded emergency alert logic to include detailed context (GPS data, UTC time) and Discord notifications.
- **Sending and receiving SMS:**  
  - Send SMS using `/sms <+15555555555> <message>`
  - Config options to either route incoming Twilio SMS messages to a specific node, or a channel index.
- **Command Handling:**  
  - Made all slash commands case‑insensitive to improve usability.
  - Enhanced custom command support via `commands_config.json` with dynamic AI prompt insertion.
- **Improved Error Handling & Reconnection:**  
  - More granular detection of connection errors (e.g., specific OSError codes) and use of a global reset event for reconnects.
- **Code Refactoring:**  
  - Overall code improvements for maintainability and clarity, with additional debug prints for troubleshooting.

### New Updates in v0.4.0 → v0.4.1
- **Error Handling (ongoing):**  
  - Trying a new method to handle WinError exceptions - which though much improved in v0.4.0 - still occur under the right connection circumstances - especially over Wi-Fi.  
     (**UPDATE: My WinError issues were being caused by a combination of low solar power, and MQTT being enabled on my node.  MQTT - especially using LongFast is very intense on a node, and can cause abrupt connection restarts as noted here:  https://github.com/meshtastic/meshtastic/pull/901 - but - now the script is super robust regardless for handling errors!)**
- **Emergency Email Subject:**  
  - Email Subject now includes the long name, short name & Node ID of the sending node, rather than just the Node ID.
- **Docker Support**  
  - Thanks @clendaniel - Who was kind enough to generate a Dockerfile & docker-compose.yaml for the project!
  
---

## Quick Start (Windows)

1. **Download/Clone**  
   - Clone the repository or copy the **meshtastic-ai** folder to your Desktop.
2. **Install Dependencies:**  
   - Create a virtual environment:
     ```bash
     cd path\to\meshtastic_ai
     python -m venv venv
     venv\Scripts\activate
     ```
   - Upgrade pip and install required packages:
     ```bash
     pip install --upgrade pip
     pip install -r requirements.txt
     ```
3. **Configure Files:**  
   - Edit `config.json`, `commands_config.json`, and `motd.json` as needed. Refer to the **Configuration** section below.
4. **Start the Bot:**  
   - Run the bot by double‑clicking `Run Mesh-AI - Windows.bat` or by executing:
     ```bash
     python meshtastic_ai.py
     ```
5. **Access the WebUI Dashboard:**  
   - Open your browser and navigate to [http://localhost:5000/dashboard](http://localhost:5000/dashboard).

![Screenshot 2025-03-07 051915](https://github.com/user-attachments/assets/bc58baf4-5cfa-40e5-8086-58d24afd311c)


---

## Basic Usage

- **Interacting with the AI:**  
  - Use `/ai` (or `/bot`, `/query`, `/data`) followed by your message to receive an AI response.
  - For direct messages, simply DM the AI node if configured to reply.
- **Location Query:**  
  - Send `/whereami` to retrieve the node’s GPS coordinates (if available).
- **Emergency Alerts:**  
  - Trigger an emergency using `/emergency <message>` or `/911 <message>`.  
    - These commands send alerts via Twilio, SMTP, and Discord (if enabled), including GPS data and timestamps.
- **Sending and receiving SMS:**  
  - Send SMS using `/sms <+15555555555> <message>`
  - Config options to either route incoming Twilio SMS messages to a specific node, or a channel index.
- **Home Assistant Integration:**  
  - When enabled, messages sent on the designated Home Assistant channel (as defined by `"home_assistant_channel_index"`) are forwarded to Home Assistant’s conversation API.
  - In secure mode, include the PIN in your message (format: `PIN=XXXX your message`).
- **WebUI Messaging:**  
  - Use the dashboard’s send‑message form to send broadcast or direct messages. The mode toggle and node selection simplify quick replies.

---

## Using the API

The Meshtastic-AI server (running on Flask) exposes the following endpoints:

- **GET `/messages`**  
  Retrieve the last 100 messages in JSON format.
- **GET `/nodes`**  
  Retrieve a live list of connected nodes as JSON.
- **GET `/connection_status`**  
  Get current connection status and error details.
- **GET `/logs`**  
  View a styled log page showing uptime, restarts, and recent log entries.
- **GET `/dashboard`**  
  Access the full WebUI dashboard.
- **POST `/send`** and **POST `/ui_send`**  
  Send messages programmatically.
- **POST `/discord_webhook`**  
  Receive messages from Discord (if configured).

---

## Configuration

Your `config.json` file controls almost every aspect of Meshtastic-AI. Below is an example configuration that includes both the previous settings and the new options:

```json
{
  "debug": false,
  
  "serial_port": "",
  "use_mesh_interface": false,
  "use_wifi": true,
  "wifi_host": "<MESHTASTIC NODE IP HERE>",
  "wifi_port": 4403,

  "ai_provider": "lmstudio", 
  "system_prompt": "You are a helpful assistant responding to mesh network chats. Respond in as few words as possible while still answering fully.",
  
  "lmstudio_url": "http://localhost:1234/v1/chat/completions",
  "lmstudio_timeout": 60,
  
  "openai_api_key": "",
  "openai_model": "gpt-3.5-turbo",
  "openai_timeout": 30,
  
  "ollama_url": "http://localhost:11434/api/generate",
  "ollama_model": "llama2",
  "ollama_timeout": 60,
  
  "home_assistant_url": "http://homeassistant.local:8123/api/conversation/process",
  "home_assistant_token": "your_home_assistant_token",
  "home_assistant_timeout": 30,
  "home_assistant_enable_pin": false,
  "home_assistant_secure_pin": "1234",
  "home_assistant_enabled": false,
  "home_assistant_channel_index": -1,
  
  "channel_names": {
    "0": "Channel 0",
    "1": "Channel 1",
    "2": "Channel 2",
    "3": "Channel 3",
    "4": "Channel 4",
    "5": "Channel 5",
    "6": "Channel 6",
    "7": "Channel 7",
    "8": "Channel 8",
    "9": "Channel 9"
  },
  
  "reply_in_channels": true,
  "reply_in_directs": true,
  "chunk_size": 200,
  "max_ai_chunks": 5,
  "chunk_delay": 10,
  
  "local_location_string": "@ MY LOCATION",
  "ai_node_name": "Mesh-AI-Alpha",
  "max_message_log": 100,
  
  "enable_twilio": false,
  "enable_smtp": false,
  
  "alert_phone_number": "+15555555555",
  "twilio_sid": "ACXXXXXXXXXXXXXXX",
  "twilio_auth_token": "your_twilio_auth_token",
  "twilio_from_number": "+14444444444",
  
  "smtp_host": "smtp.example.com",
  "smtp_port": 465,
  "smtp_user": "user@example.com",
  "smtp_pass": "your_smtp_password",
  "alert_email_to": [
    "first@example.com",
    "second@example.com",
    "third@example.com"
  ],
  
  "enable_discord": false,
  "discord_webhook_url": "https://discord.com/api/webhooks/XXXXXXXXXXXX/XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
  "discord_send_emergency": false,
  "discord_send_ai": false,
  "discord_send_all": false,
  "discord_response_channel_index": 0,
  "discord_receive_enabled": false,
  "discord_inbound_channel_index": 0,
  "discord_bot_token": "",
  "discord_channel_id": ""
}
```

*Key new options include:*  
- **Discord Settings:** For routing messages to/from Discord.  
- **Enhanced Emergency Routing:** Including support for multiple channels (Twilio, SMTP, Discord).  
- **Improved Logging:** With UTC‑based timestamps and auto‑truncation.

---

## Installation Guide

### A) Prerequisites
- **Windows or Linux PC:** A machine running Windows or Linux (macOS likely as well) - including Raspberry Pi & Linux based ARM architectures!  - Linux instructions soon!
- **Meshtastic Device:** An ESP‑based node (via USB, WiFi, or TCP).  **Make sure all MQTT features are turned off to avoid overwhelming your Node & causing connection errors.
- **Python 3.13+:** Download from [python.org](https://www.python.org/downloads/). Make sure “Add Python to PATH” is checked.
- **Dependencies:** See `requirements.txt` (includes packages like `meshtastic`, `requests`, `Flask`, `twilio`, etc.).

### B) Download & Setup
1. **Obtain the Source:**  
   - Clone the repository from [GitHub](https://github.com/mr-tbot/meshtastic-ai) or copy the **meshtastic-ai** folder.
2. **Create a Virtual Environment (Recommended):**
   ```bash
   cd path\to\meshtastic-ai
   python -m venv venv
   venv\Scripts\activate
   ```
3. **Install Dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
4. **Configure Your Files:**  
   - Edit `config.json`, `commands_config.json`, and `motd.json` as needed.

### C) Running the Bot
1. **Start the Bot:**  
   - Double‑click `Run Mesh-AI - Windows.bat` or run `python meshtastic-ai.py` directly.
2. **Monitor the Console:**  
   - Logs will show connection attempts, AI responses, and any errors.
3. **Access the WebUI:**  
   - Open [http://localhost:5000/dashboard](http://localhost:5000/dashboard) in your browser.

---

## Home Assistant & LLM API Integration

### Home Assistant Integration
- **Enable Integration:**  
  - Set `"home_assistant_enabled": true` in `config.json`.
- **Configure:**  
  - Set `"home_assistant_url"` (e.g., `http://homeassistant.local:8123/api/conversation/process`).
  - Provide `"home_assistant_token"` and adjust `"home_assistant_timeout"`.
- **Security (Optional):**  
  - Enable `"home_assistant_enable_pin": true` and set `"home_assistant_secure_pin"`.
- **Routing:**  
  - Messages on the channel designated by `"home_assistant_channel_index"` are forwarded to Home Assistant.  
  - When PIN mode is enabled, include your PIN in the format `PIN=XXXX your message`.

### LLM API Integration
- **LM Studio:**  
  - Set `"ai_provider": "lmstudio"` and configure `"lmstudio_url"`.
- **OpenAI:**  
  - Set `"ai_provider": "openai"`, provide your API key in `"openai_api_key"`, and choose a model.
- **Ollama:**  
  - Set `"ai_provider": "ollama"` and configure the corresponding URL and model.

---

## Contributing & Disclaimer

- **Alpha Software Notice:**  
  This release (v0.4.1) is experimental. Expect bugs and changes that might affect existing features. Thorough field testing is recommended before production use.
- **Feedback & Contributions:**  
  Report issues or submit pull requests on GitHub. Your input is invaluable.
- **Use Responsibly:**  
  Modifying this code for nefarious purposes is strictly prohibited. Use at your own risk.

---

## Conclusion

Meshtastic-AI Alpha v0.4.1 takes the solid foundation of v0.3.0 and introduces significant improvements in logging, error handling, Discord integration, and emergency alert routing. Whether you’re chatting directly with your node, integrating with Home Assistant, or leveraging multi‑channel alerting (Twilio, Email, Discord), this release offers a more comprehensive and reliable off‑grid AI assistant experience.

**Enjoy tinkering, stay safe, and have fun!**  
Please share your feedback or join our community on GitHub.
