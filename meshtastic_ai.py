import meshtastic
import meshtastic.serial_interface
from meshtastic import BROADCAST_ADDR
from pubsub import pub
import json
import requests
import time
from datetime import datetime, timedelta, timezone  # Added timezone import
import threading
import os
import smtplib
from email.mime.text import MIMEText
import logging
import traceback
from flask import Flask, request, jsonify, redirect, url_for, stream_with_context, Response
import sys
import socket  # for socket error checking
import re
from twilio.rest import Client  # for Twilio SMS support
from unidecode import unidecode   # Added unidecode import for Ollama text normalization
from google.protobuf.message import DecodeError
# Make sure DEBUG_ENABLED exists before any logger/filter classes use it
# -----------------------------
# Global Debug & Noise Patterns
# -----------------------------
# Debug flag loaded later from config.json
DEBUG_ENABLED = False
# Suppress these protobuf messages unless DEBUG_ENABLED=True
NOISE_PATTERNS = (
    "Error while parsing FromRadio",
    "Error parsing message with type 'meshtastic.protobuf.FromRadio'",
    "Traceback",
    "meshtastic/stream_interface.py",
    "meshtastic/mesh_interface.py",
)

class _ProtoNoiseFilter(logging.Filter):
    NOISY = (
        "Error while parsing FromRadio",
        "Error parsing message with type 'meshtastic.protobuf.FromRadio'",
    )

    def filter(self, rec: logging.LogRecord) -> bool:
        noisy = any(s in rec.getMessage() for s in self.NOISY)
        return DEBUG_ENABLED or not noisy        # show only in debug mode

root_log       = logging.getLogger()          # the root logger
meshtastic_log = logging.getLogger("meshtastic")

for lg in (root_log, meshtastic_log):
    lg.addFilter(_ProtoNoiseFilter())

def dprint(*args, **kwargs):
    if DEBUG_ENABLED:
        print(*args, **kwargs)

def info_print(*args, **kwargs):
    if not DEBUG_ENABLED:
        print(*args, **kwargs)

if DEBUG_ENABLED:
    print(f"DEBUG: Loaded main config => {config}")
# -----------------------------
# Verbose Logging Setup
# -----------------------------
SCRIPT_LOG_FILE = "script.log"
script_logs = []  # In-memory log entries (most recent 200)
server_start_time = datetime.now(timezone.utc)  # Now using UTC time
restart_count = 0

def add_script_log(message):
    # drop protobuf noise if debug is off
    NOISE_PATTERNS = (
        "Error while parsing FromRadio",
        "Error parsing message with type 'meshtastic.protobuf.FromRadio'",
        "Traceback",
        "meshtastic/stream_interface.py",
        "meshtastic/mesh_interface.py",
    )
    if not DEBUG_ENABLED and any(p in message for p in NOISE_PATTERNS):
        return

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    log_entry = f"{timestamp} - {message}"
    script_logs.append(log_entry)
    if len(script_logs) > 200:
        script_logs.pop(0)
    try:
        # Truncate file if larger than 100 MB (keep last 100 lines)
        if os.path.exists(SCRIPT_LOG_FILE):
            filesize = os.path.getsize(SCRIPT_LOG_FILE)
            if filesize > 100 * 1024 * 1024:
                with open(SCRIPT_LOG_FILE, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                last_lines = lines[-100:] if len(lines) >= 100 else lines
                with open(SCRIPT_LOG_FILE, "w", encoding="utf-8") as f:
                    f.writelines(last_lines)
        with open(SCRIPT_LOG_FILE, "a", encoding="utf-8") as f:
            # append a real newline
            f.write(log_entry + "\n")
    except Exception as e:
        print(f"⚠️ Could not write to {SCRIPT_LOG_FILE}: {e}")
# Redirect stdout and stderr to our log while still printing to terminal.
class StreamToLogger(object):
    def __init__(self, logger_func):
        self.logger_func = logger_func
        self.terminal = sys.__stdout__
        # reuse noise patterns from the Proto filter
        self.noise_patterns = _ProtoNoiseFilter.NOISY if ' _ProtoNoiseFilter' in globals() else []

    def write(self, buf):
        # still print everything to the terminal...
        self.terminal.write(buf)
        text = buf.strip()
        if not text:
            return
        # only log to script_logs if not noisy, or if debug is on
        if DEBUG_ENABLED or not any(p in text for p in self.noise_patterns):
            self.logger_func(text)

    def flush(self):
        self.terminal.flush()

sys.stdout = StreamToLogger(add_script_log)
sys.stderr = StreamToLogger(add_script_log)
# -----------------------------
# Global Connection & Reset Status
# -----------------------------
connection_status = "Disconnected"
last_error_message = ""
reset_event = threading.Event()  # Global event to signal a fatal error and trigger reconnect

# -----------------------------
# Meshtastic and Flask Setup
# -----------------------------
try:
    from meshtastic.tcp_interface import TCPInterface
except ImportError:
    TCPInterface = None

try:
    from meshtastic.mesh_interface import MeshInterface
    MESH_INTERFACE_AVAILABLE = True
except ImportError:
    MESH_INTERFACE_AVAILABLE = False

log = logging.getLogger('werkzeug')
log.disabled = True

BANNER = (
    "\033[38;5;214m"
    """
███╗   ███╗███████╗███████╗██╗  ██╗             █████╗ ██╗
████╗ ████║██╔════╝██╔════╝██║  ██║            ██╔══██╗██║
██╔████╔██║█████╗  ███████╗███████║  █████╗    ███████║██║
██║╚██╔╝██║██╔══╝  ╚════██║██╔══██║  ╚════╝    ██╔══██║██║
██║ ╚═╝ ██║███████╗███████║██║  ██║            ██║  ██║██║
╚═╝     ╚═╝╚══════╝╚══════╝╚═╝  ╚═╝            ╚═╝  ╚═╝╚═╝

Mesh-AI BETA v0.5.0 by: MR_TBOT (https://mr-tbot.com)
https://github.com/mr-tbot/mesh-ai/
    \033[32m 
Messaging Dashboard Access: http://localhost:5000/dashboard \033[38;5;214m
"""
    "\033[0m"
    "\033[31m"
    """
DISCLAIMER: This is beta software - and should not be relied upon for mission critical tasks or emergencies.
Modification of this code for nefarious purposes is strictly frowned upon. Please use responsibly.

(Use at your own risk. For feedback or issues, see the GitHub link above.)
"""
    "\033[0m"
)
print(BANNER)
add_script_log("Script started.")

# -----------------------------
# Load Config Files
# -----------------------------
CONFIG_FILE = "config.json"
COMMANDS_CONFIG_FILE = "commands_config.json"
MOTD_FILE = "motd.json"
LOG_FILE = "messages.log"
ARCHIVE_FILE = "messages_archive.json"

print("Loading config files...")

def safe_load_json(path, default_value):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"⚠️ {path} not found. Using defaults.")
    except Exception as e:
        print(f"⚠️ Could not load {path}: {e}")
    return default_value

config = safe_load_json(CONFIG_FILE, {})
commands_config = safe_load_json(COMMANDS_CONFIG_FILE, {"commands": []})
try:
    with open(MOTD_FILE, "r", encoding="utf-8") as f:
        motd_content = f.read()
except FileNotFoundError:
    print(f"⚠️ {MOTD_FILE} not found.")
    motd_content = "No MOTD available."



# -----------------------------
# AI Provider & Other Config Vars
# -----------------------------
DEBUG_ENABLED = bool(config.get("debug", False))
AI_PROVIDER = config.get("ai_provider", "lmstudio").lower()
SYSTEM_PROMPT = config.get("system_prompt", "You are a helpful assistant responding to mesh network chats.")
LMSTUDIO_URL = config.get("lmstudio_url", "http://localhost:1234/v1/chat/completions")
LMSTUDIO_TIMEOUT = config.get("lmstudio_timeout", 60)
LMSTUDIO_CHAT_MODEL = config.get(
    "lmstudio_chat_model",
    "llama-3.2-1b-instruct-uncensored",
)
LMSTUDIO_EMBEDDING_MODEL = config.get(
    "lmstudio_embedding_model",
    "text-embedding-nomic-embed-text-v1.5",	
)	
OPENAI_API_KEY = config.get("openai_api_key", "")
OPENAI_MODEL = config.get("openai_model", "gpt-3.5-turbo")
OPENAI_TIMEOUT = config.get("openai_timeout", 30)
OLLAMA_URL = config.get("ollama_url", "http://localhost:11434/api/generate")
OLLAMA_MODEL = config.get("ollama_model", "llama2")
OLLAMA_TIMEOUT = config.get("ollama_timeout", 60)
HOME_ASSISTANT_URL = config.get("home_assistant_url", "")
HOME_ASSISTANT_TOKEN = config.get("home_assistant_token", "")
HOME_ASSISTANT_TIMEOUT = config.get("home_assistant_timeout", 30)
HOME_ASSISTANT_ENABLE_PIN = bool(config.get("home_assistant_enable_pin", False))
HOME_ASSISTANT_SECURE_PIN = str(config.get("home_assistant_secure_pin", "1234"))
HOME_ASSISTANT_ENABLED = bool(config.get("home_assistant_enabled", False))
HOME_ASSISTANT_CHANNEL_INDEX = int(config.get("home_assistant_channel_index", -1))
MAX_CHUNK_SIZE = config.get("chunk_size", 200)
MAX_CHUNKS = 5
CHUNK_DELAY = config.get("chunk_delay", 10)
MAX_RESPONSE_LENGTH = MAX_CHUNK_SIZE * MAX_CHUNKS
LOCAL_LOCATION_STRING = config.get("local_location_string", "Unknown Location")
AI_NODE_NAME = config.get("ai_node_name", "AI-Bot")
FORCE_NODE_NUM = config.get("force_node_num", None)

ENABLE_DISCORD = config.get("enable_discord", False)
DISCORD_WEBHOOK_URL = config.get("discord_webhook_url", None)
DISCORD_SEND_EMERGENCY = config.get("discord_send_emergency", False)
DISCORD_SEND_AI = config.get("discord_send_ai", False)
DISCORD_SEND_ALL = config.get("discord_send_all", False)
DISCORD_RESPONSE_CHANNEL_INDEX = config.get("discord_response_channel_index", None)
DISCORD_RECEIVE_ENABLED = config.get("discord_receive_enabled", True)
# New variable for inbound routing
DISCORD_INBOUND_CHANNEL_INDEX = config.get("discord_inbound_channel_index", None)
if DISCORD_INBOUND_CHANNEL_INDEX is not None:
    DISCORD_INBOUND_CHANNEL_INDEX = int(DISCORD_INBOUND_CHANNEL_INDEX)
# For polling Discord messages (optional)
DISCORD_BOT_TOKEN = config.get("discord_bot_token", None)
DISCORD_CHANNEL_ID = config.get("discord_channel_id", None)

ENABLE_TWILIO = config.get("enable_twilio", False)
ENABLE_SMTP = config.get("enable_smtp", False)
ALERT_PHONE_NUMBER = config.get("alert_phone_number", None)
TWILIO_SID = config.get("twilio_sid", None)
TWILIO_AUTH_TOKEN = config.get("twilio_auth_token", None)
TWILIO_FROM_NUMBER = config.get("twilio_from_number", None)
SMTP_HOST = config.get("smtp_host", None)
SMTP_PORT = config.get("smtp_port", 587)
SMTP_USER = config.get("smtp_user", None)
SMTP_PASS = config.get("smtp_pass", None)
ALERT_EMAIL_TO = config.get("alert_email_to", None)

SERIAL_PORT = config.get("serial_port", "")
SERIAL_BAUD = int(config.get("serial_baud", 921600))  # ← NEW ● default 921600
USE_WIFI = bool(config.get("use_wifi", False))
WIFI_HOST = config.get("wifi_host", None)
WIFI_PORT = int(config.get("wifi_port", 4403))
USE_MESH_INTERFACE = bool(config.get("use_mesh_interface", False))

