import os
import openai
import sqlite3
import speech_recognition as sr
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from googletrans import Translator

# Load API key from .env
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__, template_folder='templates')

# In-memory log of chat messages
chat_log = []

# Database setup
conn = sqlite3.connect("chat_history.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS chats (id INTEGER PRIMARY KEY, user_message TEXT, ai_response TEXT)")
conn.commit()

@app.route('/')
def home():
    return render_template('index.html')

@app.route("/chat", methods=["POST"])
def chat():
    """Handles text-based chat input."""
    data = request.json
    user_message = data.get("message", "")
    language = data.get("language", "en")  # Default to English

    try:
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": user_message}]
        )
        ai_response = response.choices[0].message.content

        # Translate response if needed
        translator = Translator()
        translated_response = translator.translate(ai_response, dest=language).text

        # Save to database
        cursor.execute("INSERT INTO chats (user_message, ai_response) VALUES (?, ?)", (user_message, translated_response))
        conn.commit()

        # Add to in-memory log
        chat_log.append({"user": user_message, "ai": translated_response})

        return jsonify({"response": f"<strong>AI Response:</strong> {translated_response}"})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/voice", methods=["POST"])
def voice_chat():
    """Handles voice input and converts it to text."""
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        audio = recognizer.listen(source)

    try:
        user_message = recognizer.recognize_google(audio)
        print(f"Recognized: {user_message}")

        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": user_message}]
        )
        ai_response = response.choices[0].message.content

        # Add to in-memory log
        chat_log.append({"user": user_message, "ai": ai_response})

        return jsonify({"response": ai_response})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/history", methods=["GET"])
def chat_history():
    """Fetch and display chat history."""
    cursor.execute("SELECT user_message, ai_response FROM chats ORDER BY id DESC LIMIT 10")
    history = cursor.fetchall()
    return jsonify({"history": history})


@app.route("/log", methods=["GET"])
def get_log():
    """Return the in-memory chat log."""
    return jsonify({"log": chat_log})


if __name__ == "__main__":
    app.run(debug=True)
