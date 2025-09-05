import toml
from openai import OpenAI

# Load configuration from TOML file
def load_config():
    try:
        with open('config.toml', 'r') as f:
            config = toml.load(f)
            return config
    except FileNotFoundError:
        print("Error: config.toml file not found.")
        return None
    except Exception as e:
        print(f"Error loading config: {e}")
        return None

# Load config and initialize client
config = load_config()
if config and 'openai' in config and 'api_key' in config['openai']:
    client = OpenAI(
        api_key=config['openai']['api_key'],
    )

    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a virtual assistant named jarvis skilled in general tasks like Alexa and Google Cloud"},
            {"role": "user", "content": "what is coding"}
        ]
    )

    print(completion.choices[0].message.content)
else:
    print("Failed to load OpenAI API key from config.toml")