app = Flask(__name__)
messages = []
interface = None

lastDMNode = None
lastChannelIndex = None

# -----------------------------
# Location Lookup Function
# -----------------------------
def get_node_location(node_id):
    if interface and hasattr(interface, "nodes") and node_id in interface.nodes:
        pos = interface.nodes[node_id].get("position", {})
        lat = pos.get("latitude")
        lon = pos.get("longitude")
        tstamp = pos.get("time")
        return lat, lon, tstamp
    return None, None, None

def load_archive():
    global messages
    if os.path.exists(ARCHIVE_FILE):
        try:
            with open(ARCHIVE_FILE, "r", encoding="utf-8") as f:
                arr = json.load(f)
            if isinstance(arr, list):
                messages = arr
                print(f"Loaded {len(messages)} messages from archive.")
        except Exception as e:
            print(f"⚠️ Could not load archive {ARCHIVE_FILE}: {e}")
    else:
        print("No archive found; starting fresh.")

def save_archive():
    try:
        with open(ARCHIVE_FILE, "w", encoding="utf-8") as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ Could not save archive to {ARCHIVE_FILE}: {e}")

def parse_node_id(node_str_or_int):
    if isinstance(node_str_or_int, int):
        return node_str_or_int
    if isinstance(node_str_or_int, str):
        if node_str_or_int == '^all':
            return BROADCAST_ADDR
        if node_str_or_int.lower() in ['!ffffffff', '!ffffffffl']:
            return BROADCAST_ADDR
        if node_str_or_int.startswith('!'):
            hex_part = node_str_or_int[1:]
            try:
                return int(hex_part, 16)
            except ValueError:
                dprint(f"parse_node_id: Unable to parse hex from {node_str_or_int}")
                return None
        try:
            return int(node_str_or_int)
        except ValueError:
            dprint(f"parse_node_id: {node_str_or_int} not recognized as int or hex.")
            return None
    return None

def get_node_fullname(node_id):
    """Return the full (long) name if available, otherwise the short name."""
    if interface and hasattr(interface, "nodes") and node_id in interface.nodes:
        user_dict = interface.nodes[node_id].get("user", {})
        return user_dict.get("longName", user_dict.get("shortName", f"Node_{node_id}"))
    return f"Node_{node_id}"

def get_node_shortname(node_id):
    if interface and hasattr(interface, "nodes") and node_id in interface.nodes:
        user_dict = interface.nodes[node_id].get("user", {})
        return user_dict.get("shortName", f"Node_{node_id}")
    return f"Node_{node_id}"

def log_message(node_id, text, is_emergency=False, reply_to=None, direct=False, channel_idx=None):
    if node_id != "WebUI":
        display_id = f"{get_node_shortname(node_id)} ({node_id})"
    else:
        display_id = "WebUI"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    entry = {
        "timestamp": timestamp,
        "node": display_id,
        "node_id": None if node_id == "WebUI" else node_id,
        "message": text,
        "emergency": is_emergency,
        "reply_to": reply_to,
        "direct": direct,
        "channel_idx": channel_idx
    }
    messages.append(entry)
    if len(messages) > 100:
        messages.pop(0)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as logf:
            logf.write(f"{timestamp} | {display_id} | EMERGENCY={is_emergency} | {text}\n")
    except Exception as e:
        print(f"⚠️ Could not write to {LOG_FILE}: {e}")
    save_archive()
    return entry

def split_message(text):
    if not text:
        return []
    return [text[i: i + MAX_CHUNK_SIZE] for i in range(0, len(text), MAX_CHUNK_SIZE)][:MAX_CHUNKS]

def send_broadcast_chunks(interface, text, channelIndex):
    dprint(f"send_broadcast_chunks: text='{text}', channelIndex={channelIndex}")
    info_print(f"[Info] Sending broadcast on channel {channelIndex} → '{text}'")
    if interface is None:
        print("❌ Cannot send broadcast: interface is None.")
        return
    if not text:
        return
    chunks = split_message(text)
    for i, chunk in enumerate(chunks):
        try:
            interface.sendText(chunk, destinationId=BROADCAST_ADDR, channelIndex=channelIndex, wantAck=True)
            time.sleep(CHUNK_DELAY)
        except Exception as e:
            print(f"❌ Error sending broadcast chunk: {e}")
            # Check both errno and winerror for known connection errors
            error_code = getattr(e, 'errno', None) or getattr(e, 'winerror', None)
            if error_code in (10053, 10054, 10060):
                reset_event.set()
            break
        else:
            info_print(f"[Info] Successfully sent chunk {i+1}/{len(chunks)} on ch={channelIndex}.")

def send_direct_chunks(interface, text, destinationId):
    dprint(f"send_direct_chunks: text='{text}', destId={destinationId}")
    info_print(f"[Info] Sending direct message to node {destinationId} => '{text}'")
    if interface is None:
        print("❌ Cannot send direct message: interface is None.")
        return
    if not text:
        return
    ephemeral_ok = hasattr(interface, "sendDirectText")
    chunks = split_message(text)
    for i, chunk in enumerate(chunks):
        try:
            if ephemeral_ok:
                interface.sendDirectText(destinationId, chunk, wantAck=True)
            else:
                interface.sendText(chunk, destinationId=destinationId, wantAck=True)
            time.sleep(CHUNK_DELAY)
        except Exception as e:
            print(f"❌ Error sending direct chunk: {e}")
            error_code = getattr(e, 'errno', None) or getattr(e, 'winerror', None)
            if error_code in (10053, 10054, 10060):
                reset_event.set()
            break
        else:
            info_print(f"[Info] Direct chunk {i+1}/{len(chunks)} to {destinationId} sent.")

def send_to_lmstudio(user_message: str):
    """Chat/completion request to LM Studio with explicit model name."""
    dprint(f"send_to_lmstudio: user_message='{user_message}'")
    info_print("[Info] Routing user message to LMStudio…")
    payload = {
        "model": LMSTUDIO_CHAT_MODEL,  # **mandatory when multiple models loaded**
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ],
        "max_tokens": MAX_RESPONSE_LENGTH,
    }
    try:
        response = requests.post(LMSTUDIO_URL, json=payload, timeout=LMSTUDIO_TIMEOUT)
        if response.status_code == 200:
            j = response.json()
            dprint(f"LMStudio raw ⇒ {j}")
            ai_resp = (
                j.get("choices", [{}])[0]
                 .get("message", {})
                 .get("content", "🤖 [No response]")
            )
            return ai_resp[:MAX_RESPONSE_LENGTH]
        else:
            print(f"⚠️ LMStudio error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"⚠️ LMStudio request failed: {e}")
        return None
def lmstudio_embed(text: str):
    """Return an embedding vector (if you ever need it)."""
    payload = {
        "model": LMSTUDIO_EMBEDDING_MODEL,
        "input": text,
															   
    }
    try:
        r = requests.post(
            "http://localhost:1234/v1/embeddings",
            json=payload,
            timeout=LMSTUDIO_TIMEOUT,
        )
        if r.status_code == 200:
            vec = r.json().get("data", [{}])[0].get("embedding")
            return vec
        else:
            dprint(f"LMStudio embed error {r.status_code}: {r.text}")
					   
    except Exception as exc:
        dprint(f"LMStudio embed exception: {exc}")
    return None
def send_to_openai(user_message):
    dprint(f"send_to_openai: user_message='{user_message}'")
    info_print("[Info] Routing user message to OpenAI...")
    if not OPENAI_API_KEY:
        print("⚠️ No OpenAI API key provided.")
        return None
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ],
        "max_tokens": MAX_RESPONSE_LENGTH
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=OPENAI_TIMEOUT)
        if r.status_code == 200:
            jr = r.json()
            dprint(f"OpenAI raw => {jr}")
            content = (
                jr.get("choices", [{}])[0]
                  .get("message", {})
                  .get("content", "🤖 [No response]")
            )
            return content[:MAX_RESPONSE_LENGTH]
        else:
            print(f"⚠️ OpenAI error: {r.status_code} => {r.text}")
            return None
    except Exception as e:
        print(f"⚠️ OpenAI request failed: {e}")
        return None

def send_to_ollama(user_message):
    dprint(f"send_to_ollama: user_message='{user_message}'")
    info_print("[Info] Routing user message to Ollama...")
    # Normalize text for non-ASCII characters using unidecode
    user_message = unidecode(user_message)
    combined_prompt = f"{SYSTEM_PROMPT}\n{user_message}"
    payload = {
        "prompt": combined_prompt,
        "model": OLLAMA_MODEL,
        "stream": False  # Added to disable streaming responses
    }
    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=OLLAMA_TIMEOUT)
        if r.status_code == 200:
            jr = r.json()
            dprint(f"Ollama raw => {jr}")
            return jr.get("response", "🤖 [No response]")[:MAX_RESPONSE_LENGTH]
        else:
            print(f"⚠️ Ollama error: {r.status_code} => {r.text}")
            return None
    except Exception as e:
        print(f"⚠️ Ollama request failed: {e}")
        return None

def send_to_home_assistant(user_message):
    dprint(f"send_to_home_assistant: user_message='{user_message}'")
    info_print("[Info] Routing user message to Home Assistant...")
    if not HOME_ASSISTANT_URL:
        return None
    headers = {"Content-Type": "application/json"}
    if HOME_ASSISTANT_TOKEN:
        headers["Authorization"] = f"Bearer {HOME_ASSISTANT_TOKEN}"
    payload = {"text": user_message}
    try:
        r = requests.post(HOME_ASSISTANT_URL, json=payload, headers=headers, timeout=HOME_ASSISTANT_TIMEOUT)
        if r.status_code == 200:
            data = r.json()
            dprint(f"HA raw => {data}")
            speech = data.get("response", {}).get("speech", {})
            answer = speech.get("plain", {}).get("speech")
            if answer:
                return answer[:MAX_RESPONSE_LENGTH]
            return "🤖 [No response from Home Assistant]"
        else:
            print(f"⚠️ HA error: {r.status_code} => {r.text}")
            return None
    except Exception as e:
        print(f"⚠️ HA request failed: {e}")
        return None

def get_ai_response(prompt):
    if AI_PROVIDER == "lmstudio":
        return send_to_lmstudio(prompt)
    elif AI_PROVIDER == "openai":
        return send_to_openai(prompt)
    elif AI_PROVIDER == "ollama":
        return send_to_ollama(prompt)
    elif AI_PROVIDER == "home_assistant":
        return send_to_home_assistant(prompt)
    else:
        print(f"⚠️ Unknown AI provider: {AI_PROVIDER}")
        return None

def send_discord_message(content):
    if not (ENABLE_DISCORD and DISCORD_WEBHOOK_URL):
        return
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": content})
    except Exception as e:
        print(f"⚠️ Discord webhook error: {e}")

