# app.py
import os

from dotenv import load_dotenv
load_dotenv()  # ← load .env dulu

from flask import Flask, request, jsonify, render_template
from persona import build_system_prompt, TARGET_CONTACT
from memory import get_history, append_message, reset_history
from llm import chat, LLMError


app = Flask(__name__)

@app.get("/")
def home():
    return render_template("index.html", target=TARGET_CONTACT.capitalize())

@app.post("/api/chat")
def api_chat():
    payload = request.get_json(force=True, silent=True) or {}
    user_msg = (payload.get("message") or "").strip()
    contact = (payload.get("contact") or TARGET_CONTACT).strip().lower() or TARGET_CONTACT

    if not user_msg:
        return jsonify({"error": "Pesan kosong"}), 400

    system_msg = {"role": "system", "content": build_system_prompt()}
    history = get_history(contact)
    messages = [system_msg] + history + [{"role": "user", "content": user_msg}]

    try:
        reply = chat(messages)
    except LLMError as e:
        return jsonify({"error": str(e)}), 500

    append_message(contact, "user", user_msg)
    append_message(contact, "assistant", reply)

    return jsonify({"reply": reply})

@app.post("/api/reset")
def api_reset():
    payload = request.get_json(force=True, silent=True) or {}
    contact = (payload.get("contact") or TARGET_CONTACT).strip().lower() or TARGET_CONTACT
    reset_history(contact)
    return jsonify({"ok": True})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5050))
    app.run(host="127.0.0.1", port=port)
