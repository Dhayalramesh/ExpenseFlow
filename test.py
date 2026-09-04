import sys
print(f"✅ Python version: {sys.version}")

try:
    import pytesseract
    print("✅ pytesseract imported")
except ImportError as e:
    print(f"❌ pytesseract: {e}")

try:
    from groq import Groq
    print("✅ groq imported")
except ImportError as e:
    print(f"❌ groq: {e}")

try:
    from sqlalchemy import create_engine
    print("✅ sqlalchemy imported")
except ImportError as e:
    print(f"❌ sqlalchemy: {e}")

try:
    import streamlit as st
    print("✅ streamlit imported")
except ImportError as e:
    print(f"❌ streamlit: {e}")

try:
    from backend.database import get_db
    print("✅ backend.database imported")
except ImportError as e:
    print(f"❌ backend.database: {e}")