# Meshtastic-AI (Alpha v0.4.0)

![image](https://github.com/user-attachments/assets/7250e722-3f7e-49f2-9439-9b8ad75a1981)

**Meshtastic-AI** (MESH-AI for short) is an experimental project that bridges [Meshtastic](https://meshtastic.org/) LoRa mesh networks with powerful AI chatbots. This release represents a major upgrade from v0.3.0 with refined logging, enhanced error handling, and expanded integration options for emergency alerts and message routing. Whether you’re using local models (LM Studio, Ollama) or OpenAI – or integrating with Home Assistant – you now enjoy a more robust off‑grid AI assistant experience.

> **Disclaimer:**  
> This project is NOT ASSOCIATED with the official Meshtastic Project. It is provided solely as an extension to enhance your Meshtastic network with advanced AI and connectivity features.  
>  
> **Alpha Software Warning:**  
> This version is still in alpha. It may be unstable or incomplete so please avoid relying on it for mission‑critical or emergency use. Always have backup communication methods available and use responsibly.  
>  
> *I am one robot using other robots to write this code. Some features are still untested in the field. Check the GitHub issues for fixes or feedback!*

---

## Features

- **Multiple AI Providers**  
  - Use **Local** models (LM Studio, Ollama), **OpenAI**, or even integrate with **Home Assistant**.
- **Home Assistant Integration**  
  - Seamlessly forward messages from a designated channel to Home Assistant’s conversation API. Optionally secure this with a PIN.
- **Advanced Slash Commands**  
  - Built‑in commands include `/about`, `/ping`, `/test`, `/help`, `/motd`, `/ai` (and its aliases), `/emergency` (or `/911`), `/whereami`, plus support for custom commands defined in `commands_config.json`.  
  - Slash commands are now **case‑insensitive**.
- **Emergency Alerts**  
  - Trigger alerts that are routed via **Twilio SMS**, **SMTP Email**, and **Discord** (if enabled). Alerts include node GPS data and UTC timestamp.
- **Enhanced REST API & WebUI**  
  - A revamped Flask‑based dashboard offers:  
    - **Live Messaging Dashboard** with three panels (broadcast messages, direct messages, and node list).
    - **UI Customization** via a settings panel (theme color, hue rotation, custom sounds, etc.).
    - New API endpoints including `/messages`, `/nodes`, `/connection_status`, `/logs`, `/send`, `/ui_send`, and a new `/discord_webhook` for Discord inbound messages.
- **Improved Message Chunking & Routing**  
  - Automatically split long AI responses into multiple chunks (up to a configurable maximum) with delays to reduce radio congestion.
  - Configurable flags allow you to choose whether the bot replies to direct messages and/or channel messages.
- **Robust Error Handling & Logging**  
  - Uses UTC‑based timestamps, an auto‑truncating script log file, and improved error detection/reconnection logic (including threaded exception hooks).
- **Cross‑Platform (Windows‑Focused)**  
  - Official support for Windows, with Linux/macOS instructions coming soon.
- **New Discord Integration**  
  - Route messages to and from Discord. The WebUI dashboard now shows Discord messages if enabled, and a new `/discord_webhook` endpoint allows inbound Discord messages to be processed.

---

## Quick Start (Windows)

1. **Download/Clone** the repository or copy the **meshtastic-ai** folder to your Desktop.
2. **Install Dependencies:**  
   - Follow the instructions in `requirements.txt` for dependency setup.
3. **Configure Files:**  
   - Update `config.json`, `commands_config.json`, and `motd.json` as detailed below.
4. **Start the Bot:**  
   - Double‑click `Run Mesh-AI - Windows.bat` or run `python meshtastic-ai.py` from your Python environment.
5. **Access the WebUI:**  
   - Open [http://localhost:5000/dashboard](http://localhost:5000/dashboard) to view the dashboard.

---

## Detailed Setup & Configuration

### A) General Configuration
Update your `config.json` with the following key settings:

- **Basic Settings:**
  - `"debug"`: Enable verbose logging if needed.
  - `"serial_port"`, `"use_mesh_interface"`, `"use_wifi"`, `"wifi_host"`, `"wifi_port"`: Set your connectivity options.
  - `"system_prompt"`: Customize the system message for AI responses.
  - `"ai_provider"`: Choose between `"lmstudio"`, `"openai"`, `"ollama"`, or `"home_assistant"`.

- **Message Routing & Chunking:**
  - `"chunk_size"`: Maximum characters per message chunk.
  - `"max_ai_chunks"`: Maximum number of chunks an AI response is split into.
  - `"chunk_delay"`: Delay (in seconds) between sending each chunk.
  - `"reply_in_channels"` and `"reply_in_directs"`: Toggle whether the bot replies to channel broadcasts or direct messages.
  - `"channel_names"`: Customize display names for your channels.
  - `"local_location_string"`: Set your node’s location description.
  - `"ai_node_name"`: Name of the AI node (appears in responses).
  - `"max_message_log"`: Maximum number of messages to retain in log.

### B) Home Assistant Integration
To integrate with Home Assistant:
  
- Set `"home_assistant_enabled": true` in your `config.json`.
- Provide your Home Assistant details:
  - `"home_assistant_url"`: e.g., `"http://homeassistant.local:8123/api/conversation/process"`
  - `"home_assistant_token"`: Your Home Assistant API token.
  - `"home_assistant_timeout"`: Request timeout (seconds).
- **Optional Security:**  
  - Enable secure PIN mode with `"home_assistant_enable_pin": true` and set `"home_assistant_secure_pin": "XXXX"`.
- **Routing:**  
  - Use `"home_assistant_channel_index"` to designate the channel from which messages are forwarded to Home Assistant.  
  - When sending a message on this channel, if PIN mode is enabled, include your PIN (format: `PIN=XXXX your message`).

### C) Twilio SMS Integration
For SMS functionality via Twilio:

- Set `"enable_twilio": true`.
- Provide your Twilio credentials:
  - `"twilio_sid"`: Your Twilio Account SID.
  - `"twilio_auth_token"`: Your Twilio Auth Token.
  - `"twilio_from_number"`: The Twilio phone number used to send messages.
  - `"alert_phone_number"`: The recipient phone number for emergency alerts.
- **Usage:**  
  - Use the `/sms <phone_number> <message>` command to send SMS manually.
  - Emergency alerts (triggered via `/emergency` or `/911`) will also route through Twilio if configured.

### D) SMTP Email Integration
To send emergency alerts via email:

- Set `"enable_smtp": true`.
- Configure your SMTP settings:
  - `"smtp_host"`: e.g., `"smtp.example.com"`.
  - `"smtp_port"`: Typically `465` (SSL) or `587` (TLS).
  - `"smtp_user"` and `"smtp_pass"`: Your email login credentials.
  - `"alert_email_to"`: An email address or list of addresses (e.g., `[ "first@example.com", "second@example.com" ]`).

### E) Discord Integration
Enhance your setup by integrating Discord:

- Set `"enable_discord": true`.
- Provide the webhook URL:  
  - `"discord_webhook_url"`: Your Discord webhook URL.
- Configure additional Discord settings:
  - `"discord_send_emergency"`: If true, emergency alerts are posted to Discord.
  - `"discord_send_ai"`: If true, AI responses are forwarded to Discord.
  - `"discord_send_all"`: If true, all messages on the inbound channel are sent to Discord.
  - `"discord_inbound_channel_index"`: Designate which Meshtastic channel’s messages should be forwarded to Discord.
  - Optionally, set `"discord_bot_token"` and `"discord_channel_id"` if you plan on more advanced interactions.
- **New Webhook Endpoint:**  
  - The `/discord_webhook` endpoint allows external systems (or a Discord bot) to post messages into the Meshtastic network.

---

## Using the API
The Meshtastic-AI server starts a Flask server on port **5000** by default. Key endpoints include:

- **GET `/messages`**  
  Retrieve the latest messages in JSON format.
- **GET `/nodes`**  
  Get a list of connected nodes.
- **GET `/connection_status`**  
  View connection status and error details.
- **GET `/logs`**  
  Display a styled log view with uptime and recent log entries.
- **GET `/dashboard`**  
  Access the full WebUI dashboard.
- **POST `/send`** and **POST `/ui_send`**  
  Programmatically send messages.
- **POST `/discord_webhook`**  
  Receive messages from Discord (if enabled).

---

## Detailed Changelog: v0.3.0 → v0.4.0

**1. Logging & Timestamps**  
- **v0.3.0:** Timestamps were generated using local time.  
- **v0.4.0:** Logging now uses UTC-based timestamps (via Python’s `timezone.utc`), ensuring consistency across distributed nodes. The log file auto‑truncates when exceeding 100 MB by keeping the last 100 lines.  
*(See v0.4.0 code changes – citeturn0file0 vs. citeturn0file1)*

**2. Discord Integration Enhancements**  
- **v0.3.0:** Limited or no built‑in support for Discord routing.  
- **v0.4.0:**  
  - Added new configuration variables such as `discord_inbound_channel_index`, `discord_bot_token`, and `discord_channel_id`.  
  - Introduced a new `/discord_webhook` endpoint to allow inbound Discord messages to be processed and displayed on the WebUI.  
  - Expanded emergency alert capabilities to include Discord notifications if enabled.  
*(Refer to the new Discord-related code in v0.4.0 – citeturn0file0)*

**3. Emergency Alerts**  
- **v0.3.0:** Emergency alerts were sent via SMS and SMTP if configured.  
- **v0.4.0:** Emergency notifications now include additional context (e.g., GPS coordinates, UTC timestamp) and can also be sent via Discord. The routing logic checks configuration for each channel before attempting delivery.  
*(Changes seen in the `send_emergency_notification` function – citeturn0file0)*

**4. Command Handling & AI Routing**  
- **v0.3.0:** Commands were processed with a basic case‑sensitive handler.  
- **v0.4.0:** Slash commands are now case‑insensitive, reducing issues with mobile autocorrect. Custom commands from `commands_config.json` are supported with dynamic AI prompts, and special handling is applied when using Home Assistant integration with secure PIN mode.  
*(Command handling improvements in v0.4.0 – citeturn0file0)*

**5. Error Handling & Reconnection Logic**  
- **v0.3.0:** Basic error handling with standard reconnection loops.  
- **v0.4.0:** Enhanced detection of connection errors (e.g., specific OSError codes) triggers a graceful reconnect using a global reset event. Thread exception hooks and verbose logging further improve stability.  
*(Reviewed in the connection error sections in v0.4.0 – citeturn0file0)*

**6. Miscellaneous Improvements**  
- Updated banner and version text now clearly identify the testing branch as v0.4.0.  
- Overall code refactoring for clarity and better maintainability.
- Additional comments and debug prints assist in troubleshooting and field testing.

---

## Contributing & Disclaimer

- **Alpha Software Notice:**  
  This release (v0.4.0) is experimental. Expect bugs and changes that might affect existing features. Thorough field testing is still recommended before deployment in production environments.
- **Feedback & Contributions:**  
  Report issues or submit pull requests on GitHub. Your feedback is invaluable in making this project more robust.
- **Use Responsibly:**  
  Modifications for nefarious purposes are strictly prohibited. Use at your own risk.

---

## Conclusion

Meshtastic-AI Alpha v0.4.0 builds upon the solid foundation of v0.3.0, introducing significant enhancements in logging, emergency alert routing, Discord integration, and overall stability. Whether you’re interacting directly with your mesh node, integrating with Home Assistant, or leveraging multi‑channel alerting (Twilio, Email, Discord), this release offers a more comprehensive and reliable off‑grid AI assistant experience.

**Enjoy tinkering, stay safe, and have fun!**  
Please share your feedback or join our community on GitHub.

---

Happy coding, and may your mesh always stay connected!
