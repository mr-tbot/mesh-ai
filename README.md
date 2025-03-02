
███╗   ███╗███████╗███████╗██╗  ██╗████████╗ █████╗ ███████╗████████╗██╗ ██████╗  █████╗ ██╗
████╗ ████║██╔════╝██╔════╝██║  ██║╚══██╔══╝██╔══██╗██╔════╝╚══██╔══╝██║██╔════╝ ██╔══██╗██║
██╔████╔██║█████╗  ███████╗███████║   ██║   ███████║███████╗   ██║   ██║██║█████╗███████║██║
██║╚██╔╝██║██╔══╝  ╚════██║██╔══██║   ██║   ██╔══██║╚════██║   ██║   ██║██║╚════╝██╔══██║██║
██║ ╚═╝ ██║███████╗███████║██║  ██║   ██║   ██║  ██║███████║   ██║   ██║╚██████╗ ██║  ██║██║
╚═╝     ╚═╝╚══════╝╚══════╝╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝
                                                                                            
# Meshtastic-AI (Alpha v0.2.2)

**Meshtastic-AI** is an experimental project that adds AI chatbot and extended features to your [Meshtastic](https://meshtastic.org) LoRa mesh network. It allows you to interact with a conversational AI offline (via local models) or online (via OpenAI), integrates with Home Assistant, can send emergency alerts, and is highly configurable through JSON.

> **Disclaimer:**  
> This is **alpha software** and should **not** be relied upon for mission-critical or emergency use. It may be unstable or incomplete. Proceed with caution, and always have alternative communication methods available - modification of this code for nefarious purposes is strictly frowned upon.  Please use responsibly.

## Features

- **Multiple AI Providers**  
  - **Local (LM Studio, Ollama)** or **OpenAI** for GPT-based responses.
- **Home Assistant Integration**  
  - Redirect entire chat channels to your Home Assistant conversation API, optionally protected with a PIN.
- **Slash Commands**  
  - Built-in commands: `/ping`, `/test`, `/help`, `/motd`, `/ai`, `/emergency`, `/whereami`, plus custom commands via `commands_config.json`.
- **Emergency Alerts**  
  - Send SMS or email (via Twilio / SMTP) or Discord webhook when `/emergency` is triggered.  
- **Message Chunking**  
  - Large AI responses are split into smaller pieces, so you don’t overwhelm the LoRa network.
- **REST API**  
  - A built-in Flask server to read logs (`/messages`), see a web-based dashboard (`/dashboard`), or programmatically send messages (`/send`).
- **Response Chunking and token logic**  
  - Automatically chunks AI responses into multiple messages with delays to reduce strain on the mesh network & respect radio duty cycles - logic in the code automatically calculates maximum token usage for the AI API to avoid response truncation.
- **Windows-Focused**  
  - This version officially supports Windows. Linux & Mac support is planned for a future release.
  
## 1. Changelog: v0.1 → v0.2.2

Below is a high-level overview of the most notable changes and additions since the v0.1 release.

1. **Expanded Configuration & JSON Files**  
   - **New `config.json` fields**  
     - Added `debug` toggle for verbose debugging.  
     - Added options for multiple AI providers (`lmstudio`, `openai`, `ollama`), including timeouts and endpoints.  
     - Introduced **Home Assistant** integration toggles (`home_assistant_enabled`, `home_assistant_channel_index`, secure pin, etc.).  
     - Implemented **Twilio** and **SMTP** settings for emergency alerts (including phone number, email, and credentials).  
     - Added **Discord** webhook configuration toggles (e.g., `enable_discord`, `discord_send_emergency`, etc.).  
     - Several new user-configurable parameters to control message chunking (`chunk_size`, `max_ai_chunks`, and `chunk_delay`) to reduce radio congestion.  

2. **Support for Multiple AI Providers**  
   - **Local Language Models** (LM Studio, Ollama) and **OpenAI** (GPT-3.5, etc.) can be selected via `ai_provider`.  
   - Behavior is routed depending on which provider you specify in `config.json`.

3. **Home Assistant Integration**  
   - Option to route messages on a dedicated channel directly to Home Assistant’s conversation API.  
   - **Security PIN** requirement can be enabled, preventing unauthorized control of Home Assistant.  

4. **Improved Command Handling**  
   - Replaced single-purpose code with a new, flexible **commands system** loaded from `commands_config.json`.  
   - Users can define custom commands that either have direct string responses or prompt an AI.  
   - Built-in commands now include `/ping`, `/test`, `/emergency`, `/whereami`, `/help`, `/motd`, and more.  

5. **Emergency Alert System**  
   - `/emergency` (or `/911`) triggers optional Twilio SMS, SMTP email, and/or Discord alerts.  
   - Retrieves node GPS coordinates (if available) to include location in alerts.  

6. **Improved Message Chunking & Throttling**  
   - Long AI responses are split into multiple smaller segments (configurable via `chunk_size` & `max_ai_chunks`).  
   - Delays (`chunk_delay`) between chunks to avoid flooding the mesh network.  

7. **REST API Endpoints** (via built-in Flask server)  
   - `GET /messages`: Returns the last 100 messages in JSON.  
   - `GET /dashboard`: Displays a simple HTML dashboard showing the recently received messages.  
   - `POST /send`: Manually send messages to nodes (direct or broadcast) from external scripts or tools.  

8. **Improved Logging and File Structure**  
   - **`messages.log`** for persistent logging of all incoming messages, commands, and emergencies.  
   - Distinct JSON config files: `config.json`, `commands_config.json`, and `motd.json`.  

9. **Refined Startup & Script Structure**  
   - A new `Run Mesh-AI - Windows.bat` script for straightforward Windows startup.  
   - Added disclaimers for alpha usage throughout the code.  
   - Streamlined reconnection and exception handling logic with more robust error-handling.  

10. **General Stability & Code Quality Enhancements**  
   - Thorough refactoring of the code to be more modular and maintainable.  
   - Better debugging hooks, improved concurrency handling, and safer resource cleanup.  

---


## Quick Start (Windows)

1. **Download / Clone** this repository or place the **meshtastic-ai** folder on your Desktop.  
2. **Install Dependencies** (see [Installation Guide](#installation-guide) below for details).  
3. **Configure** `config.json` and other `.json` files as needed.  
4. **Double-click** `Run Mesh-AI - Windows.bat`.  
5. Meshtastic-AI will launch the Flask server and try to connect to your Meshtastic device over Serial or TCP.  
6. Once connected, open a terminal (or your Meshtastic device) and send commands like `/ping` or `/ai hello!`  
7. (Optional) Visit [http://localhost:5000/dashboard](http://localhost:5000/dashboard) to see the built-in dashboard.

## Basic Usage

- **Talk to the AI:**  
  - Send a direct message to the AI node (or a recognized shortName) using `/ai`, or just DM it if configured.  
  - Example: `/ai Hello, how are you?`
- **Check your location:**  
  - `/whereami` attempts to print your GPS coordinates (if your node has them).
- **Emergency Alerts:**  
  - Send `/emergency <message>` to trigger Twilio SMS/Email/Discord notifications (if configured).
- **Home Assistant:**  
  - If enabled, any message on the designated channel index is forwarded to Home Assistant’s conversation. If a PIN is required, include `PIN=XXXX` in the message.

---

## 3. Installation Guide

Below is a detailed guide for setting up **Meshtastic-AI Alpha v0.2.2** on Windows.

### A) Prerequisites

1. **Python 3.9+**  
   - Install from [python.org](https://www.python.org/downloads/) or confirm Python 3.9+ is on your system.  
   - Make sure to check “Add Python to PATH” during installation.

2. **Meshtastic Device**  
   - A working Meshtastic node with either a USB serial connection or a WiFi/TCP interface (ESP32-based devices) on the same network.

3. **Dependencies**  
   - The main Python dependencies are listed in `requirements.txt`. They include:  
     - `meshtastic==2.5.12`  
     - `requests`  
     - `Flask`  
     - `twilio` (for SMS)  
     - `pubsub`  
     - etc.  

### B) Download & Folder Setup

1. **Obtain the Source**  
   - Either clone the [GitHub repository](https://github.com/mr-tbot/meshtastic-ai) or copy the **meshtastic-ai** folder to your Desktop.  
2. **(Recommended) Create a Virtual Environment**  
   ```bash
   cd path\to\meshtastic-ai
   python -m venv venv
   venv\Scripts\activate
   ```
3. **Install Requirements**  
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

### C) Configure `config.json`

Open `config.json` in any text editor. Below is a breakdown of important fields (this is only a partial list—see file for all):

```json
{
  "debug": false,
  "use_mesh_interface": false,
  "use_wifi": true,
  "wifi_host": "YOUR_MESHTASTIC_NODE_IP",
  "wifi_port": 4403,

  "serial_port": "",
  "ai_provider": "lmstudio",
  "system_prompt": "You are a helpful assistant responding to mesh network chats.",

  "lmstudio_url": "http://localhost:1234/v1/chat/completions",
  "lmstudio_timeout": 60,

  "openai_api_key": "YOUR_OPENAI_API_KEY",
  "openai_model": "gpt-3.5-turbo",
  "openai_timeout": 30,

  "ollama_url": "http://localhost:11434/api/generate",
  "ollama_model": "llama3",
  "ollama_timeout": 60,

  "home_assistant_url": "http://YOUR_HOME_ASSISTANT_URL:8123/api/conversation/process",
  "home_assistant_token": "YOUR_HOME_ASSISTANT_BEARER_TOKEN",
  "home_assistant_timeout": 60,
  "home_assistant_enable_pin": false,
  "home_assistant_secure_pin": "1234",

  "home_assistant_enabled": false,
  "home_assistant_channel_index": 6,

  "chunk_size": 200,
  "max_ai_chunks": 4,
  "chunk_delay": 10,
  "local_location_string": "YourLocationStringHere",
  "ai_node_name": "Mesh-AI-Node",
  "force_node_num": null,

  "enable_twilio": false,
  "enable_smtp": true,
  ...
}
```

Key points:

- **`debug`**  
  - Set to `true` for verbose logs in the console.
- **Connection Options**  
  - **`use_wifi`** & `wifi_host`: Enable if you have a WiFi-enabled Meshtastic device.  
  - **`serial_port`**: If you prefer USB direct connection (Windows often uses something like `COM3`). Leave blank to auto-detect.
- **AI Provider**  
  - `"ai_provider": "lmstudio"`: Uses a local LLM via LM Studio.  
  - `"ai_provider": "openai"`: Routes user queries to the OpenAI API (requires `openai_api_key`).  
  - `"ai_provider": "ollama"`: Uses a local LLaMA-based server.  
- **Home Assistant**  
  - **`home_assistant_enabled`**: Whether to enable routing.  
  - **`home_assistant_channel_index`**: The channel index that triggers Home Assistant.  
  - **`home_assistant_enable_pin`**: If `true`, messages must include `PIN=XXXX` to be passed to Home Assistant.  
- **Message Chunking**  
  - `chunk_size` and `max_ai_chunks`: Controls how messages are split to avoid overwhelming the LoRa network.  
  - `chunk_delay`: Delay (in seconds) between sending each chunk.  
- **Emergency Settings** (Email or Twilio)  
  - **`enable_twilio`** / **`enable_smtp`** toggles.  
  - Fill in Twilio or SMTP credentials if you want to use them for `/emergency`.  
- **Discord Settings**  
  - `enable_discord` and `discord_webhook_url` to forward messages or emergencies to Discord.

### D) Configure `commands_config.json`

This file defines custom slash commands. For example:

```json
{
  "commands": [
    {
      "command": "/ping",
      "response": "Pong!"
    },
    {
      "command": "/weather",
      "response": "Currently, local weather is unknown. (This is a placeholder.)"
    },
    {
      "command": "/funfact",
      "ai_prompt": "Give me a fun fact about {user_input}"
    }
  ]
}
```

- **`command`**: The slash command text, e.g. `/funfact`.  
- **`response`**: A static string to return immediately.  
- **`ai_prompt`**: A dynamic AI-based command, combining the user’s input into the prompt.  

### E) Configure `motd.json`

Contains a simple string displayed by `/motd`:

```json
"Welcome to the Meshtastic AI Chat Bot by MR-TBOT.COM! Enjoy your stay off the grid."
```

You can edit this text to change the “Message of the Day.”

### F) Running the Bot

1. **Double-click** `Run Mesh-AI - Windows.bat` in the main folder.  
2. A console window will appear, showing logs and attempt to connect to your Meshtastic device.  
3. After successful connection, you should see:

   ```
   Starting Meshtastic-AI server...
   Launching Flask in the background on port 5000...
   Attempting to connect to Meshtastic device...
   ...
   Subscribing to on_receive callback...
   Connection successful. Running until error or Ctrl+C.
   ```

4. **Test** by sending messages on your Meshtastic device. For instance, send `/ping` or `/test` from your node.  
5. Optionally, open [http://localhost:5000/dashboard](http://localhost:5000/dashboard) in your browser to see recent messages.

---

## 4. Using the API

Meshtastic-AI starts a local **Flask** server on port **5000** by default. Three main endpoints exist:

1. **GET `/messages`**  
   - Returns the most recent 100 messages in JSON format.  
   - Example:
     ```bash
     curl http://localhost:5000/messages
     ```

2. **GET `/dashboard`**  
   - Shows a simple HTML page with the latest messages.

3. **POST `/send`**  
   - Allows you to send messages from external scripts or other services to the mesh.  
   - Expects JSON:  
     ```json
     {
       "message": "Hello from API!",
       "node_id": "!433e231c",
       "channel_index": 0,
       "direct": false
     }
     ```
   - `node_id` can be a hex-based Meshtastic ID (like `!433e231c`) or a broadcast address.  
   - `channel_index` is optional (defaults to 0).  
   - `direct` can be `true` for direct messages or `false` for a broadcast.

---

## 5. Home Assistant Integration

1. **Enable**  
   - In `config.json`, set `"home_assistant_enabled": true` and pick a `home_assistant_channel_index` that you want to dedicate to Home Assistant.  

2. **API Token & URL**  
   - Provide your Home Assistant conversation URL in `home_assistant_url`, typically something like:  
     ```
     http://<YOUR-HA-IP>:8123/api/conversation/process
     ```
   - Include a valid token in `home_assistant_token`:  
     ```json
     "home_assistant_token": "YOUR_HOME_ASSISTANT_BEARER_TOKEN"
     ```
3. **PIN Protection (Optional)**  
   - If `"home_assistant_enable_pin": true`, you must include `PIN=XXXX` in your chat messages, or Meshtastic-AI will refuse to relay them.  
4. **Send Commands**  
   - Any message on the configured channel (for instance, channel index 6) automatically routes to Home Assistant’s conversation engine.  
   - The Home Assistant response is returned as text, which is forwarded back to your Meshtastic device.

---

## 6. Supported LLM APIs

### A) LM Studio
- **Local** large language models served by LM Studio at the URL in `lmstudio_url`.
- `lmstudio_timeout` can be increased if your model is slow to respond.

### B) OpenAI
- Provide your `openai_api_key`, set `"ai_provider": "openai"`, and specify the model name (`gpt-3.5-turbo`, etc.).
- Keep an eye on your **API usage and costs**.

### C) Ollama
- Another local LLM server. Specify `ollama_url` and `ollama_model`.
- `ollama_timeout` is also configurable.

---

## 7. Disclaimers & Next Steps

- **Alpha Software**  
  - This version (v0.2.2) is still in **alpha**. Expect bugs, incomplete features, and potential instability.
- **Not for Emergencies**  
  - Do not depend solely on this system for any life-critical or mission-critical scenarios.  
  - Always have backup communication methods available.
- **Linux & macOS Support**  
  - Currently, the packaged scripts are tailored to Windows. Linux/macos instructions will come soon.  
- **Contributions**  
  - If you find a bug or want to help, please open an issue on GitHub or submit a pull request.

---

## 8. Conclusion

By following this guide, you’ll have an **off-grid AI assistant** on your Meshtastic network, complete with custom slash commands, optional Home Assistant integration, and multiple AI backend choices. Enjoy tinkering with **Meshtastic-AI** and help shape its evolution by providing feedback on GitHub!

**Stay safe, and have fun!**

---

**End of Documentation**  

> **Thank you for using Meshtastic-AI Alpha v0.2.2!**  

Please report any issues or ideas on the project’s GitHub.

I am actively looking for people to help support this project!  Please reach out to get involved!