# -----------------------------
# Revised Emergency Notification Function
# -----------------------------
def send_emergency_notification(node_id, user_msg, lat=None, lon=None, position_time=None):
    info_print("[Info] Sending emergency notification...")

    sn = get_node_shortname(node_id)
    fullname = get_node_fullname(node_id)
    full_msg = f"EMERGENCY from {sn} ({fullname}) [Node {node_id}]:\n"
    if lat is not None and lon is not None:
        maps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
        full_msg += f" - Location: {maps_url}\n"
    if position_time:
        full_msg += f" - Last GPS time: {position_time}\n"
    if user_msg:
        full_msg += f" - Message: {user_msg}\n"
    
    # Attempt to send SMS via Twilio if configured.
    try:
        if ENABLE_TWILIO and TWILIO_SID and TWILIO_AUTH_TOKEN and ALERT_PHONE_NUMBER and TWILIO_FROM_NUMBER:
            client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
            client.messages.create(
                body=full_msg,
                from_=TWILIO_FROM_NUMBER,
                to=ALERT_PHONE_NUMBER
            )
            print("✅ Emergency SMS sent via Twilio.")
        else:
            print("Twilio not properly configured for SMS.")
    except Exception as e:
        print(f"⚠️ Twilio error: {e}")

    # Attempt to send email via SMTP if configured.
    try:
        if ENABLE_SMTP and SMTP_HOST and SMTP_USER and SMTP_PASS and ALERT_EMAIL_TO:
            if isinstance(ALERT_EMAIL_TO, list):
                email_to = ", ".join(ALERT_EMAIL_TO)
            else:
                email_to = ALERT_EMAIL_TO
            msg = MIMEText(full_msg)
            msg["Subject"] = f"EMERGENCY ALERT from {sn} ({fullname}) [Node {node_id}]"
            msg["From"] = SMTP_USER
            msg["To"] = email_to
            if SMTP_PORT == 465:
                s = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT)
            else:
                s = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
                s.starttls()
            s.login(SMTP_USER, SMTP_PASS)
            s.sendmail(SMTP_USER, email_to, msg.as_string())
            s.quit()
            print("✅ Emergency email sent via SMTP.")
        else:
            print("SMTP not properly configured for email alerts.")
    except Exception as e:
        print(f"⚠️ SMTP error: {e}")

    # Attempt to post emergency alert to Discord if enabled.
    try:
        if DISCORD_SEND_EMERGENCY and ENABLE_DISCORD and DISCORD_WEBHOOK_URL:
            requests.post(DISCORD_WEBHOOK_URL, json={"content": full_msg})
            print("✅ Emergency alert posted to Discord.")
        else:
            print("Discord emergency notifications disabled or not configured.")
    except Exception as e:
        print(f"⚠️ Discord webhook error: {e}")

# -----------------------------
# Helper: Validate/Strip PIN (for Home Assistant)
# -----------------------------
def pin_is_valid(text):
    lower = text.lower()
    if "pin=" not in lower:
        return False
    idx = lower.find("pin=") + 4
    candidate = lower[idx:idx+4]
    return (candidate == HOME_ASSISTANT_SECURE_PIN.lower())

def strip_pin(text):
    lower = text.lower()
    idx = lower.find("pin=")
    if idx == -1:
        return text
    return text[:idx].strip() + " " + text[idx+8:].strip()

def route_message_text(user_message, channel_idx):
    if HOME_ASSISTANT_ENABLED and channel_idx == HOME_ASSISTANT_CHANNEL_INDEX:
        info_print("[Info] Routing to Home Assistant channel.")
        if HOME_ASSISTANT_ENABLE_PIN:
            if not pin_is_valid(user_message):
                return "Security code missing/invalid. Format: 'PIN=XXXX your msg'"
            user_message = strip_pin(user_message)
        ha_response = send_to_home_assistant(user_message)
        return ha_response if ha_response else "🤖 [No response from Home Assistant]"
    else:
        info_print(f"[Info] Using default AI provider: {AI_PROVIDER}")
        resp = get_ai_response(user_message)
        return resp if resp else "🤖 [No AI response]"

# -----------------------------
# Revised Command Handler (Case-Insensitive)
# -----------------------------
def handle_command(cmd, full_text, sender_id):
    cmd = cmd.lower()
    dprint(f"handle_command => cmd='{cmd}', full_text='{full_text}', sender_id={sender_id}")
    if cmd == "/about":
        return "Meshtastic-AI Off Grid Chat Bot - By: MR-TBOT.com"
    elif cmd in ["/ai", "/bot", "/query", "/data"]:
        user_prompt = full_text[len(cmd):].strip()
        if AI_PROVIDER == "home_assistant" and HOME_ASSISTANT_ENABLE_PIN:
            if not pin_is_valid(user_prompt):
                return "Security code missing or invalid. Use 'PIN=XXXX'"
            user_prompt = strip_pin(user_prompt)
        ai_answer = get_ai_response(user_prompt)
        return ai_answer if ai_answer else "🤖 [No AI response]"
    elif cmd == "/whereami":
        lat, lon, tstamp = get_node_location(sender_id)
        sn = get_node_shortname(sender_id)
        if lat is None or lon is None:
            return f"🤖 Sorry {sn}, I have no GPS fix for your node."
        tstr = str(tstamp) if tstamp else "Unknown"
        return f"Node {sn} GPS: {lat}, {lon} (time: {tstr})"
    elif cmd in ["/emergency", "/911"]:
        lat, lon, tstamp = get_node_location(sender_id)
        user_msg = full_text[len(cmd):].strip()
        send_emergency_notification(sender_id, user_msg, lat, lon, tstamp)
        log_message(sender_id, f"EMERGENCY TRIGGERED: {full_text}", is_emergency=True)
        return "🚨 Emergency alert sent. Stay safe."
    elif cmd == "/test":
        sn = get_node_shortname(sender_id)
        return f"Hello {sn}! Received {LOCAL_LOCATION_STRING} by {AI_NODE_NAME}."
    elif cmd == "/help":
        built_in = ["/about", "/query", "/whereami", "/emergency", "/911", "/test", "/motd"]
        custom_cmds = [c.get("command") for c in commands_config.get("commands",[])]
        return "Commands:\n" + ", ".join(built_in + custom_cmds)
    elif cmd == "/motd":
        return motd_content
    elif cmd == "/sms":
        parts = full_text.split(" ", 2)
        if len(parts) < 3:
            return "Invalid syntax. Use: /sms <phone_number> <message>"
        phone_number = parts[1]
        message_text = parts[2]
        try:
            client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
            client.messages.create(
                body=message_text,
                from_=TWILIO_FROM_NUMBER,
                to=phone_number
            )
            print(f"✅ SMS sent to {phone_number}")
            return "SMS sent successfully."
        except Exception as e:
            print(f"⚠️ Failed to send SMS: {e}")
            return "Failed to send SMS."
    for c in commands_config.get("commands", []):
        if c.get("command").lower() == cmd:
            if "ai_prompt" in c:
                user_input = full_text[len(cmd):].strip()
                custom_text = c["ai_prompt"].replace("{user_input}", user_input)
                if AI_PROVIDER == "home_assistant" and HOME_ASSISTANT_ENABLE_PIN:
                    if not pin_is_valid(custom_text):
                        return "Security code missing or invalid."
                    custom_text = strip_pin(custom_text)
                ans = get_ai_response(custom_text)
                return ans if ans else "🤖 [No AI response]"
            elif "response" in c:
                return c["response"]
            return "No configured response for this command."
    return None

def parse_incoming_text(text, sender_id, is_direct, channel_idx):
    dprint(f"parse_incoming_text => text='{text}' is_direct={is_direct} channel={channel_idx}")
    info_print(f"[Info] Received from node {sender_id} (direct={is_direct}, ch={channel_idx}) => '{text}'")
    text = text.strip()
    if not text:
        return None
    if is_direct and not config.get("reply_in_directs", True):
        return None
    if (not is_direct) and channel_idx != HOME_ASSISTANT_CHANNEL_INDEX and not config.get("reply_in_channels", True):
        return None
    if text.startswith("/"):
        cmd = text.split()[0]
        resp = handle_command(cmd, text, sender_id)
        return resp
    if is_direct:
        return get_ai_response(text)
    if HOME_ASSISTANT_ENABLED and channel_idx == HOME_ASSISTANT_CHANNEL_INDEX:
        return route_message_text(text, channel_idx)
    return None

def on_receive(packet=None, interface=None, **kwargs):
    dprint(f"on_receive => packet={packet}")
    if not packet or 'decoded' not in packet:
        dprint("No decoded packet => ignoring.")
        return
    if packet['decoded']['portnum'] != 'TEXT_MESSAGE_APP':
        dprint("Not TEXT_MESSAGE_APP => ignoring.")
        return
    try:
        text_raw = packet['decoded']['payload']
        text = text_raw.decode('utf-8', errors='replace')
        sender_node = packet.get('fromId', None)
        raw_to = packet.get('toId', None)
        to_node_int = parse_node_id(raw_to)
        ch_idx = packet.get('channel', 0)
        dprint(f"[MSG] from {sender_node} to {raw_to} (ch={ch_idx}): {text}")
        entry = log_message(sender_node, text, direct=(to_node_int != BROADCAST_ADDR), channel_idx=(None if to_node_int != BROADCAST_ADDR else ch_idx))
        global lastDMNode, lastChannelIndex
        if to_node_int != BROADCAST_ADDR:
            lastDMNode = sender_node
        else:
            lastChannelIndex = ch_idx

        # Only forward messages on the configured Discord inbound channel to Discord.
        if ENABLE_DISCORD and DISCORD_SEND_ALL and DISCORD_INBOUND_CHANNEL_INDEX is not None and ch_idx == DISCORD_INBOUND_CHANNEL_INDEX:
            sender_info = f"{get_node_shortname(sender_node)} ({sender_node})"
            disc_content = f"**{sender_info}**: {text}"
            send_discord_message(disc_content)

        my_node_num = None
        if FORCE_NODE_NUM is not None:
            my_node_num = FORCE_NODE_NUM
        else:
            if hasattr(interface, "myNode") and interface.myNode:
                my_node_num = interface.myNode.nodeNum
            elif hasattr(interface, "localNode") and interface.localNode:
                my_node_num = interface.localNode.nodeNum
        is_direct = False
        if to_node_int == BROADCAST_ADDR:
            is_direct = False
        elif my_node_num is not None and to_node_int == my_node_num:
            is_direct = True
        else:
            is_direct = (my_node_num == to_node_int)
        resp = parse_incoming_text(text, sender_node, is_direct, ch_idx)
        if resp:
            info_print("[Info] Wait 10s before responding to reduce collisions.")
            time.sleep(10)
            log_message(AI_NODE_NAME, resp, reply_to=entry['timestamp'])
            # If message originated on Discord inbound channel, also send the AI response back to Discord.
            if ENABLE_DISCORD and DISCORD_SEND_AI and DISCORD_INBOUND_CHANNEL_INDEX is not None and ch_idx == DISCORD_INBOUND_CHANNEL_INDEX:
                disc_msg = f"🤖 **{AI_NODE_NAME}**: {resp}"
                send_discord_message(disc_msg)
            if is_direct:
                send_direct_chunks(interface, resp, sender_node)
            else:
                send_broadcast_chunks(interface, resp, ch_idx)
    except OSError as e:
        error_code = getattr(e, 'errno', None) or getattr(e, 'winerror', None)
        print(f"⚠️ OSError detected in on_receive: {e} (error code: {error_code})")
        if error_code in (10053, 10054, 10060):
            print("⚠️ Connection error detected. Restarting interface...")
            global connection_status
            connection_status = "Disconnected"
            reset_event.set()
        # Instead of re-raising, simply return to prevent thread crash
        return
    except Exception as e:
        print(f"⚠️ Unexpected error in on_receive: {e}")
        return

@app.route("/messages", methods=["GET"])
def get_messages_api():
    dprint("GET /messages => returning current messages")
    return jsonify(messages)

@app.route("/nodes", methods=["GET"])
def get_nodes_api():
    node_list = []
    if interface and hasattr(interface, "nodes"):
        for nid in interface.nodes:
            sn = get_node_shortname(nid)
            ln = get_node_fullname(nid)
            node_list.append({
                "id": nid,
                "shortName": sn,
                "longName": ln
            })
    return jsonify(node_list)

@app.route("/connection_status", methods=["GET"], endpoint="connection_status_info")
def connection_status_info():
    return jsonify({"status": connection_status, "error": last_error_message})

@app.route("/logs_stream")
def logs_stream():
    def generate():
        last_index = 0
        while True:
            # apply your noise filter
            visible = [
                line for line in script_logs
                if DEBUG_ENABLED or not any(p in line for p in _ProtoNoiseFilter.NOISY)
            ]
            # send only the new lines
            if last_index < len(visible):
                for line in visible[last_index:]:
                    # each SSE “data:” is one log line
                    yield f"data: {line}\n\n"
                last_index = len(visible)
            time.sleep(0.5)

    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no"   # for nginx, disables proxy buffering
    }
    return Response(
        stream_with_context(generate()),
        headers=headers,
        mimetype="text/event-stream"
    )

