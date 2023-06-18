from flask import Flask, render_template, request, session, jsonify
from typing import Dict
from dotenv import load_dotenv
from .chat.chat import ChatSession
import os

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("CHAT_APP_SECRET_KEY")

chat_sessions: Dict[str, ChatSession] = {}

@app.route("/")
def index():
    chat_session = _get_user_session()
    return render_template("chat.html", conversation=chat_session.get_messages())

@app.route('/chat', methods=['POST'])
def chat():
    message: str = request.json['message']
    chat_session = _get_user_session()
    chatgpt_message = chat_session.get_chatgpt_response(message)
    return jsonify({"message": chatgpt_message})

def _get_user_session() -> ChatSession:
    chat_session_id = session.get("chat_session_id")
    if not chat_session_id or chat_session_id not in chat_sessions:
        chat_session = ChatSession()
        chat_sessions[chat_session.session_id] = chat_session
        session["chat_session_id"] = chat_session.session_id
    else:
        chat_session = chat_sessions[chat_session_id]
    return chat_session