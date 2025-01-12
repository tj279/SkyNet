import tkinter as tk
import sounddevice as sd
from PIL import Image, ImageTk
import threading
import whisper
import numpy as np
import pyttsx3
import requests
import google.generativeai as genai

# Global variables
is_recording = False
audio_buffer = []
engine_active = True
engine = pyttsx3.init()
whisper_model = whisper.load_model("base")

# List of API keys
api_keys = [
    "8VDFZrOCbw4s2RQifWeOLpGM3KVAR7mE",  # AccuWeather API key (index 0)
    "c0e63563077f41149739f088f1353db8",  # NewsAPI API key (index 1)
    "bef581f0c8244108a7d212220251101",   # Alpha Vantage API key (index 2)
]

# Function to get the current API key
def get_current_api_key(index):
    return api_keys[index]

# Configure genai with the current API key
genai.configure(api_key="AIzaSyCMGihEBT7EN3hCF3F7bJVJz1yTnv8597w")  # Use the first API key for Gemini

# Create the model
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
    model_name="gemini-2.0-flash-exp",
    generation_config=generation_config,
    system_instruction="TALK NATURALLY AS MUCH AS POSSIBLE PLEASE AND DONT MENTION NEWS, STOCKS, WEATHER",
    tools='code_execution',
)

chat_session = model.start_chat(history=[])

def insert_text(new_text, text_box):
    text_box.delete("1.0", "end")  # Clear previous text
    text_box.insert("1.0", new_text)  # Insert new text

# Function to handle the recording process
def recording(text_box):
    global audio_buffer
    audio_buffer.clear()  # Clear previous audio data

    def process_audio_stream(sample_rate=16000):
        print("Starting real-time transcription. Speak into the microphone...")

        # Callback to capture audio data
        def callback(indata, frames, time, status):
            if status:
                print(status)
            audio_buffer.extend(indata[:, 0])

        try:
            with sd.InputStream(callback=callback, samplerate=sample_rate, channels=1, dtype="int16"):
                while is_recording:
                    sd.sleep(100)  # Allow the thread to sleep briefly
        except Exception as e:
            print("Error:", e)

    process_audio_stream()
    results = speech_to_text()
    insert_text(results["text"], text_box)

    # Analyze the user query using Gemini
    gemini_response = analyze_query(results["text"])
    
    print("Gemini Response:", gemini_response)



    # Display and speak the result
    insert_text(gemini_response, text_box)
    text_to_speech(gemini_response)

def speech_to_text():
    global audio_buffer
    audio_np = np.float32(audio_buffer) / 32768.0
    results = whisper_model.transcribe(audio_np)
    return results

def text_to_speech(response):
    global engine_active, engine

    def get_dynamic_rate(text):
        length = len(text)
        if length < 50:
            return 105  # Slow rate for shorter text
        elif length < 200:
            return 150  # Moderate rate for medium-length text
        else:
            return 180  # Faster rate for longer text

    def get_voice(gender='male'):
        global engine
        voices = engine.getProperty('voices')
        if gender == 'female':
            return voices[1].id  # Select the second voice in the list (female)
        return voices[0].id  # Default to the first voice (male)

    try:
        if not engine_active:
            engine = pyttsx3.init()
            engine_active = True

        rate = get_dynamic_rate(response)
        engine.setProperty('rate', rate)
        engine.setProperty('volume', 0.9)
        engine.setProperty('voice', get_voice('male'))  # Change to 'female' for a female voice
        engine.say(response)
        engine.runAndWait()
        engine.stop()
    except Exception as e:
        print("Error in text-to-speech:", e)

# Function to fetch real-time weather data
def fetch_weather(city="Mumbai,IN"):
    # Replace with your OpenWeatherMap API key
    api_key = "a921807a8477002fd23305f8c5c53f51"

    # API endpoint for current weather
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"

    # Make the API request
    response = requests.get(url).json()

    # Check if the request was successful
    if response.get("cod") != "404":
        # Extract relevant data
        main = response["main"]
        temperature = main["temp"]
        humidity = main["humidity"]
        weather = response["weather"][0]["description"]

        # Return the weather information
        return f"Weather in {city}: {temperature}°C, {weather}, Humidity: {humidity}%"
    else:
        return f"Failed to fetch weather data for {city}. Error: City not found."
