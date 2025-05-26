import sys
import os

print("--- Python Environment Check ---")
print(f"Python Executable: {sys.executable}")
print(f"Python Version: {sys.version.split()[0]}")
print(f"Current Working Directory: {os.getcwd()}")
print("\n--- Checking Core Dependencies ---")

try:
    import streamlit
    print(f"Streamlit: PASSED (Version: {streamlit.__version__}, Path: {streamlit.__path__})")
except ImportError as e:
    print(f"Streamlit: FAILED (Error: {e})")
    print("  Please ensure Streamlit is installed in your environment (e.g., 'pip install streamlit')")

try:
    import groq
    print(f"Groq: PASSED (Version: {groq.__version__}, Path: {groq.__path__})")
except ImportError as e:
    print(f"Groq: FAILED (Error: {e})")
    print("  Please ensure the Groq Python client is installed (e.g., 'pip install groq')")

print("\n--- Checking Groq API Key ---")
api_key = os.environ.get("GROQ_API_KEY")
if api_key:
    print(f"GROQ_API_KEY: FOUND (Value: '{api_key[:5]}...{api_key[-5:]}' (obfuscated))")
else:
    print("GROQ_API_KEY: NOT FOUND")
    print("  Please ensure the GROQ_API_KEY environment variable is set.")
    print("  The main application will show a warning if this key is not set at runtime.")

print("\n--- Check Complete ---")
print("If all core dependencies show 'PASSED' and your GROQ_API_KEY is 'FOUND', your basic environment should be okay.")
print("If you see 'FAILED' for any dependency, please install/reinstall it in your current Python environment.")
print(f"To run this check, use: python ipc_voice_app/check_env.py (ensure '{os.path.basename(sys.executable)}' is the correct interpreter from your activated virtual environment).")
