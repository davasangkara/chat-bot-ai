# llm.py
from __future__ import annotations
import os
from typing import List, Dict

class LLMError(Exception):
    pass

def chat(messages: List[Dict], temperature: float = 0.6, top_p: float = 0.9) -> str:
    """
    messages: [{role: system|user|assistant, content: str}] -> str reply
    Baca ENV saat runtime & kompatibel berbagai versi google-generativeai.
    """
    provider = os.getenv("PROVIDER", "gemini").lower()
    if provider != "gemini":
        raise LLMError("Set PROVIDER=gemini pada .env")

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()

    if not api_key:
        raise LLMError("GEMINI_API_KEY tidak ditemukan. Set di .env")
    if not messages:
        raise LLMError("Pesan kosong")

    # --- Siapkan system_instruction & history ---
    system_instruction = ""
    converted_history = []

    # Pisahkan pesan terakhir sebagai input
    last_msg = messages[-1]
    last_input = last_msg.get("content", "")
    history_iter = messages[:-1]

    for m in history_iter:
        role = m.get("role")
        content = (m.get("content") or "").strip()
        if not content:
            continue
        if role == "system":
            system_instruction += ("" if not system_instruction else "\n") + content
        else:
            # Gemini history format: role in {"user","model"}
            g_role = "user" if role == "user" else "model"
            converted_history.append({"role": g_role, "parts": [content]})

    try:
        import google.generativeai as genai
    except Exception:
        raise LLMError("Pustaka google-generativeai belum terpasang. Jalankan: pip install google-generativeai")

    try:
        genai.configure(api_key=api_key)

        generation_config = {
            "temperature": float(temperature),
            "top_p": float(top_p),
        }

        # --- Buat model secara KOMPATIBEL lintas versi ---
        # 1) Argumen POSISI (umumnya diterima semua versi)
        try:
            model_obj = genai.GenerativeModel(
                model_name,  # <- posisi, bukan keyword 'model'
                system_instruction=system_instruction or None,
                generation_config=generation_config,
            )
        except TypeError:
            # 2) Versi lama: pakai keyword 'model_name'
            model_obj = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=system_instruction or None,
                generation_config=generation_config,
            )

        # Fallback bila model '2.0' belum tersedia di akun/region
        try:
            chat_sess = model_obj.start_chat(history=converted_history)
        except Exception as e:
            if "not found" in str(e).lower() or "unsupported" in str(e).lower():
                # Coba fallback ke model stabil
                model_name_fallback = "gemini-1.5-flash"
                try:
                    model_obj = genai.GenerativeModel(
                        model_name_fallback,
                        system_instruction=system_instruction or None,
                        generation_config=generation_config,
                    )
                except TypeError:
                    model_obj = genai.GenerativeModel(
                        model_name=model_name_fallback,
                        system_instruction=system_instruction or None,
                        generation_config=generation_config,
                    )
                chat_sess = model_obj.start_chat(history=converted_history)
            else:
                raise

        # --- Kirim pesan terakhir ---
        resp = chat_sess.send_message(last_input or " ")

        # --- Ambil teks balasan ---
        if getattr(resp, "text", None):
            return resp.text.strip()

        if getattr(resp, "candidates", None):
            for c in resp.candidates:
                if getattr(c, "content", None) and c.content.parts:
                    return "".join(getattr(p, "text", "") for p in c.content.parts).strip()

        raise LLMError("Tidak ada teks balasan dari Gemini.")
    except LLMError:
        raise
    except Exception as e:
        raise LLMError(f"Gemini error: {e}")