@app.route("/logs", methods=["GET"])
def logs():
    uptime = datetime.now(timezone.utc) - server_start_time
    uptime_str = str(uptime).split('.')[0]

    # build a regex that matches any protobuf noise
    noise_re = re.compile(r"protobuf|DecodeError|ParseFromString", re.IGNORECASE)

    # include only non-noisy lines unless DEBUG_ENABLED
    visible = [
        line for line in script_logs
        if DEBUG_ENABLED or not noise_re.search(line)
    ]
    log_text = "\n".join(visible)

    html = f"""<html>
  <head>
    <meta http-equiv="refresh" content="1">
    <title>Meshtastic-AI Logs</title>
    <style>
      body {{ background:#000; color:#fff; font-family:monospace; padding:20px; }}
      pre {{ white-space: pre-wrap; word-break: break-word; }}
    </style>
  </head>
  <body>
    <h1>Script Logs</h1>
    <div><strong>Uptime:</strong> {uptime_str}</div>
    <div><strong>Restarts:</strong> {restart_count}</div>
    <pre id="logbox">{log_text}</pre>
    <script>
      // once the page renders, scroll to the bottom
      document.addEventListener("DOMContentLoaded", () => {{
        window.scrollTo(0, document.body.scrollHeight);
      }});
    </script>
  </body>
</html>"""
    return html
