# Meshtastic-AI (Alpha v0.3.0)


![image](https://github.com/user-attachments/assets/bffe7a1c-3cbe-4e1d-b585-d8b3a0684128)


**Meshtastic-AI** (MESH-AI for short) is an experimental project that bridges [[Meshtastic](https://meshtastic.org/)]LoRa mesh networks with powerful AI chatbots. In this release, the project has received a major overhaul in its WebUI along with extensive improvements in error handling, logging, and message routing options. Whether you use local models (LM Studio, Ollama) or OpenAI, or even integrate with Home Assistant, you now enjoy a more robust off-grid AI assistant experience.

> **Disclaimer:**  
>  
> This project is NOT ASSOCIATED with the official Meshtastic Project. It is provided as an extension to help you add AI and advanced features to your Meshtastic network.  
>  
> **Alpha Software Warning:**  
> This version is still in alpha. It may be unstable or incomplete, so please avoid relying on it for mission-critical or emergency use. Always have backup communication methods available, and please use responsibly.  
>  
> *I am one robot using other robots to write this code. Some features are still untested in the field. Check the GitHub issues for fixes or feedback!*

---

## Features

- **Multiple AI Providers**  
  - **Local** (LM Studio, Ollama) or **OpenAI** for GPT-based responses.
- **Home Assistant Integration**  
  - Seamlessly forward chat messages to Home Assistant’s conversation API (optionally secured with a PIN).
- **Advanced Slash Commands**  
  - Built-in commands include `/about`, `/ping`, `/test`, `/help`, `/motd`, `/ai`, `/emergency`, `/whereami`, plus custom commands via `commands_config.json`.
- **Emergency Alerts**  
  - Trigger SMS (Twilio), email (SMTP), and Discord notifications using the `/emergency` command.
- **Enhanced REST API & WebUI**  
  - A completely revamped Flask-based dashboard provides:
    - **Live Messaging Dashboard** with three-column layout for broadcast messages, direct messages, and available nodes.
    - **UI Customization** via a settings panel (theme color, hue rotation, custom sound, etc.).
    - Additional endpoints: `/messages`, `/nodes`, `/connection_status`, `/send`, and `/ui_send` (for sending messages directly from the WebUI).
- **Improved Message Chunking & Routing**  
  - Automatic splitting of long AI responses into up to 5 chunks (configurable) with configurable delays to reduce radio congestion.
  - New configuration options allow you to toggle whether the bot replies to direct messages and/or channel messages.
- **Robust Error Handling & Reconnection Logic**  
  - Enhanced logging with a dedicated script log file (with auto-truncation) and verbose console output.
  - Automatic detection of connection issues with threaded monitoring and graceful reconnects.
  - Thread exception hooks to log and recover from runtime errors.
- **Windows-Focused (with planned Linux/macOS support)**  
  - This version officially supports Windows environments. Linux & macOS instructions are coming soon.

---

## 1. Changelog: v0.2.2 → v0.3.0

### WebUI Overhaul
- **Redesigned Dashboard:**  
  The built-in dashboard now features a modern three-column layout:
  - **Channel Messages:** View broadcast messages in real time.
  - **Available Nodes:** See a live list of nodes with options to directly message (DM) them.
  - **Direct Messages:** Separate panel for DM conversations.
- **Enhanced UI Interactivity:**  
  - A new send-message form with toggleable message mode (direct vs. broadcast).
  - Dynamic character counting and message chunk preview.
  - A settings panel to customize theme color, enable hue rotation, and set custom incoming message sounds.
  - A scrolling ticker and quick-access header buttons (e.g., view logs).
  
  
![image](https://github.com/user-attachments/assets/8125b5a3-a1ca-4bf4-b349-c0cd83433372)



### Improved Error Handling and Stability
- **Verbose Logging & Script Log File:**  
  - All stdout and stderr are redirected to an in-memory log as well as to a persistent `script.log` file with auto-truncation.
- **Connection Monitoring:**  
  - Added a connection monitor thread that detects disconnections and triggers a reconnect automatically.
- **Thread Exception Hook:**  
  - Implemented Python’s threading exception hook to capture and log runtime errors for better debugging and reliability.

### Enhanced Message Routing & AI Response Options
- **Configurable Reply Modes:**  
  - New configuration flags (`reply_in_channels` and `reply_in_directs`) allow you to control whether the AI should respond to broadcast messages and/or direct messages.
- **Extended Message Chunking:**  
  - Maximum message chunks increased (default now up to 5) to support longer AI responses without flooding the network.
- **Improved Command Handling:**  
  - Updated slash command processing including a new `/about` command.
  - Custom commands in `commands_config.json` continue to work with dynamic AI prompts.

### Expanded API Endpoints
- **New `/nodes` Endpoint:**  
  - Retrieve a live list of connected nodes as JSON.
- **Updated `/connection_status` Endpoint:**  
  - Get detailed status information including connection errors.
- **New `/ui_send` Endpoint:**  
  - Specifically designed for messages sent through the WebUI, supporting both direct and broadcast modes.

### Other Improvements
- **Home Assistant Integration:**  
  - More robust handling including optional secure PIN support.
- **Emergency Alert Enhancements:**  (STILL WIDELY UNTESTED.  DO NOT RELY ON THESE FEATURES)
  - Expanded support for Discord alerts in addition to Twilio and SMTP.
- **Refined Startup & Reconnection Logic:**  
  - Cleaner reconnection loops and resource cleanup on errors.

---

## 2. Quick Start (Windows)

1. **Download/Clone** this repository or copy the **meshtastic-ai** folder to your Desktop.
2. **Install Dependencies:**  
   - Follow the [[Installation Guide](https://chatgpt.com/g/g-p-67c3129aef7c8191947e4134e61baf8f-meshtastic-ai/c/67caeff9-f0d4-8006-8e79-24fcee0104ca#installation-guide)](#installation-guide) for dependency setup.
3. **Configure** `config.json`, `commands_config.json`, and `motd.json` (see [[Configuration](https://chatgpt.com/g/g-p-67c3129aef7c8191947e4134e61baf8f-meshtastic-ai/c/67caeff9-f0d4-8006-8e79-24fcee0104ca#configuration)](#configuration) below).
4. **Double-click** `Run Mesh-AI - Windows.bat` to start the server.
5. The Meshtastic-AI server launches the Flask WebUI on port **5000** and connects to your Meshtastic device.
6. **Test the Setup:**  
   - Send commands like `/ping` or `/ai hello!` from your Meshtastic device.
   - For direct DM interaction, simply send a message without a command.
7. **Explore the WebUI:**  
   - Open [http://localhost:5000/dashboard](http://localhost:5000/dashboard) in your browser to view the updated dashboard.
8. (Optional) If Home Assistant integration is enabled, configure the dedicated channel index and secure PIN settings as needed.

---

## 3. Basic Usage

- **Interacting with the AI:**  
  - Use `/ai` (or aliases `/bot`, `/query`, `/data`) followed by your message to get a response.
  - For direct messages, simply DM the AI node (if configured to reply to direct messages).
- **Location Query:**  
  - Send `/whereami` to retrieve your node’s GPS coordinates (if available).
- **Emergency Alerts:**  
  - Trigger an emergency with `/emergency <message>` or `/911 <message>`. Alerts are sent via SMS, email, and/or Discord (if configured).  GPS data of the alerting Meshtastic node is pulled into the message .
- **Home Assistant:**  
  - Messages on the dedicated channel (configured via `home_assistant_channel_index`) are routed to Home Assistant’s conversation API. If secure PIN mode is enabled, include `PIN=XXXX` in your message.
- **WebUI Messaging:**  
  - Use the dashboard’s send-message form to broadcast or directly message other nodes. The mode toggle and node selection facilitate quick replies.

---

## 4. Using the API

The Meshtastic-AI server starts a Flask server on port **5000** by default. The key endpoints include:

- **GET `/messages`:**  
  Retrieve the last 100 messages in JSON format.
- **GET `/nodes`:**  
  Get a live list of connected nodes.
- **GET `/connection_status`:**  
  Check the current connection status and error details.
- **GET `/dashboard`:**  
  Access the full WebUI dashboard.
- **POST `/send`:**  
  Send a message programmatically.  
  *Example JSON payload:*
  ```json
  {
    "message": "Hello from API!",
    "node_id": "!433e231c",
    "channel_index": 0,
    "direct": false
  }
  ```
- **POST `/ui_send`:**  
  Endpoint used by the WebUI form to send messages (supports both direct and broadcast modes).

---

## 5. Configuration

The `config.json` file has been updated to include new options for reply modes, UI settings, and additional endpoint configurations. An example configuration is shown below:

```json
{
  "debug": false,
  "use_mesh_interface": false,
  "use_wifi": true,
  "wifi_host": "<MESHTASTIC NODE IP HERE>",
  "wifi_port": 4403,

  "serial_port": "",
  "ai_provider": "<lmstudio, openai, or ollama>",
  "system_prompt": "You are a helpful assistant responding to mesh network chats. Respond in as few words as possible while still answering fully.",

  "lmstudio_url": "http://localhost:1234/v1/chat/completions",
  "lmstudio_timeout": 60,

  "openai_api_key": "",
  "openai_model": "gpt-3.5-turbo",
  "openai_timeout": 60,

  "ollama_url": "http://localhost:11434/api/generate",
  "ollama_model": "llama2",
  "ollama_timeout": 60,

  "home_assistant_url": "http://homeassistant.local:8123/api/conversation/process",
  "home_assistant_token": "<INPUT HA TOKEN HERE>",
  "home_assistant_timeout": 90,
  "home_assistant_enable_pin": false,
  "home_assistant_secure_pin": "1234",

  "home_assistant_enabled": false,
  "home_assistant_channel_index": 1,

  "channel_names": {
    "0": "LongFast",
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
  "max_ai_chunks": 4,
  "chunk_delay": 10,
  "local_location_string": "@ <YOUR LOCATION STRING HERE>",
  "ai_node_name": "Mesh-AI-Alpha",
  "max_message_log": 0,

  "enable_twilio": false,
  "enable_smtp": false,
  "alert_phone_number": "+15555555555",
  "twilio_sid": "<TWILIO_SID>",
  "twilio_auth_token": "<TWILIO_AUTH_TOKEN>",
  "twilio_from_number": "+14444444444",

  "smtp_host": "<SMTP HOST HERE>",
  "smtp_port": 465,
  "smtp_user": "<SMTP USER HERE>",
  "smtp_pass": "<SMTP PASS HERE>",
  "alert_email_to": "<ALERT EMAIL HERE>",

  "enable_discord": false,
  "discord_webhook_url": "",
  "discord_send_emergency": false,
  "discord_send_ai": false,
  "discord_send_all": false
}
```

*Key new options:*
- **`reply_in_channels` / `reply_in_directs`:** Control whether the AI responds to broadcast channels and/or direct messages.
- **`channel_names`:** Customize the display names for channels (the WebUI will use these names).
- **Enhanced timeout and chunk settings** for more robust AI interactions.

---

## 6. Installation Guide

### A) Prerequisites

- **Windows PC:** A machine running Windows.
- **Meshtastic Device:** An ESP-based Meshtastic node (with USB, WiFi, or TCP connectivity).
- **Python 3.9+:** Install from [[python.org](https://www.python.org/downloads/)](https://www.python.org/downloads/) (ensure you check “Add Python to PATH”).
- **Dependencies:** Listed in `requirements.txt` (includes `meshtastic`, `requests`, `Flask`, `twilio`, etc.).

### B) Download & Setup

1. **Obtain the Source:**  
   - Clone the [[GitHub repository](https://github.com/mr-tbot/meshtastic-ai)](https://github.com/mr-tbot/meshtastic-ai) or copy the **meshtastic-ai** folder to your Desktop.
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

### C) Configure Your Files

- Edit `config.json`, `commands_config.json`, and `motd.json` as needed.
- See the [[Configuration](https://chatgpt.com/g/g-p-67c3129aef7c8191947e4134e61baf8f-meshtastic-ai/c/67caeff9-f0d4-8006-8e79-24fcee0104ca#configuration)](#configuration) section above for details.

### D) Running the Bot

1. **Start the Bot:**  
   - Double-click `Run Mesh-AI - Windows.bat` or run the main script via your Python environment.
2. **Monitor the Console:**  
   - Logs will show connection attempts, AI responses, and any errors.
3. **Access the WebUI:**  
   - Open [http://localhost:5000/dashboard](http://localhost:5000/dashboard) in your browser to interact with the dashboard.

---

## 7. Home Assistant & LLM API Integration

### Home Assistant
- Enable by setting `"home_assistant_enabled": true` in `config.json`.
- Configure the API URL, token, and optionally secure PIN settings.
- Any message on the designated channel (e.g., channel 1) will be forwarded to Home Assistant.

### LLM APIs
- **LM Studio:** Set `"ai_provider": "lmstudio"` and configure the LM Studio URL.
- **OpenAI:** Set `"ai_provider": "openai"`, provide your OpenAI API key, and select the model.
- **Ollama:** Set `"ai_provider": "ollama"` and configure the URL/model details.

---

## 8. Contributing & Disclaimer

- **Alpha Software Notice:**  
  This release (v0.3.0) is still experimental. Expect bugs and changes that might affect existing features.  A lot of this is not field tested...  
- **Feedback & Contributions:**  
  Please report issues or submit pull requests on GitHub. Your input and participation is invaluable for improving the project.
- **Use Responsibly:**  
  Modification of this code for nefarious purposes is strictly frowned upon.

---

## 9. Conclusion

Meshtastic-AI Alpha v0.3.0 brings a powerful new WebUI, enhanced stability, and greater configurability to your Meshtastic network’s AI assistant. Whether you’re chatting directly with your node or managing your Home Assistant offline -  this release helps you stay connected—even off the grid.

**Enjoy tinkering, stay safe, and have fun!**

**Thank you for using Meshtastic-AI Alpha v0.3.0!**  
Please share your feedback or join our community on GitHub.
