# api/index.py
from dotenv import load_dotenv
load_dotenv()  # aman buat lokal; di Vercel pakai env dashboard

# penting: ekspor nama variabel 'app'
from app import app  # Flask instance bernama 'app'
