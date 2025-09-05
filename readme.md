# Jarvis AI Assistant 🤖

![Jarvis Logo](https://i.imgur.com/JZkfLXi.png) *(optional: add your own logo image)*

A voice-controlled AI assistant inspired by Iron Man's Jarvis, powered by GPT-4 and featuring advanced capabilities including system control, web automation, emotion detection, and natural language processing.

## Features ✨

### Core Functionality
- **Voice Recognition**:
  - Wake word detection ("Hey Jarvis")
  - Voice input and output (ElevenLabs, gTTS, pyttsx3 fallback)
  - Language detection for responses
  - Conversational memory/history
  - GPT-3.5/4 powered AI chat and Q&A

- **Memory and Learning**:
  - Stores user activity in JSON format
  - Tracks application usage patterns
  - Maintains user preferences
  - Persistent storage of interactions

- **Emotion Detection**:
  - Real-time facial emotion recognition using webcam
  - Tracks user's emotional state over time
  - Adapts responses based on detected emotions
  - Stores emotion history for analysis

- **Screen Activity Monitoring**:
  - Tracks active windows and applications
  - Uses OCR to extract text from screen
  - Analyzes user activity patterns
  - Tracks time spent on different applications

### Productivity Tools
- **Reminder System**:
  - Set reminders with natural language ("remind me to...")
  - Supports time-based and recurring reminders
  - Visual and audio notifications
  - Persistent storage of reminders

- **Application Control**:
  - Open applications via voice commands
  - Custom app aliases for common applications
  - System-wide hotkeys for quick access
  - Application usage statistics

- **Web Integration**:
  - Web search with Google
  - YouTube video search and playback
  - Wikipedia lookups
  - Weather information

### User Interface
- **System Tray Integration**:
  - Runs in background with system tray icon
  - Quick access to common functions
  - Notification center for reminders and alerts
  - Easy access to settings and preferences

- **Daily Summaries**:
  - Generates daily activity reports
  - Tracks most used applications
  - Analyzes emotional patterns
  - Provides insights and suggestions

- **Personalized Experience**:
  - Time-based greetings
  - Customizable voice and responses
  - Learning from user preferences
  - Context-aware suggestions

## Installation 🛠️

### Prerequisites
- Python 3.8+
- OpenAI API key with GPT-4 access
- ElevenLabs API key (for premium voice) *(optional)*

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/jarvis-ai-assistant.git
   cd jarvis-ai-assistant
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create `config.toml` file:
   ```toml
   [openai]
   api_key = "your_openai_api_key"
   model = "gpt-4"
   max_tokens = 150
   temperature = 0.7

   [elevenlabs]
   api_key = "your_elevenlabs_api_key"
   voice_id = "21m00Tcm4TlvDq8ikWAM"  # Indian accent

   [wolframalpha]
   app_id = "your_wolfram_app_id"

   [settings]
   max_history = 10
   ```

## Usage 🎤

1. Start Jarvis:
   ```bash
   python jarvis.py
   ```

2. Wake Jarvis by saying "Jarvis" or give direct commands

3. Try these commands:
   - "Jarvis, open YouTube"
   - "Jarvis, set a reminder for 5 minutes to check the oven"
   - "Jarvis, tell me a joke"
   - "Jarvis, what's the capital of France?"
   - "Jarvis, increase brightness by 20%"

## Voice Configuration 🎙️

The assistant supports multiple voice options:

1. **ElevenLabs** (Premium, recommended):
   - Indian accent included by default
   - Change `voice_id` in config for different voices

2. **gTTS** (Free Google Text-to-Speech):
   - Automatic fallback if ElevenLabs fails

3. **pyttsx3** (Local):
   - Ultimate fallback option

## Troubleshooting ⚠️

**Common Issues:**

1. **Microphone not working**:
   - Check your system audio settings
   - Ensure `pyaudio` is properly installed

2. **API errors**:
   - Verify your API keys in `config.toml`
   - Check your OpenAI account for GPT-4 access

3. **Command not recognized**:
   - Speak clearly and naturally
   - Check the available commands list

## Contributing 🤝

Contributions are welcome! Here's how:

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License 📄

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments 🙏

- OpenAI for the GPT-4 API
- ElevenLabs for voice synthesis
- All open-source libraries used in this project

---

**Note:** This project is for educational purposes only. Not affiliated with Marvel or Disney.
```

This README includes:

1. **Visual elements** (emoji, optional logo)
2. **Comprehensive feature list**
3. **Clear installation instructions**
4. **Usage examples**
5. **Configuration details**
6. **Troubleshooting guide**
7. **Contribution guidelines**
8. **License information**
9. **Acknowledgments**

You can customize it further by:
- Adding screenshots/videos
- Including a demo GIF
- Adding system requirements
- Expanding the command list
- Adding roadmap/future features