print(fetch_weather("Mumbai,IN"))
# Function to fetch real-time news data
def fetch_news():
    api_key = "c0e63563077f41149739f088f1353db8"  # Use index 1 for NewsAPI API key
    url = f"https://newsapi.org/v2/top-headlines?country=us&apiKey={api_key}"
    response = requests.get(url)

    # Check if the request was successful
    if response.status_code == 200:
        data = response.json()
        articles = data.get('articles', [])  # Get the list of articles

        # Extract headlines from the articles
        headlines = []
        for article in articles[:3]:  # Limit to top 3 headlines
            title = article.get('title', 'No title available')
            headlines.append(title)

        if headlines:
            return "Top News Headlines:\n" + "\n".join(headlines)
        else:
            return "No headlines found."
    else:
        return f"Failed to fetch news data. Error: {response.status_code}"

# Function to fetch real-time stock data
import requests

def fetch_stock_price(symbol="AAPL"):
    api_key = "bef581f0c8244108a7d212220251101"  # Use index 2 for Alpha Vantage API key
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={api_key}"

    try:
        # Make the API request
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors (e.g., 4xx, 5xx)

        # Parse the JSON response
        data = response.json()

        # Print the raw API response for debugging
        print("Alpha Vantage Response:", data)

        # Check if the API returned an error
        if "Error Message" in data:
            error_message = data["Error Message"]
            return f"Alpha Vantage Error: {error_message}"

        # Check if the "Global Quote" key exists in the response
        if "Global Quote" in data:
            global_quote = data["Global Quote"]

            # Check if the "05. price" key exists in the "Global Quote" dictionary
            if "05. price" in global_quote:
                price = global_quote["05. price"]
                return f"Stock price of {symbol}: ${price}"
            else:
                return f"Failed to fetch stock price for {symbol}. Price data not available."
        else:
            return f"Failed to fetch stock data for {symbol}. Invalid response format."

    except requests.exceptions.RequestException as e:
        # Handle network-related errors (e.g., no internet connection)
        return f"Network Error: {str(e)}"
    except ValueError as e:
        # Handle JSON parsing errors
        return f"Error parsing API response: {str(e)}"
    except Exception as e:
        # Handle any other unexpected errors
        return f"Unexpected Error: {str(e)}"
