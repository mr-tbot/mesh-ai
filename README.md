Meshtastic-AI: Off-Grid AI Chat Bot - ALPHA v0.1 - THE FIRST PUBLIC RELEASE!

Overview

Meshtastic-AI is an open-source project designed to integrate AI with Meshtastic nodes for off-grid communication. The bot listens for direct messages from users or /commands in the mesh network and responds by relaying information from LMStudio API (OpenAI and ollama coming soon). This allows users to interact with the system, ask questions, and receive AI-generated responses—even in remote areas without internet access.

Unlike traditional messaging systems, Meshtastic-AI does not focus on sending and receiving general messages across the mesh network. Instead, it serves as a bridge for off-grid questions and answers. It listens for direct messages or commands and uses an AI model to generate and send responses based on the query or command.

This script has been successfully tested on Windows 11 - but will possibly work on Linux and MacOS operating systems with a little extra work.  Official Linux and MacOS support will come in time with community help.

Testing Hardware: This has been tested on Meshtastic 2.5.20 using a Heltec V3 board with LMStudio 0.3.9 Beta 6 on Windows 11.  OpenAI functionality remains broken for the time being - but will be implemented soon!

Serial Mode Tools: Additional Python scripts for automating the enabling of serial mode will be included in the release.  These were paramount in helping me get this working initially - and others might find some benefit in them.


_____________________________________________________________________________________________________________________________________________________________

Key Features:

- AI-Driven Responses: Relays messages to an AI service like LMStudio or OpenAI (coming soon) for generating intelligent responses.
- Command Handling: Listens for specific commands in the mesh network, such as /ai, /whereami, or /emergency, and responds accordingly.
- Message Chunking: Implements chunked message delivery to avoid congestion and maximize the effective use of the limited radio bandwidth on the mesh network.
- Emergency Alerts: Provides functionality for sending emergency SMS or email alerts through Twilio and SMTP.
- Web Interface: Exposes a simple web dashboard for viewing messages and managing the system via HTTP.

_____________________________________________________________________________________________________________________________________________________________

How It Works
Message Handling and Command Response

The script is designed to listen for two types of messages:

Direct Messages: 

These are messages sent directly to the node on the mesh network. When a user sends a direct message to the node (e.g., asking a question), the system forwards this message to an AI service for processing and then sends the AI’s response back to the requesting node.

Slash Commands: 

These are commands sent in channels where the node is active. Commands such as /ai, /whereami, and /emergency are interpreted by the system, and based on the command, an appropriate response is generated and sent back to the channel or directly to the user.

_____________________________________________________________________________________________________________________________________________________________

The AI Service:

The bot integrates with LMStudio or (soon) OpenAI APIs. When the bot receives a question or query, it forwards this to the configured AI service. It processes the response and sends it back to the mesh network, allowing users to receive intelligent answers, even without internet access.  Any model can be useed - as this script only acts as a forarder between the LMStudio or OpenAI API and the Meshtastic Network...  So - tailored models can be used in various situations...  You could have a model that is specifically for assistance or data or a model that just cracks jokes - you could even have a model that role plays while you are out playing airsoft - for example.


Chunking and Network Optimization
Since Meshtastic operates on a low bandwidth, limited duty cycle, especially in areas with regulatory restrictions (e.g., Europe’s 10% duty cycle limit), it is crucial to minimize congestion on the network.

Meshtastic-AI uses message chunking to break long responses into smaller pieces, ensuring that each message is transmitted efficiently without overloading the network. These chunks are sent with a delay between each to ensure that the system adheres to Meshtastic’s duty cycle limitations.

Chunk Size and Delay: You can adjust the chunk size, maximum number of chunks, and delay between chunks in the config.json file:
chunk_size: Defines the maximum size of each chunk of a message.
max_ai_chunks: Limits the maximum number of chunks to send for a single message.
chunk_delay: Sets a delay (in seconds) between sending each chunk to prevent network congestion.
Maximum Token Calculation for LMStudio
To reduce the risk of truncated AI responses, Meshtastic-AI automatically calculates the maximum number of tokens for LMStudio based on the chunk size and number of chunks. This ensures that responses from the AI are as complete as possible while adhering to the token limit. The token limit is calculated as:

_____________________________________________________________________________________________________________________________________________________________

// MAX_RESPONSE_LENGTH = chunk_size * max_ai_chunks

_____________________________________________________________________________________________________________________________________________________________

This calculated length determines how much text the system can send in a single response, optimizing the balance between message size and token limits to avoid truncation.

Client Mode
The node running the system should be in "Client_Mute" mode to maximize the AI response efficiency. In this mode, the node does not send unnecessary beacons or forward other messages, leaving more of the duty cycle available for AI response transmissions.

Why Client_Mute Mode?: Other modes may send additional messages that could interfere with the timely delivery of responses. This is especially important in areas where the duty cycle is limited (e.g., in Europe, where the duty cycle is 10%). Testing has shown that placing the node in Client_Mute mode ensures that most of the duty cycle is available for responding to AI queries.

_____________________________________________________________________________________________________________________________________________________________


Configuration

config.json
The configuration file allows you to adjust various settings, including the AI service configuration, chunking parameters, and emergency alert settings.

- lmstudio_url: The URL of the LMStudio API server. Default: "http://localhost:1234/v1/chat/completions".
- lmstudio_timeout: The timeout for AI requests. Default: 60 seconds.
- chunk_size: The size of each chunk of a message. Default: 200 characters.
- max_ai_chunks: The maximum number of chunks allowed for a single message. Default: 4.
- chunk_delay: The delay between sending each chunk. Default: 10 seconds.
- local_location_string: The string identifying the location of the node. Default: "Near Boulder Station".
- ai_node_name: The name of the AI node. Default: "Mesh-AI-Alpha".
- force_node_num: Optionally override the node number. Default: null.
- enable_twilio: Whether to enable Twilio SMS notifications. Default: false.
- enable_smtp: Whether to enable SMTP email notifications. Default: false.

_____________________________________________________________________________________________________________________________________________________________

// Example config.json (default settings):

{
  "debug": false,
  "use_mesh_interface": false,
  "lmstudio_url": "http://localhost:1234/v1/chat/completions",
  "lmstudio_timeout": 60,
  "chunk_size": 200,
  "max_ai_chunks": 4,
  "chunk_delay": 10,
  "local_location_string": "Near Boulder Station",
  "ai_node_name": "Mesh-AI-Alpha",
  "force_node_num": null,
  "enable_twilio": false,
  "enable_smtp": false,
  "alert_phone_number": "+15555555555",
  "twilio_sid": "ACXXXX",
  "twilio_auth_token": "XXXX",
  "twilio_from_number": "+14444444444",
  "smtp_host": "smtp.gmail.com",
  "smtp_port": 587,
  "smtp_user": "myemail@gmail.com",
  "smtp_pass": "mypassword",
  "alert_email_to": "emergency@recipient.com"
}


_____________________________________________________________________________________________________________________________________________________________


Channel /Slash Commands

Meshtastic-AI listens for the following built-in commands:

/about: Information about the bot.
/ai: Query the AI for a response.
/whereami: Get the GPS coordinates of the current node.
/emergency /911: Trigger an emergency alert (SMS/Email).
/test: A simple test message.  Takes the senders shortcode name and generates a response to facilitate easier range testing on channels.
/help: List available commands.
/motd: Display the message of the day.

****/commands are currently CASE SENSITIVE - this will be improved later.****

These commands will respond on any channel the node attached to the machine is a member of - including LongFast.  The /commands feature is not only there to 
enable functionality, but also to prevent spamming by the AI.  Future versions MAY allow for free communication on specific channels - but in an effort to prevent overwhelming the meshtastic network and AI generated SPAM - these features will currently remain limited.  -  

We can only hope people use this technology for good - it is not my intention for this to be used for evil...  but there is always that chance.

Custom commands can be defined in the commands_config.json file.

Example of Custom Commands Configuration:

_____________________________________________________________________________________________________________________________________________________________

{
  "commands": [
    {
      "command": "/ping",
      "response": "Pong!"
    },
    {
      "command": "/weather",
      "response": "Currently, local weather is unknown. (This is a placeholder.)"
    }
  ]
}