# -----------------------------
# Revised Discord Webhook Route for Inbound Messages
# -----------------------------
@app.route("/discord_webhook", methods=["POST"])
def discord_webhook():
    if not DISCORD_RECEIVE_ENABLED:
        return jsonify({"status": "disabled", "message": "Discord receive is disabled"}), 200
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No JSON payload provided"}), 400

    # Extract the username (default if not provided)
    username = data.get("username", "DiscordUser")
    channel_index = DISCORD_INBOUND_CHANNEL_INDEX
    message_text = data.get("message")
    if message_text is None:
        return jsonify({"status": "error", "message": "Missing message"}), 400

    # Prepend username to the message
    formatted_message = f"**{username}**: {message_text}"

    try:
        log_message("Discord", formatted_message, direct=False, channel_idx=int(channel_index))
        if interface is None:
            print("❌ Cannot route Discord message: interface is None.")
        else:
            send_broadcast_chunks(interface, formatted_message, int(channel_index))
        print(f"✅ Routed Discord message back on channel {channel_index}")
        return jsonify({"status": "sent", "channel_index": channel_index, "message": formatted_message})
    except Exception as e:
        print(f"⚠️ Discord webhook error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# -----------------------------
# New Twilio SMS Webhook Route for Inbound SMS
# -----------------------------
@app.route("/twilio_webhook", methods=["POST"])
def twilio_webhook():
    sms_body = request.form.get("Body")
    from_number = request.form.get("From")
    if not sms_body:
        return "No SMS body received", 400
    target = config.get("twilio_inbound_target", "channel")
    if target == "channel":
        channel_index = config.get("twilio_inbound_channel_index")
        if channel_index is None:
            return "No inbound channel index configured", 400
        log_message("Twilio", f"From {from_number}: {sms_body}", direct=False, channel_idx=int(channel_index))
        send_broadcast_chunks(interface, sms_body, int(channel_index))
        print(f"✅ Routed incoming SMS from {from_number} to channel {channel_index}")
    elif target == "node":
        node_id = config.get("twilio_inbound_node")
        if node_id is None:
            return "No inbound node configured", 400
        log_message("Twilio", f"From {from_number}: {sms_body}", direct=True)
        send_direct_chunks(interface, sms_body, node_id)
        print(f"✅ Routed incoming SMS from {from_number} to node {node_id}")
    else:
        return "Invalid twilio_inbound_target config", 400
    return "SMS processed", 200

@app.route("/dashboard", methods=["GET"])
def dashboard():
    channel_names = config.get("channel_names", {})
    channel_names_json = json.dumps(channel_names)

    # Prepare node GPS and beacon info for JS
    node_gps_info = {}
    if interface and hasattr(interface, "nodes"):
        for nid, ninfo in interface.nodes.items():
            pos = ninfo.get("position", {})
            lat = pos.get("latitude")
            lon = pos.get("longitude")
            tstamp = pos.get("time")
            # Try all possible hop keys, fallback to None
            hops = (
                ninfo.get("hopLimit")
                or ninfo.get("hop_count")
                or ninfo.get("hopCount")
                or ninfo.get("numHops")
                or ninfo.get("num_hops")
                or ninfo.get("hops")
                or None
            )
            # Convert tstamp (epoch) to readable UTC if present
            if tstamp:
                try:
                    dt = datetime.fromtimestamp(tstamp, timezone.utc)
                    tstr = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
                except Exception:
                    tstr = str(tstamp)
            else:
                tstr = None
            node_gps_info[str(nid)] = {
                "lat": lat,
                "lon": lon,
                "beacon_time": tstr,
                "hops": hops,
            }
    node_gps_info_json = json.dumps(node_gps_info)

    # Get connected node's GPS for distance calculation
    my_lat, my_lon, _ = get_node_location(interface.myNode.nodeNum) if interface and hasattr(interface, "myNode") and interface.myNode else (None, None, None)
    my_gps_json = json.dumps({"lat": my_lat, "lon": my_lon})

    html = """
<html>
<head>
  <title>Meshtastic AI Dashboard</title>
  <style>
    :root { --theme-color: #ffa500; }
    body { background: #000; color: #fff; font-family: Arial, sans-serif; margin: 0; padding-top: 120px; transition: filter 0.5s linear; }
    #connectionStatus { position: fixed; top: 0; left: 0; width: 100%; z-index: 350; text-align: center; padding: 0; font-size: 14px; font-weight: bold; display: block; }
    .header-buttons { position: fixed; top: 0; right: 0; z-index: 400; }
    .header-buttons a { background: var(--theme-color); color: #000; padding: 8px 12px; margin: 5px; text-decoration: none; border-radius: 4px; font-weight: bold; }
    #ticker-container { position: fixed; top: 20px; left: 0; width: 100vw; z-index: 300; height: 50px; display: flex; align-items: center; justify-content: center; pointer-events: none; }
    #ticker { background: #111; color: var(--theme-color); white-space: nowrap; overflow: hidden; width: 100vw; min-width: 100vw; max-width: 100vw; padding: 5px 0; font-size: 36px; display: none; position: relative; border-bottom: 2px solid var(--theme-color); min-height: 50px; pointer-events: auto; }
    #ticker p { display: inline-block; margin: 0; animation: tickerScroll 30s linear infinite; vertical-align: middle; min-width: 100vw; }
    #ticker .dismiss-btn { position: absolute; right: 20px; top: 50%; transform: translateY(-50%); font-size: 18px; background: #222; color: #fff; border: 1px solid var(--theme-color); border-radius: 4px; cursor: pointer; padding: 2px 10px; z-index: 10; }
    @keyframes tickerScroll { 0% { transform: translateX(100%); } 100% { transform: translateX(-100%); } }
    #sendForm { margin: 20px; padding: 20px; background: #111; border: 2px solid var(--theme-color); border-radius: 10px; }
    .three-col { display: flex; flex-direction: row; gap: 20px; margin: 20px; height: calc(100vh - 220px); }
    .three-col .col:nth-child(1), .three-col .col:nth-child(3) { flex: 2; overflow-y: auto; }
    .three-col .col:nth-child(2) { flex: 1; overflow-y: auto; }
    .lcars-panel { background: #111; padding: 20px; border: 2px solid var(--theme-color); border-radius: 10px; }
    .lcars-panel h2 { color: var(--theme-color); margin-top: 0; }
    .message { border: 1px solid var(--theme-color); border-radius: 4px; margin: 5px; padding: 5px; }
    .message.outgoing { background: #222; }
    .message.newMessage { border-color: #00ff00; background: #1a2; }
    .message.recentNode { border-color: #00bfff; background: #113355; }
    .timestamp { font-size: 0.8em; color: #666; }
    .btn { margin-left: 10px; padding: 2px 6px; font-size: 0.8em; cursor: pointer; }
    .switch { position: relative; display: inline-block; width: 60px; height: 34px; vertical-align: middle; }
    .switch input { opacity: 0; width: 0; height: 0; }
    .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #ccc; transition: .4s; }
    .slider:before { position: absolute; content: ""; height: 26px; width: 26px; left: 4px; bottom: 4px; background-color: white; transition: .4s; }
    input:checked + .slider { background-color: #2196F3; }
    input:focus + .slider { box-shadow: 0 0 1px #2196F3; }
    input:checked + .slider:before { transform: translateX(26px); }
    .slider.round { border-radius: 34px; }
    .slider.round:before { border-radius: 50%; }
    #charCounter { font-size: 0.9em; color: #ccc; text-align: right; margin-top: 5px; }
    .nodeItem { margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid var(--theme-color); display: flex; flex-direction: column; align-items: flex-start; flex-wrap: wrap; }
    .nodeItem.recentNode { border-bottom: 2px solid #00bfff; background: #113355; }
    .nodeMainLine { font-weight: bold; font-size: 1.1em; }
    .nodeLongName { color: #aaa; font-size: 0.98em; margin-top: 2px; }
    .nodeInfoLine { margin-top: 2px; font-size: 0.95em; color: #ccc; display: flex; flex-wrap: wrap; gap: 10px; }
    .nodeGPS { margin-left: 0; }
    .nodeBeacon { color: #aaa; font-size: 0.92em; }
    .nodeHops { color: #6cf; font-size: 0.92em; }
    .nodeMapBtn { margin-left: 0; background: #222; color: #fff; border: 1px solid #ffa500; border-radius: 4px; padding: 2px 6px; font-size: 1em; cursor: pointer; text-decoration: none; }
    .nodeMapBtn:hover { background: #ffa500; color: #000; }
    .channel-header { display: flex; align-items: center; gap: 10px; }
    .reply-btn { margin-left: 10px; padding: 2px 8px; font-size: 0.85em; background: #222; color: var(--theme-color); border: 1px solid var(--theme-color); border-radius: 4px; cursor: pointer; }
    .mark-read-btn { margin-left: 10px; padding: 2px 8px; font-size: 0.85em; background: #222; color: #0f0; border: 1px solid #0f0; border-radius: 4px; cursor: pointer; }
    .mark-all-read-btn { margin-left: 10px; padding: 2px 8px; font-size: 0.85em; background: #222; color: #ff0; border: 1px solid #ff0; border-radius: 4px; cursor: pointer; }
    /* Threaded DM styles */
    .dm-thread { margin-bottom: 16px; border-left: 3px solid var(--theme-color); padding-left: 10px; }
    .dm-thread .message { margin-left: 0; }
    .dm-thread .reply-btn { margin-top: 5px; }
    .dm-thread .thread-replies { margin-left: 30px; border-left: 2px dashed #555; padding-left: 10px; }
    /* Hide Discord section by default */
    #discordSection { display: none; }
    /* Node sort controls */
    .nodeSortBar { margin-bottom: 10px; }
    .nodeSortBar label { margin-right: 8px; }
    .nodeSortBar select { background: #222; color: #fff; border: 1px solid var(--theme-color); border-radius: 4px; padding: 2px 8px; }
    /* Full width search bar for nodes */
    #nodeSearch { width: 100%; margin-bottom: 10px; font-size: 1em; padding: 6px; box-sizing: border-box; }
    /* UI Settings panel hidden by default */
    .settings-panel { display: none; background: #111; border: 2px solid var(--theme-color); border-radius: 10px; padding: 20px; margin: 20px; }
    .settings-toggle { background: var(--theme-color); color: #000; padding: 8px 12px; margin: 20px; border-radius: 4px; font-weight: bold; cursor: pointer; display: inline-block; }
    .settings-toggle.active { background: #222; color: #ffa500; }
    /* Timezone selector */
    #timezoneSelect { margin-left: 10px; }
  </style>

  <script>
    // --- Mark as Read/Unread State ---
    let readDMs = JSON.parse(localStorage.getItem("readDMs") || "[]");
    let readChannels = JSON.parse(localStorage.getItem("readChannels") || "{}");

    function saveReadDMs() {
      localStorage.setItem("readDMs", JSON.stringify(readDMs));
    }
    function saveReadChannels() {
      localStorage.setItem("readChannels", JSON.stringify(readChannels));
    }
    function markDMAsRead(ts) {
      if (!readDMs.includes(ts)) {
        readDMs.push(ts);
        saveReadDMs();
        fetchMessagesAndNodes();
      }
    }
    function markAllDMsAsRead() {
      if (!confirm("Are you sure you want to mark ALL direct messages as read?")) return;
      let dms = allMessages.filter(m => m.direct);
      readDMs = dms.map(m => m.timestamp);
      saveReadDMs();
      fetchMessagesAndNodes();
    }
    function markChannelAsRead(channelIdx) {
      if (!confirm("Are you sure you want to mark ALL messages in this channel as read?")) return;
      let msgs = allMessages.filter(m => !m.direct && m.channel_idx == channelIdx);
      if (!readChannels) readChannels = {};
      readChannels[channelIdx] = msgs.map(m => m.timestamp);
      saveReadChannels();
      fetchMessagesAndNodes();
    }
    function isDMRead(ts) {
      return readDMs.includes(ts);
    }
    function isChannelMsgRead(ts, channelIdx) {
      return readChannels && readChannels[channelIdx] && readChannels[channelIdx].includes(ts);
    }

    // --- Ticker Dismissal State ---
    function setTickerDismissed(ts) {
      // Store the timestamp of the dismissed message and expiry
      localStorage.setItem("tickerDismissed", JSON.stringify({ts: ts, until: Date.now() + 30000}));
    }
    function isTickerDismissed(ts) {
      let obj = {};
      try { obj = JSON.parse(localStorage.getItem("tickerDismissed") || "{}"); } catch(e){}
      if (!obj.ts || !obj.until) return false;
      // Only dismiss if the same message and not expired
      return obj.ts === ts && Date.now() < obj.until;
    }

    // --- Timezone Offset State ---
    function getTimezoneOffset() {
      let tz = localStorage.getItem("meshtastic_ui_tz_offset");
      if (tz === null || isNaN(Number(tz))) return 0;
      return Number(tz);
    }
    function setTimezoneOffset(val) {
      localStorage.setItem("meshtastic_ui_tz_offset", String(val));
    }

    // Globals for reply targets
    var lastDMTarget = null;
    var lastChannelTarget = null;
    let allNodes = [];
    let allMessages = [];
    let lastMessageTimestamp = null;
    let tickerTimeout = null;
    let tickerLastShownTimestamp = null;
    let nodeGPSInfo = """ + node_gps_info_json + """;
    let myGPS = """ + my_gps_json + """;

    // --- Node Sorting ---
    let nodeSortKey = localStorage.getItem("nodeSortKey") || "name";
    let nodeSortDir = localStorage.getItem("nodeSortDir") || "asc";

    function setNodeSort(key, dir) {
      nodeSortKey = key;
      nodeSortDir = dir;
      localStorage.setItem("nodeSortKey", key);
      localStorage.setItem("nodeSortDir", dir);
      updateNodesUI(allNodes, false);
    }

    function compareNodes(a, b) {
      // Helper for null/undefined
      function safe(v) { return v === undefined || v === null ? "" : v; }
      // For distance, use haversine if both have GPS, else sort GPS-enabled first
      if (nodeSortKey === "distance") {
        let aGPS = nodeGPSInfo[String(a.id)];
        let bGPS = nodeGPSInfo[String(b.id)];
        let aHas = aGPS && aGPS.lat != null && aGPS.lon != null;
        let bHas = bGPS && bGPS.lat != null && bGPS.lon != null;
        if (!aHas && !bHas) return 0;
        if (aHas && !bHas) return -1;
        if (!aHas && bHas) return 1;
        let distA = calcDistance(myGPS.lat, myGPS.lon, aGPS.lat, aGPS.lon);
        let distB = calcDistance(myGPS.lat, myGPS.lon, bGPS.lat, bGPS.lon);
        return (distA - distB) * (nodeSortDir === "asc" ? 1 : -1);
      }
      if (nodeSortKey === "gps") {
        let aGPS = nodeGPSInfo[String(a.id)];
        let bGPS = nodeGPSInfo[String(b.id)];
        let aHas = aGPS && aGPS.lat != null && aGPS.lon != null;
        let bHas = bGPS && bGPS.lat != null && bGPS.lon != null;
        if (aHas && !bHas) return nodeSortDir === "asc" ? -1 : 1;
        if (!aHas && bHas) return nodeSortDir === "asc" ? 1 : -1;
        return 0;
      }
      if (nodeSortKey === "name") {
        let cmp = safe(a.shortName).localeCompare(safe(b.shortName), undefined, {sensitivity:"base"});
        return cmp * (nodeSortDir === "asc" ? 1 : -1);
      }
      if (nodeSortKey === "beacon") {
        let aGPS = nodeGPSInfo[String(a.id)];
        let bGPS = nodeGPSInfo[String(b.id)];
        let aTime = aGPS && aGPS.beacon_time ? Date.parse(aGPS.beacon_time.replace(" UTC","Z")) : 0;
        let bTime = bGPS && bGPS.beacon_time ? Date.parse(bGPS.beacon_time.replace(" UTC","Z")) : 0;
        return (bTime - aTime) * (nodeSortDir === "asc" ? -1 : 1);
      }
      if (nodeSortKey === "hops") {
        let aGPS = nodeGPSInfo[String(a.id)];
        let bGPS = nodeGPSInfo[String(b.id)];
        let aH = aGPS && aGPS.hops != null ? aGPS.hops : 99;
        let bH = bGPS && bGPS.hops != null ? bGPS.hops : 99;
        return (aH - bH) * (nodeSortDir === "asc" ? 1 : -1);
      }
      return 0;
    }

    // Haversine formula (km)
    function calcDistance(lat1, lon1, lat2, lon2) {
      if (
        lat1 == null || lon1 == null ||
        lat2 == null || lon2 == null
      ) return 99999;
      let toRad = x => x * Math.PI / 180;
      let R = 6371;
      let dLat = toRad(lat2 - lat1);
      let dLon = toRad(lon2 - lon1);
      let a = Math.sin(dLat/2) * Math.sin(dLat/2) +
              Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) *
              Math.sin(dLon/2) * Math.sin(dLon/2);
      let c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
      return R * c;
    }

    // --- UI Settings State ---
    let uiSettings = {
      themeColor: "#ffa500",
      hueRotateEnabled: false,
      hueRotateSpeed: 10,
      soundURL: ""
    };
    let hueRotateInterval = null;
    let currentHue = 0;

    function toggleMode(force) {
      if (typeof force !== "undefined") {
        document.getElementById('modeSwitch').checked = force === 'direct';
      }
      const dm = document.getElementById('modeSwitch').checked;
      document.getElementById('dmField').style.display = dm ? 'block' : 'none';
      document.getElementById('channelField').style.display = dm ? 'none' : 'block';
      document.getElementById('modeLabel').textContent = dm ? 'Direct' : 'Broadcast';
    }

    document.addEventListener("DOMContentLoaded", function() {
      document.getElementById('modeSwitch').addEventListener('change', function() {
        toggleMode();
      });
      document.getElementById('settingsToggle').addEventListener('click', function() {
        const panel = document.getElementById('settingsPanel');
        if (panel.style.display === 'none' || panel.style.display === '') {
          panel.style.display = 'block';
          this.textContent = "Hide UI Settings";
        } else {
          panel.style.display = 'none';
          this.textContent = "Show UI Settings";
        }
      });
      document.getElementById('settingsPanel').style.display = 'none'; // Hide settings panel by default
      document.getElementById('settingsToggle').textContent = "Show UI Settings";
      document.getElementById('nodeSearch').addEventListener('input', function() {
        filterNodes(this.value, false);
      });
      document.getElementById('destNodeSearch').addEventListener('input', function() {
        filterNodes(this.value, true);
      });

      // Node sort controls
      document.getElementById('nodeSortKey').addEventListener('change', function() {
        setNodeSort(this.value, nodeSortDir);
      });
      document.getElementById('nodeSortDir').addEventListener('change', function() {
        setNodeSort(nodeSortKey, this.value);
      });

      // --- UI Settings: Load from localStorage ---
      loadUISettings();

      // Set initial values in settings panel
      document.getElementById('uiColorPicker').value = uiSettings.themeColor;
      document.getElementById('hueRotateEnabled').checked = uiSettings.hueRotateEnabled;
      document.getElementById('hueRotateSpeed').value = uiSettings.hueRotateSpeed;
      document.getElementById('soundURL').value = uiSettings.soundURL;

      // Apply settings on load
      applyThemeColor(uiSettings.themeColor);
      if (uiSettings.hueRotateEnabled) startHueRotate(uiSettings.hueRotateSpeed);
      setIncomingSound(uiSettings.soundURL);

      // Apply button
      document.getElementById('applySettingsBtn').addEventListener('click', function() {
        // Read values
        uiSettings.themeColor = document.getElementById('uiColorPicker').value;
        uiSettings.hueRotateEnabled = document.getElementById('hueRotateEnabled').checked;
        uiSettings.hueRotateSpeed = parseFloat(document.getElementById('hueRotateSpeed').value);
        // For soundURL, only allow local file path from file input
        var fileInput = document.getElementById('soundFile');
        if (fileInput && fileInput.files.length > 0) {
          var file = fileInput.files[0];
          var url = URL.createObjectURL(file);
          uiSettings.soundURL = url;
          document.getElementById('soundURL').value = file.name;
        }
        saveUISettings();
        applyThemeColor(uiSettings.themeColor);
        if (uiSettings.hueRotateEnabled) {
          startHueRotate(uiSettings.hueRotateSpeed);
        } else {
          stopHueRotate();
        }
        setIncomingSound(uiSettings.soundURL);
        // Save timezone offset
        setTimezoneOffset(document.getElementById('timezoneSelect').value);
        fetchMessagesAndNodes();
      });

      // Listen for file input change to update sound preview
      document.getElementById('soundFile').addEventListener('change', function() {
        if (this.files.length > 0) {
          var file = this.files[0];
          var url = URL.createObjectURL(file);
          uiSettings.soundURL = url;
          document.getElementById('soundURL').value = file.name;
          setIncomingSound(url);
        }
      });

      // Set initial sort controls
      document.getElementById('nodeSortKey').value = nodeSortKey;
      document.getElementById('nodeSortDir').value = nodeSortDir;

      // Set timezone selector
      let tzSel = document.getElementById('timezoneSelect');
      let tz = getTimezoneOffset();
      tzSel.value = tz;
    });

    // --- UI Settings Functions ---
    function saveUISettings() {
      // Only persist the file name for sound, not the blob URL
      let settingsToSave = Object.assign({}, uiSettings);
      if (settingsToSave.soundURL && settingsToSave.soundURL.startsWith('blob:')) {
        settingsToSave.soundURL = document.getElementById('soundURL').value;
      }
      localStorage.setItem("meshtastic_ui_settings", JSON.stringify(settingsToSave));
    }
    function loadUISettings() {
      try {
        let s = localStorage.getItem("meshtastic_ui_settings");
        if (s) {
          let parsed = JSON.parse(s);
          Object.assign(uiSettings, parsed);
        }
      } catch (e) {}
    }
    function applyThemeColor(color) {
      document.documentElement.style.setProperty('--theme-color', color);
    }
    function startHueRotate(speed) {
      stopHueRotate();
      hueRotateInterval = setInterval(function() {
        currentHue = (currentHue + 1) % 360;
        document.body.style.filter = `hue-rotate(${currentHue}deg)`;
      }, Math.max(5, 1000 / Math.max(1, speed)));
    }
    function stopHueRotate() {
      if (hueRotateInterval) clearInterval(hueRotateInterval);
      hueRotateInterval = null;
      document.body.style.filter = "";
      currentHue = 0;
    }
    function toggleHueRotate(enabled, speed) {
      uiSettings.hueRotateEnabled = enabled;
      uiSettings.hueRotateSpeed = speed;
      saveUISettings();
      if (enabled) startHueRotate(speed);
      else stopHueRotate();
    }
    function setIncomingSound(url) {
      let audio = document.getElementById('incomingSound');
      audio.src = url || "";
      uiSettings.soundURL = url;
      saveUISettings();
    }

    function replyToMessage(mode, target) {
      toggleMode(mode);
      if (mode === 'direct') {
        const dest = document.getElementById('destNode');
        dest.value = target;
        const name = dest.selectedOptions[0] ? dest.selectedOptions[0].text.split(' (')[0] : '';
        document.getElementById('messageBox').value = '@' + name + ': ';
      } else {
        const ch = document.getElementById('channelSel');
        ch.value = target;
        document.getElementById('messageBox').value = '';
      }
    }

    function dmToNode(nodeId, shortName, replyToTs) {
      toggleMode('direct');
      document.getElementById('destNode').value = nodeId;
      if (replyToTs) {
        // Prefill with quoted message if replying to a thread
        let threadMsg = allMessages.find(m => m.timestamp === replyToTs);
        let quoted = threadMsg ? `> ${threadMsg.message}\n` : '';
        document.getElementById('messageBox').value = quoted + '@' + shortName + ': ';
      } else {
        document.getElementById('messageBox').value = '@' + shortName + ': ';
      }
    }

    function replyToLastDM() {
      if (lastDMTarget !== null) {
        const opt = document.querySelector(`#destNode option[value="${lastDMTarget}"]`);
        const shortName = opt ? opt.text.split(' (')[0] : '';
        dmToNode(lastDMTarget, shortName);
      } else {
        alert("No direct message target available.");
      }
    }

    function replyToLastChannel() {
      if (lastChannelTarget !== null) {
        toggleMode('broadcast');
        document.getElementById('channelSel').value = lastChannelTarget;
        document.getElementById('messageBox').value = '';
      } else {
        alert("No broadcast channel target available.");
      }
    }

    // Data fetch & UI updates
    const CHANNEL_NAMES = """ + json.dumps(channel_names) + """;

    function getNowUTC() {
      return new Date(new Date().toISOString().slice(0, 19) + "Z");
    }

    function getTZAdjusted(tsStr) {
      // tsStr is "YYYY-MM-DD HH:MM:SS UTC"
      let tz = getTimezoneOffset();
      if (!tsStr) return "";
      let dt = new Date(tsStr.replace(" UTC", "Z"));
      if (isNaN(dt.getTime())) return tsStr;
      dt.setHours(dt.getHours() + tz);
      let pad = n => n < 10 ? "0" + n : n;
      return dt.getFullYear() + "-" + pad(dt.getMonth()+1) + "-" + pad(dt.getDate()) + " " +
             pad(dt.getHours()) + ":" + pad(dt.getMinutes()) + ":" + pad(dt.getSeconds()) +
             (tz === 0 ? " UTC" : (tz > 0 ? " UTC+" + tz : " UTC" + tz));
    }

    function isRecent(tsStr, minutes) {
      if (!tsStr) return false;
      let now = getNowUTC();
      let msgTime = new Date(tsStr.replace(" UTC", "Z"));
      return (now - msgTime) < minutes * 60 * 1000;
    }

    async function fetchMessagesAndNodes() {
      try {
        let msgs = await (await fetch("/messages")).json();
        allMessages = msgs;
        let nodes = await (await fetch("/nodes")).json();
        allNodes = nodes;
        updateMessagesUI(msgs);
        updateNodesUI(nodes, false);
        updateNodesUI(nodes, true);
        updateDirectMessagesUI(msgs, nodes);
        highlightRecentNodes(nodes);
        showLatestMessageTicker(msgs);
        updateDiscordMessagesUI(msgs);
      } catch (e) { console.error(e); }
    }

    function updateMessagesUI(messages) {
      // Reverse the order to show the newest messages first
      const groups = {};
      messages.slice().reverse().forEach(m => {
        if (!m.direct && m.channel_idx != null) {
          (groups[m.channel_idx] = groups[m.channel_idx] || []).push(m);
        }
      });

      const channelDiv = document.getElementById("channelDiv");
      channelDiv.innerHTML = "";
      Object.keys(groups).sort().forEach(ch => {
        const name = CHANNEL_NAMES[ch] || `Channel ${ch}`;
        // Channel header with reply and mark all as read button
        const headerWrap = document.createElement("div");
        headerWrap.className = "channel-header";
        const header = document.createElement("h3");
        header.textContent = `${ch} – ${name}`;
        header.style.margin = 0;
        headerWrap.appendChild(header);

        // Add reply button for channel
        const replyBtn = document.createElement("button");
        replyBtn.textContent = "Send to Channel";
        replyBtn.className = "reply-btn";
        replyBtn.onclick = function() {
          replyToMessage('broadcast', ch);
        };
        headerWrap.appendChild(replyBtn);

        // Mark all as read for this channel
        const markAllBtn = document.createElement("button");
        markAllBtn.textContent = "Mark all as read";
        markAllBtn.className = "mark-all-read-btn";
        markAllBtn.onclick = function() {
          markChannelAsRead(ch);
        };
        headerWrap.appendChild(markAllBtn);

        channelDiv.appendChild(headerWrap);

        groups[ch].forEach(m => {
          if (isChannelMsgRead(m.timestamp, ch)) return; // Hide read messages
          const wrap = document.createElement("div");
          wrap.className = "message";
          if (isRecent(m.timestamp, 60)) wrap.classList.add("newMessage");
          const ts = document.createElement("div");
          ts.className = "timestamp";
          ts.textContent = `📢 ${getTZAdjusted(m.timestamp)} | ${m.node}`;
          const body = document.createElement("div");
          body.textContent = m.message;
          wrap.append(ts, body);

          // Mark as read button
          const markBtn = document.createElement("button");
          markBtn.textContent = "Mark as read";
          markBtn.className = "mark-read-btn";
          markBtn.onclick = function() {
            if (!readChannels[ch]) readChannels[ch] = [];
            if (!readChannels[ch].includes(m.timestamp)) {
              readChannels[ch].push(m.timestamp);
              saveReadChannels();
              fetchMessagesAndNodes();
            }
          };
          wrap.appendChild(markBtn);

          channelDiv.appendChild(wrap);
        });
        channelDiv.appendChild(document.createElement("hr"));
      });

      // Update global reply targets
      lastDMTarget = null;
      lastChannelTarget = null;
      for (const m of messages) {
        if (m.direct && m.node_id != null && lastDMTarget === null) {
          lastDMTarget = m.node_id;
        }
        if (!m.direct && m.channel_idx != null && lastChannelTarget === null) {
          lastChannelTarget = m.channel_idx;
        }
        if (lastDMTarget != null && lastChannelTarget != null) break;
      }
    }

    // --- DM Threaded UI ---
    function updateDirectMessagesUI(messages, nodes) {
      // Group DMs by node_id, then by thread (reply_to)
      const dmDiv = document.getElementById("dmMessagesDiv");
      dmDiv.innerHTML = "";

      // Only direct messages, newest first
      let dms = messages.filter(m => m.direct && !isDMRead(m.timestamp)).slice().reverse();

      // Group by node_id
      let threads = {};
      dms.forEach(m => {
        if (!threads[m.node_id]) threads[m.node_id] = [];
        threads[m.node_id].push(m);
      });

      // Mark all as read button for DMs
      if (dms.length > 0) {
        const markAllBtn = document.createElement("button");
        markAllBtn.textContent = "Mark all as read";
        markAllBtn.className = "mark-all-read-btn";
        markAllBtn.onclick = function() {
          markAllDMsAsRead();
        };
        dmDiv.appendChild(markAllBtn);
      }

      Object.keys(threads).forEach(nodeId => {
        const node = allNodes.find(n => n.id == nodeId);
        const shortName = node ? node.shortName : nodeId;
        const threadDiv = document.createElement("div");
        threadDiv.className = "dm-thread";

        // Find root messages (no reply_to)
        let rootMsgs = threads[nodeId].filter(m => !m.reply_to);

        rootMsgs.forEach(rootMsg => {
          const wrap = document.createElement("div");
          wrap.className = "message";
          if (isRecent(rootMsg.timestamp, 60)) wrap.classList.add("newMessage");
          const ts = document.createElement("div");
          ts.className = "timestamp";
          ts.textContent = `📩 ${getTZAdjusted(rootMsg.timestamp)} | ${rootMsg.node}`;
          const body = document.createElement("div");
          body.textContent = rootMsg.message;
          wrap.append(ts, body);

          // Add reply button for root
          const replyBtn = document.createElement("button");
          replyBtn.textContent = "Reply";
          replyBtn.className = "reply-btn";
          replyBtn.onclick = function() {
            dmToNode(nodeId, shortName, rootMsg.timestamp);
          };
          wrap.appendChild(replyBtn);

          // Mark as read button for root
          const markBtn = document.createElement("button");
          markBtn.textContent = "Mark as read";
          markBtn.className = "mark-read-btn";
          markBtn.onclick = function() {
            markDMAsRead(rootMsg.timestamp);
          };
          wrap.appendChild(markBtn);

          threadDiv.appendChild(wrap);

          // Find replies to this root
          let replies = threads[nodeId].filter(m => m.reply_to === rootMsg.timestamp);
          if (replies.length) {
            const repliesDiv = document.createElement("div");
            repliesDiv.className = "thread-replies";
            replies.forEach(replyMsg => {
              const replyWrap = document.createElement("div");
              replyWrap.className = "message";
              if (isRecent(replyMsg.timestamp, 60)) replyWrap.classList.add("newMessage");
              const rts = document.createElement("div");
              rts.className = "timestamp";
              rts.textContent = `↪️ ${getTZAdjusted(replyMsg.timestamp)} | ${replyMsg.node}`;
              const rbody = document.createElement("div");
              rbody.textContent = replyMsg.message;
              replyWrap.append(rts, rbody);

              // Reply to reply (threaded)
              const replyBtn2 = document.createElement("button");
              replyBtn2.textContent = "Reply";
              replyBtn2.className = "reply-btn";
              replyBtn2.onclick = function() {
                dmToNode(nodeId, shortName, replyMsg.timestamp);
              };
              replyWrap.appendChild(replyBtn2);

              // Mark as read button for reply
              const markBtn2 = document.createElement("button");
              markBtn2.textContent = "Mark as read";
              markBtn2.className = "mark-read-btn";
              markBtn2.onclick = function() {
                markDMAsRead(replyMsg.timestamp);
              };
              replyWrap.appendChild(markBtn2);

              repliesDiv.appendChild(replyWrap);
            });
            threadDiv.appendChild(repliesDiv);
          }
        });

        dmDiv.appendChild(threadDiv);
      });
    }

    function updateNodesUI(nodes, isDest) {
      // isDest: false = available nodes panel, true = destination node dropdown
      if (!isDest) {
        const list = document.getElementById("nodeListDiv");
        let filter = document.getElementById('nodeSearch').value.toLowerCase();
        list.innerHTML = "";
        let filtered = nodes.filter(n =>
          (n.shortName && n.shortName.toLowerCase().includes(filter)) ||
          (n.longName && n.longName.toLowerCase().includes(filter)) ||
          String(n.id).toLowerCase().includes(filter)
        );
        // Sort
        filtered.sort(compareNodes);

        filtered.forEach(n => {
          const d = document.createElement("div");
          d.className = "nodeItem";
          if (isRecentNode(n.id)) d.classList.add("recentNode");

          // Main line: Short name and ID
          const mainLine = document.createElement("div");
          mainLine.className = "nodeMainLine";
          mainLine.innerHTML = `<span>${n.shortName || ""}</span> <span style="color:#ffa500;">(${n.id})</span>`;
          d.appendChild(mainLine);

          // Long name (if present)
          if (n.longName && n.longName !== n.shortName) {
            const longName = document.createElement("div");
            longName.className = "nodeLongName";
            longName.textContent = n.longName;
            d.appendChild(longName);
          }

          // Info line 1: GPS/map, distance
          const infoLine1 = document.createElement("div");
          infoLine1.className = "nodeInfoLine";
          let gps = nodeGPSInfo[String(n.id)];
          if (gps && gps.lat != null && gps.lon != null) {
            // Map button (emoji)
            const mapA = document.createElement("a");
            mapA.href = `https://www.google.com/maps/search/?api=1&query=${gps.lat},${gps.lon}`;
            mapA.target = "_blank";
            mapA.className = "nodeMapBtn";
            mapA.title = "Show on Google Maps";
            mapA.innerHTML = "🗺️";
            infoLine1.appendChild(mapA);

            // Distance
            if (myGPS && myGPS.lat != null && myGPS.lon != null) {
              let dist = calcDistance(myGPS.lat, myGPS.lon, gps.lat, gps.lon);
              if (dist < 99999) {
                const distSpan = document.createElement("span");
                distSpan.className = "nodeGPS";
                distSpan.title = "Approximate distance from connected node";
                distSpan.innerHTML = `📏 ${dist.toFixed(2)} km`;
                infoLine1.appendChild(distSpan);
              }
            }
          }
          d.appendChild(infoLine1);

          // Info line 2: Beacon/reporting time
          const infoLine2 = document.createElement("div");
          infoLine2.className = "nodeInfoLine";
          if (gps && gps.beacon_time) {
            const beacon = document.createElement("span");
            beacon.className = "nodeBeacon";
            beacon.title = "Last beacon/reporting time";
            beacon.innerHTML = `🕒 ${getTZAdjusted(gps.beacon_time)}`;
            infoLine2.appendChild(beacon);
          }
          d.appendChild(infoLine2);

          // Info line 3: Hops
          const infoLine3 = document.createElement("div");
          infoLine3.className = "nodeInfoLine";
          // Only show hops if available and not null/undefined/""
          if (gps && gps.hops != null && gps.hops !== "" && gps.hops !== undefined) {
            const hops = document.createElement("span");
            hops.className = "nodeHops";
            hops.title = "Hops from this node";
            hops.innerHTML = `⛓️ ${gps.hops} hop${gps.hops==1?"":"s"}`;
            infoLine3.appendChild(hops);
            d.appendChild(infoLine3);
          }
          // If hops is not available, do not show this section at all

          // DM button
          const btn = document.createElement("button");
          btn.textContent = "DM";
          btn.className = "btn";
          btn.onclick = () => dmToNode(n.id, n.shortName);
          d.append(btn);

          list.appendChild(d);
        });
      } else {
        const sel  = document.getElementById("destNode");
        const prevNode = sel.value;
        sel.innerHTML  = "<option value=''>--Select Node--</option>";
        let filter = document.getElementById('destNodeSearch').value.toLowerCase();
        let filtered = nodes.filter(n =>
          (n.shortName && n.shortName.toLowerCase().includes(filter)) ||
          (n.longName && n.longName.toLowerCase().includes(filter)) ||
          String(n.id).toLowerCase().includes(filter)
        );
        filtered.forEach(n => {
          const opt = document.createElement("option");
          opt.value = n.id;
          opt.innerHTML = `${n.shortName} (${n.id})`;
          sel.append(opt);
        });
        sel.value = prevNode;
      }
    }

    function filterNodes(val, isDest) {
      updateNodesUI(allNodes, isDest);
    }

    // Track recently discovered nodes (seen in last hour)
    function isRecentNode(nodeId) {
      // Find the latest message from this node
      let found = allMessages.slice().reverse().find(m => m.node_id == nodeId);
      if (!found) return false;
      return isRecent(found.timestamp, 60);
    }

    function highlightRecentNodes(nodes) {
      // Called after updateNodesUI
      // No-op: handled by .recentNode class in updateNodesUI
    }

    // Show latest inbound message in ticker, dismissable, timeout after 30s, and persist dismiss across refreshes
    function showLatestMessageTicker(messages) {
      // Show both channel and direct inbound messages, but not outgoing (WebUI, Discord, Twilio, DiscordPoll, AI_NODE_NAME)
      // and not AI responses (reply_to is not null)
      let inbound = messages.filter(m =>
        m.node !== "WebUI" &&
        m.node !== "Discord" &&
        m.node !== "Twilio" &&
        m.node !== "DiscordPoll" &&
        m.node !== """ + json.dumps(AI_NODE_NAME) + """ &&
        (!m.reply_to) // Only show original messages, not replies (AI responses)
      );
      if (!inbound.length) return hideTicker();
      let latest = inbound[inbound.length - 1];
      if (!latest || !latest.message) return hideTicker();

      // If dismissed, don't show
      if (isTickerDismissed(latest.timestamp)) return hideTicker();

      // Only show ticker if not already shown for this message
      if (tickerLastShownTimestamp === latest.timestamp) return;
      tickerLastShownTimestamp = latest.timestamp;

      let ticker = document.getElementById('ticker');
      let tickerMsg = ticker.querySelector('p');
      tickerMsg.textContent = latest.message;
      ticker.style.display = 'block';

      // Show dismiss button at far right, on top
      let dismissBtn = ticker.querySelector('.dismiss-btn');
      if (!dismissBtn) {
        dismissBtn = document.createElement('button');
        dismissBtn.textContent = "Dismiss";
        dismissBtn.className = "dismiss-btn";
        dismissBtn.onclick = function(e) {
          e.stopPropagation();
          ticker.style.display = 'none';
          setTickerDismissed(latest.timestamp);
          if (tickerTimeout) clearTimeout(tickerTimeout);
        };
        ticker.appendChild(dismissBtn);
      } else {
        // Always update dismiss button to dismiss this message
        dismissBtn.onclick = function(e) {
          e.stopPropagation();
          ticker.style.display = 'none';
          setTickerDismissed(latest.timestamp);
          if (tickerTimeout) clearTimeout(tickerTimeout);
        };
      }

      // Remove after 30s and persist dismiss
      if (tickerTimeout) clearTimeout(tickerTimeout);
      tickerTimeout = setTimeout(() => {
        ticker.style.display = 'none';
        setTickerDismissed(latest.timestamp);
        tickerLastShownTimestamp = null;
      }, 30000);
    }

    function hideTicker() {
      let ticker = document.getElementById('ticker');
      ticker.style.display = 'none';
      tickerLastShownTimestamp = null;
      if (tickerTimeout) {
        clearTimeout(tickerTimeout);
        tickerTimeout = null;
      }
    }

    function pollStatus() {
      fetch("/connection_status")
        .then(r => r.json())
        .then(d => {
          const s = document.getElementById("connectionStatus");
          if (d.status != "Connected") {
            s.style.background = "red";
            s.style.height = "40px";
            s.textContent = `Connection Error: ${d.error}`;
          } else {
            s.style.background = "green";
            s.style.height = "20px";
            s.textContent = "Connected";
          }
        })
        .catch(e => console.error(e));
    }
    setInterval(pollStatus, 5000);

    function onPageLoad() {
      setInterval(fetchMessagesAndNodes, 10000);
      fetchMessagesAndNodes();
      toggleMode(); // Set initial mode
    }
    window.addEventListener("load", onPageLoad);

    // --- Discord Messages Section ---
    function updateDiscordMessagesUI(messages) {
      // Only show Discord messages if any exist
      let discordMsgs = messages.filter(m => m.node === "Discord" || m.node === "DiscordPoll");
      let discordSection = document.getElementById("discordSection");
      let discordDiv = document.getElementById("discordMessagesDiv");
      if (discordMsgs.length === 0) {
        discordSection.style.display = "none";
        discordDiv.innerHTML = "";
        return;
      }
      discordSection.style.display = "block";
      discordDiv.innerHTML = "";
      discordMsgs.forEach(m => {
        const wrap = document.createElement("div");
        wrap.className = "message";
        if (isRecent(m.timestamp, 60)) wrap.classList.add("newMessage");
        const ts = document.createElement("div");
        ts.className = "timestamp";
        ts.textContent = `💬 ${getTZAdjusted(m.timestamp)} | ${m.node}`;
        const body = document.createElement("div");
        body.textContent = m.message;
        wrap.append(ts, body);
        discordDiv.appendChild(wrap);
      });
    }
  </script>
</head>
<body onload="onPageLoad()">
  <div id="connectionStatus"></div>
  <div class="header-buttons"><a href="/logs" target="_blank">Logs</a></div>
  <div id="ticker-container">
    <div id="ticker"><p></p></div>
  </div>
  <audio id="incomingSound"></audio>

  <div class="lcars-panel" id="sendForm">
    <h2>Send a Message</h2>
    <form method="POST" action="/ui_send">
      <label>Message Mode:</label>
      <label class="switch">
        <input type="checkbox" id="modeSwitch">
        <span class="slider round"></span>
      </label>
      <span id="modeLabel">Broadcast</span><br><br>

      <div id="dmField" style="display:none;">
        <label>Destination Node:</label><br>
        <input type="text" id="destNodeSearch" placeholder="Search destination nodes..."><br>
        <select id="destNode" name="destination_node"></select><br><br>
      </div>

      <div id="channelField" style="display:block;">
        <label>Channel:</label><br>
        <select id="channelSel" name="channel_index">
"""
    for i in range(8):
        name = channel_names.get(str(i), f"Channel {i}")
        html += f"          <option value='{i}'>{i} - {name}</option>\n"
    html += """        </select><br><br>
      </div>

      <label>Message:</label><br>
      <textarea id="messageBox" name="message" rows="3" style="width:80%;"></textarea>
      <div id="charCounter">Characters: 0/1000, Chunks: 0/5</div><br>
      <button type="submit">Send</button>
      <button type="button" onclick="replyToLastDM()">Reply to Last DM</button>
      <button type="button" onclick="replyToLastChannel()">Reply to Last Channel</button>
    </form>
  </div>

  <div class="three-col">
    <div class="col">
      <div class="lcars-panel">
        <h2>Channel Messages</h2>
        <div id="channelDiv"></div>
      </div>
    </div>
    <div class="col">
      <div class="lcars-panel">
        <h2>Available Nodes</h2>
        <input type="text" id="nodeSearch" placeholder="Search nodes by name, id, or long name...">
        <div class="nodeSortBar">
          <label for="nodeSortKey">Sort by:</label>
          <select id="nodeSortKey">
            <option value="name">Name</option>
            <option value="beacon">Last Reporting Time</option>
            <option value="hops">Number of Hops</option>
            <option value="gps">GPS Enabled</option>
            <option value="distance">Distance</option>
          </select>
          <label for="nodeSortDir">Order:</label>
          <select id="nodeSortDir">
            <option value="asc">Ascending</option>
            <option value="desc">Descending</option>
          </select>
        </div>
        <div id="nodeListDiv"></div>
      </div>
    </div>
    <div class="col">
      <div class="lcars-panel">
        <h2>Direct Messages</h2>
        <div id="dmMessagesDiv"></div>
      </div>
    </div>
  </div>

  <div class="lcars-panel" id="discordSection" style="margin:20px;">
    <h2>Discord Messages</h2>
    <div id="discordMessagesDiv"></div>
  </div>

  <div class="settings-toggle" id="settingsToggle">Show UI Settings</div>
  <div class="settings-panel" id="settingsPanel">
    <h2>UI Settings</h2>
    <label for="uiColorPicker">Theme Color:</label>
    <input type="color" id="uiColorPicker" value="#ffa500"><br><br>
    <label for="hueRotateEnabled">Enable Hue Rotation:</label>
    <input type="checkbox" id="hueRotateEnabled"><br><br>
    <label for="hueRotateSpeed">Hue Rotation Speed:</label>
    <input type="range" id="hueRotateSpeed" min="5" max="60" step="0.1" value="10"><br><br>
    <label for="soundFile">Incoming Message Sound (local file):</label>
    <input type="file" id="soundFile" accept="audio/*"><br>
    <input type="text" id="soundURL" placeholder="No file selected" readonly style="background:#222;color:#fff;border:none;"><br><br>
    <label for="timezoneSelect">Timezone Offset (hours):</label>
    <select id="timezoneSelect">
"""
    # Timezone selector: -12 to +14
    for tz in range(-12, 15):
        html += f'      <option value="{tz}">{tz:+d}</option>\n'
    html += """    </select><br><br>
    <button id="applySettingsBtn" type="button">Apply Settings</button>
  </div>
</body>
</html>
"""
    return html
@app.route("/ui_send", methods=["POST"])
def ui_send():
    message = request.form.get("message", "").strip()
    mode = "direct" if request.form.get("destination_node", "") != "" else "broadcast"
    if mode == "direct":
        dest_node = request.form.get("destination_node", "").strip()
    else:
        dest_node = None
    if mode == "broadcast":
        channel_idx = int(request.form.get("channel_index", "0"))
    else:
        channel_idx = None
    if not message:
        return redirect(url_for("dashboard"))
    try:
        if mode == "direct" and dest_node:
            dest_info = f"{get_node_shortname(dest_node)} ({dest_node})"
            log_message("WebUI", f"{message} [to: {dest_info}]", direct=True)
            info_print(f"[UI] Direct message to node {dest_info} => '{message}'")
            send_direct_chunks(interface, message, dest_node)
        else:
            log_message("WebUI", f"{message} [to: Broadcast Channel {channel_idx}]", direct=False, channel_idx=channel_idx)
            info_print(f"[UI] Broadcast on channel {channel_idx} => '{message}'")
            send_broadcast_chunks(interface, message, channel_idx)
    except Exception as e:
        print(f"⚠️ /ui_send error: {e}")
    return redirect(url_for("dashboard"))

@app.route("/send", methods=["POST"])
def send_message():
    dprint("POST /send => manual JSON send")
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No JSON payload"}), 400
    message = data.get("message")
    node_id = data.get("node_id")
    channel_idx = data.get("channel_index", 0)
    direct = data.get("direct", False)
    if not message or node_id is None:
        return jsonify({"status": "error", "message": "Missing 'message' or 'node_id'"}), 400
    try:
        if direct:
            log_message("WebUI", f"{message} [to: {get_node_shortname(node_id)} ({node_id})]", direct=True)
            info_print(f"[Info] Direct send to node {node_id} => '{message}'")
            send_direct_chunks(interface, message, node_id)
            return jsonify({"status": "sent", "to": node_id, "direct": True, "message": message})
        else:
            log_message("WebUI", f"{message} [to: Broadcast Channel {channel_idx}]", direct=False, channel_idx=channel_idx)
            info_print(f"[Info] Broadcast on ch={channel_idx} => '{message}'")
            send_broadcast_chunks(interface, message, channel_idx)
            return jsonify({"status": "sent", "to": f"channel {channel_idx}", "message": message})
    except Exception as e:
        print(f"⚠️ Failed to send: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

def connect_interface():
    """Return a Meshtastic interface with the baud rate from config.

    Resolution order:
      1. Wi‑Fi TCP bridge
      2. Local MeshInterface()
      3. USB SerialInterface (explicit path or auto‑detect)
    """
    global connection_status, last_error_message
    try:
        # 1️⃣  Wi‑Fi bridge -------------------------------------------------
        if USE_WIFI and WIFI_HOST and TCPInterface is not None:
            print(f"TCPInterface → {WIFI_HOST}:{WIFI_PORT}")
            connection_status, last_error_message = "Connected", ""
            return TCPInterface(hostname=WIFI_HOST, portNumber=WIFI_PORT)

        # 2️⃣  Local mesh interface ---------------------------------------
        if USE_MESH_INTERFACE and MESH_INTERFACE_AVAILABLE:
            print("MeshInterface() for direct‑radio mode")
            connection_status, last_error_message = "Connected", ""
            return MeshInterface()

        # 3️⃣  USB serial --------------------------------------------------
        if SERIAL_PORT:
            print(f"SerialInterface on '{SERIAL_PORT}' (default baud, will switch to {SERIAL_BAUD}) …")
            iface = meshtastic.serial_interface.SerialInterface(devPath=SERIAL_PORT)
        else:
            print(f"SerialInterface auto‑detect (default baud, will switch to {SERIAL_BAUD}) …")
            iface = meshtastic.serial_interface.SerialInterface()

        # Attempt to change baudrate after opening
        try:
            ser = getattr(iface, "_serial", None)
            if ser is not None and hasattr(ser, "baudrate"):
                ser.baudrate = SERIAL_BAUD
                print(f"Baudrate switched to {SERIAL_BAUD}")
        except Exception as e:
            print(f"⚠️ could not set baudrate to {SERIAL_BAUD}: {e}")

        connection_status, last_error_message = "Connected", ""
        return iface

    except Exception as exc:
        connection_status, last_error_message = "Disconnected", str(exc)
        add_script_log(f"Connection error: {exc}")
        raise

def thread_excepthook(args):
    logging.error(f"Meshtastic thread error: {args.exc_value}")
    traceback.print_exception(args.exc_type, args.exc_value, args.exc_traceback)
    global connection_status
    connection_status = "Disconnected"
    reset_event.set()

threading.excepthook = thread_excepthook

@app.route("/connection_status", methods=["GET"])
def connection_status_route():
    return jsonify({"status": connection_status, "error": last_error_message})

def main():
    global interface, restart_count, server_start_time, reset_event
    server_start_time = server_start_time or datetime.now(timezone.utc)
    restart_count += 1
    add_script_log(f"Server restarted. Restart count: {restart_count}")
    print("Starting Meshtastic-AI server...")
    load_archive()
        # Additional startup info:
    if ENABLE_DISCORD:
        print(f"Discord configuration enabled: Inbound channel index: {DISCORD_INBOUND_CHANNEL_INDEX}, Webhook URL is {'set' if DISCORD_WEBHOOK_URL else 'not set'}, Bot Token is {'set' if DISCORD_BOT_TOKEN else 'not set'}, Channel ID is {'set' if DISCORD_CHANNEL_ID else 'not set'}.")
    else:
        print("Discord configuration disabled.")
    if ENABLE_TWILIO:
        if TWILIO_SID and TWILIO_AUTH_TOKEN and ALERT_PHONE_NUMBER and TWILIO_FROM_NUMBER:
            print("Twilio is configured for emergency SMS.")
        else:
            print("Twilio is not properly configured for emergency SMS.")
    else:
        print("Twilio is disabled.")
    if ENABLE_SMTP:
        if SMTP_HOST and SMTP_USER and SMTP_PASS and ALERT_EMAIL_TO:
            print("SMTP is configured for emergency email alerts.")
        else:
            print("SMTP is not properly configured for emergency email alerts.")
    else:
        print("SMTP is disabled.")
    print("Launching Flask in the background on port 5000...")
    api_thread = threading.Thread(
        target=app.run,
        kwargs={"host": "0.0.0.0", "port": 5000, "debug": False},
        daemon=True
    )
    api_thread.start()
    # If Discord polling is configured, start that thread.
    if DISCORD_BOT_TOKEN and DISCORD_CHANNEL_ID:
        threading.Thread(target=poll_discord_channel, daemon=True).start()
    while True:
        try:
            print("---------------------------------------------------")
            print("Attempting to connect to Meshtastic device...")
            try:
                pub.unsubscribe(on_receive, "meshtastic.receive")
            except Exception:
                pass
            try:
                if interface:
                    interface.close()
            except Exception:
                pass
            interface = connect_interface()
            print("Subscribing to on_receive callback...")
            pub.subscribe(on_receive, "meshtastic.receive")
            print(f"AI provider set to: {AI_PROVIDER}")
            if HOME_ASSISTANT_ENABLED:
                print(f"Home Assistant multi-mode is ENABLED. Channel index: {HOME_ASSISTANT_CHANNEL_INDEX}")
                if HOME_ASSISTANT_ENABLE_PIN:
                    print("Home Assistant secure PIN protection is ENABLED.")
            print("Connection successful. Running until error or Ctrl+C.")
            add_script_log("Connection established successfully.")
            # Inner loop: periodically check if a reset has been signaled
            while not reset_event.is_set():
                time.sleep(1)
            raise OSError("Reset event triggered due to connection loss")
        except KeyboardInterrupt:
            print("User interrupted the script. Shutting down.")
            add_script_log("Server shutdown via KeyboardInterrupt.")
            break
        except OSError as e:
            error_code = getattr(e, 'errno', None) or getattr(e, 'winerror', None)
            if error_code in (10053, 10054, 10060):
                print("⚠️ Connection was forcibly closed. Attempting to reconnect...")
                add_script_log(f"Connection forcibly closed: {e} (error code: {error_code})")
                time.sleep(5)
                reset_event.clear()
                continue
        except Exception as e:
            logging.error(f"⚠️ Connection/runtime error: {e}")
            add_script_log(f"Error: {e}")
            print("Will attempt reconnect in 30 seconds...")
            try:
                interface.close()
            except Exception:
                pass
            time.sleep(30)
            reset_event.clear()
            continue

def connection_monitor(initial_delay=30):
    global connection_status
    time.sleep(initial_delay)
    while True:
        if connection_status == "Disconnected":
            print("⚠️ Connection lost! Triggering reconnect...")
            reset_event.set()
        time.sleep(5)

# Start the watchdog thread after 20 seconds to give node a chance to connect
def poll_discord_channel():
    """Polls the Discord channel for new messages using the Discord API."""
    # Wait a short period for interface to be set up
    time.sleep(5)
    last_message_id = None
    headers = {"Authorization": f"Bot {DISCORD_BOT_TOKEN}"}
    url = f"https://discord.com/api/v9/channels/{DISCORD_CHANNEL_ID}/messages"
    while True:
        try:
            params = {"limit": 10}
            if last_message_id:
                params["after"] = last_message_id
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                msgs = response.json()
                msgs = sorted(msgs, key=lambda m: int(m["id"]))
                for msg in msgs:
                    if msg["author"].get("bot"):
                        continue
                    # Only process messages that arrived after the script started
                    if last_message_id is None:
                        msg_timestamp_str = msg.get("timestamp")
                        if msg_timestamp_str:
                            msg_time = datetime.fromisoformat(msg_timestamp_str.replace("Z", "+00:00"))
                            if msg_time < server_start_time:
                                continue
                    username = msg["author"].get("username", "DiscordUser")
                    content = msg.get("content")
                    if content:
                        formatted = f"**{username}**: {content}"
                        log_message("DiscordPoll", formatted, direct=False, channel_idx=DISCORD_INBOUND_CHANNEL_INDEX)
                        if interface is None:
                            print("❌ Cannot send polled Discord message: interface is None.")
                        else:
                            send_broadcast_chunks(interface, formatted, DISCORD_INBOUND_CHANNEL_INDEX)
                        print(f"Polled and routed Discord message: {formatted}")
                        last_message_id = msg["id"]
            else:
                print(f"Discord poll error: {response.status_code} {response.text}")
        except Exception as e:
            print(f"Error polling Discord: {e}")
        time.sleep(10)

if __name__ == "__main__":
    while True:
        try:
            main()
        except KeyboardInterrupt:
            print("User interrupted the script. Exiting.")
            add_script_log("Server exited via KeyboardInterrupt.")
            break
        except Exception as e:
            logging.error(f"Unhandled error in main: {e}")
            add_script_log(f"Unhandled error: {e}")
            print("Encountered an error. Restarting in 30 seconds...")
            time.sleep(30)