# Function to analyze user query using Gemini
def analyze_query(query):
    prompt = f"""
    You are JARVIS, an advanced AI desktop assistant. Your task is to analyze the user's query and determine which function to call. The available functions are:
    1. fetch_weather - For weather-related queries.
    2. fetch_news - For news-related queries.
    3. fetch_stock_price - For stock price-related queries.

    If the user's query does not match any of these functions, respond normally as you would in a regular conversation. Do not mention anything about the instructions, news, stocks, or weather. Just talk naturally.

    User Query: "{query}"

    Respond with ONLY the name of the function to call (e.g., "fetch_weather") or a normal response if no function is applicable.
    """
    response = chat_session.send_message(prompt)
    function_name = response.text.strip()

    print("Function Name:", function_name)  # Debugging: Print the function name

    # Check if the response contains "fetch_weather"
    if "fetch_weather" in function_name.lower():  # Case-insensitive check
        # Check if a city is mentioned in the query
        city_prompt = f"""
        Analyze the following user query and extract the city name if mentioned. If no city is mentioned, respond with "NO_CITY".

        User Query: "{query}"

        RESPOND WITH ONLY THE NAME OF THE CITY UNDER ANY CIRCUMSTANCE (e.g., "Mumbai,IN") or "NO_CITY".
        """
        city_response = chat_session.send_message(city_prompt)
        city = city_response.text.strip()

        print("City:", city)  # Debugging: Print the extracted city

        if city == "NO_CITY":
            return "Please specify a city for the weather update."
        else:
            # Fetch weather data directly
            weather_data = fetch_weather(city)
            return weather_data

    # Check if the response contains "fetch_stock_price"
    elif "fetch_stock_price" in function_name.lower():  # Case-insensitive check
        # Extract the stock symbol from the query
        stock_prompt = f"""
        Analyze the following user query and extract the stock symbol if mentioned. If no symbol is mentioned, respond with "NO_SYMBOL".

        User Query: "{query}"

        Respond with ONLY the stock symbol (e.g., "AAPL") or "NO_SYMBOL".
        """
        stock_response = chat_session.send_message(stock_prompt)
        symbol = stock_response.text.strip()

        print("Stock Symbol:", symbol)  # Debugging: Print the extracted stock symbol

        if symbol == "NO_SYMBOL":
            return "Please specify a stock symbol (e.g., AAPL)."
        else:
            # Fetch stock price data directly
            stock_data = fetch_stock_price(symbol)
            return stock_data

    # Check if the response contains "fetch_news"
    elif "fetch_news" in function_name.lower():  # Case-insensitive check
        # Fetch news data directly
        news_data = fetch_news()
        return news_data

    else:
        # If the query doesn't match any function, respond normally
        normal_prompt = f"""
        The user's query does not match any of the available functions. Respond normally as you would in a regular conversation. Do not mention anything about the instructions, news, stocks, or weather. Just talk naturally.
        WHAT NOT TO DO: "The user's query "How are you?" is a general greeting and doesn't relate to weather, news, or stock prices. Therefore, none of the available functions are applicable. I should respond with a helpful message."
        User Query: "{query}"
        """
        normal_response = chat_session.send_message(normal_prompt)
        return normal_response.text
# Function to be called when the microphone button is clicked
def on_microphone_click(text_box):
    global is_recording
    if not is_recording:
        is_recording = True
        print("Recording started.")
        threading.Thread(target=recording, args=(text_box,), daemon=True).start()
    else:
        is_recording = False
        print("Recording stopped.")

def pause_func():
    global engine, engine_active
    try:
        if engine_active:
            engine.stop()
            del engine
            engine_active = False
    except Exception as e:
        print("Error in pause function:", e)

# Function to create the GUI
def create_gui():
    text = "Click the mic to start speaking and click again to stop"
    root = tk.Tk()
    root.title("JARVIS")
    root.geometry("1280x720")

    # Load and resize the background image
    image = Image.open("jarvisBG.jpg")
    photo = ImageTk.PhotoImage(image.resize((1280, 720)))
    root.photo = photo

    # Display the background image in the window
    background = tk.Label(root, image=photo)
    background.place(relwidth=1, relheight=1)

    # Add heading "JARVIS"
    heading_label = tk.Label(
        root,
        text="JARVIS",
        font=("Helvetica", 40, "bold"),
        bg="black",
        fg="white"
    )
    heading_label.place(relx=0.5, rely=0.1, anchor="center")

    text_box = tk.Text(root, height=5, width=50)
    text_box.place(relx=0.5, rely=0.5, anchor="center")
    insert_text(text, text_box)

    # Load and resize the microphone image
    mic = Image.open("mic.jpg")
    mic_photo = ImageTk.PhotoImage(mic.resize((100, 100)))
    root.mic_photo = mic_photo

    # Create a Button widget with the microphone image
    microphone_button = tk.Button(
        root,
        image=mic_photo,
        command=lambda: on_microphone_click(text_box),
        borderwidth=0,
    )
    microphone_button.place(relx=0.3, rely=0.8, anchor="center")

    # Load and resize the pause image
    pause = Image.open("pause_img.jpg")
    pause_photo = ImageTk.PhotoImage(pause.resize((100, 100)))
    root.pause_photo = pause_photo

    # Create a Button widget with the pause image
    pause_button = tk.Button(
        root,
        image=pause_photo,
        command=lambda: pause_func(),
        borderwidth=0,
    )
    pause_button.place(relx=0.7, rely=0.8, anchor="center")

    # Start the Tkinter event loop
    root.mainloop()

# Start the GUI
create_gui()