_____________________________________________________________________________________________________________________________________________________________

MOTD Customization: The message of the day (MOTD) can be changed by modifying the motd.json file.

_____________________________________________________________________________________________________________________________________________________________


Emergency Alerts (untested at this time)

If enabled in config.json, Meshtastic-AI can send SMS and Email alerts for emergencies via Twilio and SMTP. Ensure that the necessary credentials and recipient information are provided in the config file.

***** FIRST DISCLAIMER *****

The machine running this script MUST have an internet connection to send SMS or Email Emergency alerts.  This feature currently remains UNTESTED - and should not be depended upon in a true emergency situation at this time!  If your goal is a totally offline, off grid implementation of LMStudio - please be aware that offline emergency alerts ARE NOT AVAILABLE AT THIS TIME.  There will be a way to turn off the feature entirely in future versions.

_____________________________________________________________________________________________________________________________________________________________

Offline / Off-Grid LMStudio Integration

For the offline AI functionality to work, LMStudio must be running and its web server active. The address of the server can be configured in the config.json file under lmstudio_url. This bot acts as a man-in-the-middle, forwarding the messages to LMStudio, which processes the input and returns the generated responses.

The AI can run any model, and the bot will handle passing and decoding the serial messages on the Meshtastic node, forwarding them to LMStudio, and then sending the AI's response to the sender node or the corresponding channel.

_____________________________________________________________________________________________________________________________________________________________

Flask Web Interface

The bot exposes the following web API:

GET /messages: Returns a JSON feed of recent messages.
GET /dashboard: Displays a simple HTML dashboard with recent messages.
POST /send: Sends a message to a specified node in the mesh.

_____________________________________________________________________________________________________________________________________________________________

Running the Bot

To run the bot:
Navigate using terminal or CMD to your installation directory & run the following:
_____________________________________________________________________________________________________________________________________________________________


python meshtastic_ai.py

_____________________________________________________________________________________________________________________________________________________________

This will start the bot and expose the Flask web API on http://localhost:5000.

_____________________________________________________________________________________________________________________________________________________________

Features Coming Soon:

- OpenAI API Integration - actively in development.
- Ollama API Options (though LMStudio is far superior).
- Discord Webhook Publishing.
- Further Web Dashboard Development.
- Emergency Alert Field Testing and improvements
- Further configuration options TBD.

_____________________________________________________________________________________________________________________________________________________________

Installation Guide

Prerequisites

Before starting the installation, make sure you have the following:

- A Meshtastic Node (such as a Heltec V3 (currently only tested model) or similar).
- A computer running Python 3.13 or higher (Windows, Linux, or Mac should work).
- LMStudio should be running with its web server active. Your config.json should point to the LMStudio instance's address.
- Twilio and SMTP credentials (optional, if you want emergency SMS and email alerts).
- The USB Serial drivers for your node installed and it's COM port identified.  Currently the script works specifically on COM3 - but this setting will be exposed in config.json very soon.  If you need a different COM port - you can edit it easily in the meshtastic_ai.py script (as well as any other settings not currently exposed in the config.json) 

_____________________________________________________________________________________________________________________________________________________________


Step 1: Install Python 3.13+

Ensure that Python 3.13 or higher is installed on your system.

- Windows: Download from python.org.

- (untested) Linux: Use your package manager (e.g., sudo apt install python3 on Ubuntu).

- (untested) Mac: Use Homebrew (brew install python3) or download from python.org.

After installing Python, verify the installation by running the following in your terminal or command prompt:

_____________________________________________________________________________________________________________________________________________________________


python --version

_____________________________________________________________________________________________________________________________________________________________


Clone the Meshtastic-AI repository to your local machine. If you don't have Git installed, you can download it from git-scm.com.

git clone https://github.com/mr-tbot/meshtastic-ai.git
cd meshtastic-ai

_____________________________________________________________________________________________________________________________________________________________


Step 3: Install Dependencies

Navigate to the project folder and install the required dependencies. This is done using Python’s package manager, pip.

Open your terminal (or command prompt).
Run the following command inside the meshtastic-ai directory:

_____________________________________________________________________________________________________________________________________________________________


pip install -r requirements.txt

_____________________________________________________________________________________________________________________________________________________________


This will install all the necessary Python libraries for the bot to function, including Meshtastic, Flask, requests, and others.

_____________________________________________________________________________________________________________________________________________________________


Step 4: Configure config.json

The config.json file contains settings for the AI model, chunking parameters, and emergency alerts. Modify this file to match your setup:

Open the config.json file in a text editor.

Configure the following settings:

lmstudio_url: Set the URL of the LMStudio API server. Example:

"lmstudio_url": "http://localhost:1234/v1/chat/completions"

- chunk_size, max_ai_chunks, chunk_delay: Adjust these parameters for optimal chunking based on your network conditions.

- If you're enabling Twilio or SMTP for emergency alerts, ensure you provide the correct credentials.

- Set the local_location_string and ai_node_name to reflect your desired node settings.



force_node_num Explanation:

"force_node_num" is an optional setting in the config.json file.

Purpose: This option was implemented in case your Meshtastic node is having trouble sending or receiving messages. Sometimes, nodes might not properly identify themselves on the mesh network, causing communication issues.

How to Use:

If you're facing communication problems, you can set a specific node number for your node to ensure it is properly identified.

To get your node number, run the following command in your terminal or command prompt:

_____________________________________________________________________________________________________________________________________________________________


meshtastic --info

_____________________________________________________________________________________________________________________________________________________________


This will display information about your connected Meshtastic device, including its 9 digit node ID number.

Example: If the command gives you a node number like 123456789, you can enter it like this in config.json:

_____________________________________________________________________________________________________________________________________________________________


"force_node_num": 123456789

_____________________________________________________________________________________________________________________________________________________________


When to Use: Only modify this setting if you're experiencing issues with your node not being able to send or receive messages correctly. It helps ensure that your node is always using the correct node ID.


_____________________________________________________________________________________________________________________________________________________________



Step 5: Configure motd.json

To customize the Message of the Day (MOTD), edit the motd.json file.

_____________________________________________________________________________________________________________________________________________________________



Step 6: Set the Meshtastic Node to "Client_Mute" Mode

To make sure the node is not sending unnecessary beacons and using the duty cycle efficiently:

Put the Meshtastic node into "Client_Mute" mode. This mode allows your node to respond more efficiently by not broadcasting extra messages.
You can typically set this in the Meshtastic app or via the node's configuration commands.
Note: This step is especially important for areas where the duty cycle is limited, like in Europe, where the duty cycle is restricted to 10%.

_____________________________________________________________________________________________________________________________________________________________


Step 7: Run LMStudio - OpenAI and ollama coming soon!

Ensure that LMStudio is running on your machine and that its web server is active. The bot will rely on this server to generate AI responses. Set the lmstudio_url in config.json to the correct address of your running LMStudio instance.

_____________________________________________________________________________________________________________________________________________________________


Step 8: Run the Bot
With everything configured, it’s time to run the bot. In your terminal, execute the following in your terminal from the installation directory:

_____________________________________________________________________________________________________________________________________________________________


python meshtastic_ai.py

_____________________________________________________________________________________________________________________________________________________________


The bot will start and run in the background, listening for messages and commands on your connected Meshtastic node.
The Flask web interface will be available at http://localhost:5000. You can use it to view recent messages and interact with the bot via HTTP.

_____________________________________________________________________________________________________________________________________________________________


MOTD Customization: The message of the day (MOTD) can be changed by modifying the motd.json file.



Early Alpha: This is an early alpha release. The SMS and SMTP features remain UNTESTED and should not be relied upon for mission-critical implementations until the code matures further.

Developer Background: Hi- I'm TBOT.  I am not a professional coder but an avid computer nerd. This project was built using tools available to bridge gaps, with most of the code generated using OpenAI's GPT-4 1o model and Llama-based LLMs. While the code works well and was created from scratch in under 12 hours, it might benefit from a professional review. My ability to test and debug is limited, so feedback from experienced developers is encouraged. So far, the chat routing and reply system has been stable and effective.


