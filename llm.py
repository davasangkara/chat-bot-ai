# llm.py
from __future__ import annotations
import os, time
from typing import List, Dict

class LLMError(Exception):
    pass

def _is_quota_err(e: Exception) -> bool:
    s = str(e).lower()
    return ("429" in s) or ("quota" in s) or ("rate limit" in s)

def _make_model(genai, model_name: str, system_instruction: str, generation_config: dict):
    # Kompatibel lintas-versi (posisi dulu, lalu keyword)
    try:
        return genai.GenerativeModel(
            model_name,
            system_instruction=system_instruction or None,
            generation_config=generation_config,
        )
    except TypeError:
        return genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_instruction or None,
            generation_config=generation_config,
        )

def chat(messages: List[Dict], temperature: float = 0.6, top_p: float = 0.9) -> str:
    """
    Gemini only. Baca ENV saat runtime + retry & fallback bila quota/429.
    """
    provider = os.getenv("PROVIDER", "gemini").lower()
    if provider != "gemini":
        raise LLMError("Set PROVIDER=gemini pada .env")

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    primary_model = (os.getenv("GEMINI_MODEL", "gemini-1.5-flash") or "gemini-1.5-flash").strip()

    # daftar fallback dari ENV (dipisah koma)
    fb_raw = os.getenv("GEMINI_FALLBACK_MODELS", "gemini-1.5-flash-8b,gemini-1.5-pro")
    fallback_models = [m.strip() for m in fb_raw.split(",") if m.strip()]

    # retry settings
    max_retries = int(os.getenv("RATE_LIMIT_MAX_RETRIES", "2"))
    base_delay  = float(os.getenv("RATE_LIMIT_BASE_DELAY", "3.0"))  # detik

    if not api_key:
        raise LLMError("GEMINI_API_KEY tidak ditemukan. Set di .env")
    if not messages:
        raise LLMError("Pesan kosong")

    # Siapkan instruction & history
    system_instruction = ""
    converted_history = []

    last_msg = messages[-1]
    last_input = last_msg.get("content", "") or " "
    for m in messages[:-1]:
        role = m.get("role")
        content = (m.get("content") or "").strip()
        if not content:
            continue
        if role == "system":
            system_instruction += ("" if not system_instruction else "\n") + content
        else:
            g_role = "user" if role == "user" else "model"
            converted_history.append({"role": g_role, "parts": [content]})

    try:
        import google.generativeai as genai
    except Exception:
        raise LLMError("Pustaka google-generativeai belum terpasang. Jalankan: pip install google-generativeai")

    genai.configure(api_key=api_key)
    generation_config = {"temperature": float(temperature), "top_p": float(top_p)}

    # coba dengan primary + daftar fallback
    model_chain = [primary_model] + [m for m in fallback_models if m != primary_model]

    last_err = None
    for model_name in model_chain:
        try:
            model_obj = _make_model(genai, model_name, system_instruction, generation_config)
            chat_sess = model_obj.start_chat(history=converted_history)

            # kirim dengan retry saat 429/kuota
            for attempt in range(max_retries + 1):
                try:
                    resp = chat_sess.send_message(last_input)
                    if getattr(resp, "text", None):
                        return resp.text.strip()
                    if getattr(resp, "candidates", None):
                        for c in resp.candidates:
                            if getattr(c, "content", None) and c.content.parts:
                                return "".join(getattr(p, "text", "") for p in c.content.parts).strip()
                    raise LLMError("Tidak ada teks balasan dari Gemini.")
                except Exception as e:
                    last_err = e
                    if _is_quota_err(e) and attempt < max_retries:
                        # backoff (mis. 3s, lalu 6s)
                        delay = base_delay * (2 ** attempt)
                        time.sleep(delay)
                        continue
                    else:
                        raise
        except Exception as e:
            last_err = e
            # Jika model tidak tersedia/kuota habis, lanjut coba model berikutnya
            continue

    # Kalau semua gagal:
    if last_err:
        s = str(last_err)
        if _is_quota_err(last_err):
            raise LLMError("Kuota Gemini untuk model saat ini habis. Coba beberapa menit lagi, atau ganti model/fallback.")
        raise LLMError(f"Gemini error: {s}")
    raise LLMError("Tidak bisa menghubungi Gemini saat ini.")
