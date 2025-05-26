import streamlit as st
import os
import groq
from streamlit_audiorecorder import audiorecorder
import io

# 1. Set Title
st.set_page_config(layout="wide") # Use wide layout for better spacing
st.title("IPC Code Generator from Voice Input")

# General Instructions
st.markdown("""
This app takes your voice input describing an event, transcribes it to text, 
and then suggests potentially relevant Indian Penal Code (IPC) sections. 
Please ensure your Groq API key is set below to enable the app's functionalities.
""")
st.markdown("---")

# API Key Instructions and Check
with st.expander("🔑 Groq API Key Configuration", expanded=True):
    st.markdown("""
    This application uses Groq services for audio transcription and IPC code generation.
    To use this app, you need a Groq API key. 
    
    **Steps to set your API key:**
    1. Obtain an API key from [GroqCloud](https://console.groq.com/keys).
    2. Set it as an environment variable named `GROQ_API_KEY`.
       - For local execution, you can set it in your terminal before running Streamlit (e.g., `export GROQ_API_KEY='your_key_here'`).
       - If deploying on a platform, use their secrets management to set this environment variable.
    
    _**Note:** The API key will not be stored by this application. It is only used for API calls during your current session._
    """)
    groq_api_key = os.environ.get("GROQ_API_KEY")

    if not groq_api_key:
        st.error("🔴 GROQ_API_KEY is not set. The application will not function correctly. Please set this environment variable using the instructions above.")
        client = None  # Ensure client is None if API key is not set
        st.session_state.client_initialized = False
    else:
        st.success("🟢 GROQ_API_KEY is set and detected.")
        if not st.session_state.get("client_initialized", False): # Initialize client only once
            try:
                client = groq.Groq(api_key=groq_api_key)
                st.session_state.client_initialized = True
            except Exception as e:
                st.error(f"🔴 Failed to initialize Groq client: {e}")
                client = None
                st.session_state.client_initialized = False
        else: # Client already initialized, reuse it
            client = groq.Groq(api_key=groq_api_key) if st.session_state.client_initialized else None


# Initialize session state variables if they don't exist
if "transcribed_text_content" not in st.session_state:
    st.session_state.transcribed_text_content = "Transcribed text will appear here..."
if "ipc_codes_content" not in st.session_state:
    st.session_state.ipc_codes_content = "Relevant IPC sections will appear here..."
if "client_initialized" not in st.session_state: # Ensure this is initialized early
    st.session_state.client_initialized = False


# Main app layout with columns for better organization
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Record Crime Description")
    # Modify audiorecorder appearance for better UX
    audio_bytes = audiorecorder(
        "🎤 Start Recording", 
        "■ Stop Recording", 
        pause_prompt="", 
        key="audio_recorder_main"
    )

    if audio_bytes and client and st.session_state.get("client_initialized", False):
        st.audio(audio_bytes, format="audio/wav")
        
        # Clear previous results and show processing state
        st.session_state.transcribed_text_content = "⏳ Transcribing audio..."
        st.session_state.ipc_codes_content = "Relevant IPC sections will appear here..."
        # Force immediate UI update for text areas
        st.experimental_rerun() 

    elif audio_bytes and (not client or not st.session_state.get("client_initialized", False)):
        st.error("🔴 Groq client not initialized. Cannot process audio. Check API key and client initialization above.")

# This block handles processing if audio_bytes exist from the previous run after rerun
if st.session_state.transcribed_text_content == "⏳ Transcribing audio..." and client and st.session_state.get("client_initialized", False) and audio_bytes:
    try:
        audio_buffer = io.BytesIO(audio_bytes)  # audio_bytes should be from current session state or recorder
        audio_buffer.name = "filename.wav"  # Groq API expects a name attribute for the file tuple

        # Perform transcription
        transcription_response = client.audio.transcriptions.create(
            file=(audio_buffer.name, audio_buffer.getvalue()), # Pass buffer.getvalue()
            model="whisper-large-v3-turbo",
            response_format="json"
        )
        
        if transcription_response and transcription_response.text:
            st.session_state.transcribed_text_content = transcription_response.text
            
            # IPC Code Generation Trigger
            # Check if transcription was successful and not an error/placeholder message
            valid_transcription = st.session_state.transcribed_text_content and \
                                  not st.session_state.transcribed_text_content.startswith("Transcription failed") and \
                                  not st.session_state.transcribed_text_content.startswith("API Error") and \
                                  not st.session_state.transcribed_text_content.startswith("Unexpected Error")

            if valid_transcription:
                st.session_state.ipc_codes_content = "⏳ Generating IPC codes..."
                st.experimental_rerun() # Rerun to show "Generating IPC codes..."
            else: # Transcription was not valid for IPC generation
                 st.session_state.ipc_codes_content = "Relevant IPC sections will appear here..." # Reset IPC
                 st.experimental_rerun()

        else: # Transcription response was empty or invalid
            st.session_state.transcribed_text_content = "Transcription failed: No text in response."
            st.warning("Transcription was not successful. Please try recording again.")
            st.session_state.ipc_codes_content = "Relevant IPC sections will appear here..." # Reset IPC
            st.experimental_rerun()

    except groq.APIError as e_transcribe:
        st.error(f"🔴 Groq API Error during transcription: {e_transcribe}")
        st.session_state.transcribed_text_content = f"API Error: {e_transcribe}"
        st.session_state.ipc_codes_content = "Relevant IPC sections will appear here..." # Reset IPC
        st.experimental_rerun()
    except Exception as e_general_transcribe:
        st.error(f"🔴 An unexpected error occurred during transcription: {e_general_transcribe}")
        st.session_state.transcribed_text_content = f"Unexpected Error: {e_general_transcribe}"
        st.session_state.ipc_codes_content = "Relevant IPC sections will appear here..." # Reset IPC
        st.experimental_rerun()

# This block handles IPC generation if transcription was successful from the previous run
if st.session_state.ipc_codes_content == "⏳ Generating IPC codes..." and client and st.session_state.get("client_initialized", False):
    try:
        system_message = """You are a helpful legal assistant. Your task is to analyze the user's description of a crime and identify relevant sections from the Indian Penal Code (IPC). Only list the IPC section numbers and their titles (e.g., 'Section 302: Punishment for murder.'). Do not add any extra explanations, disclaimers, or introductory/concluding remarks unless they are part of the IPC section title itself. If no specific crime is described or the text is too vague, state 'No specific IPC sections applicable based on the description.'"""
        user_message = st.session_state.transcribed_text_content # Use the transcribed text

        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ],
            model="mixtral-8x7b-32768",
            temperature=0.2,
            max_tokens=1000, # Increased max_tokens for potentially longer lists of IPCs
        )
        if chat_completion.choices and chat_completion.choices[0].message and chat_completion.choices[0].message.content:
            st.session_state.ipc_codes_content = chat_completion.choices[0].message.content
        else:
            st.session_state.ipc_codes_content = "IPC code generation failed or returned empty."
            st.warning("IPC code generation was not successful.")
    except groq.APIError as ipc_e:
        st.error(f"🔴 Groq API Error during IPC code generation: {ipc_e}")
        st.session_state.ipc_codes_content = f"API Error during IPC generation: {ipc_e}"
    except Exception as ipc_gen_e:
        st.error(f"🔴 An unexpected error occurred during IPC code generation: {ipc_gen_e}")
        st.session_state.ipc_codes_content = f"Unexpected Error during IPC generation: {ipc_gen_e}"
    st.experimental_rerun() # Rerun to display the final IPC codes or error


with col2:
    st.subheader("2. Transcribed Text")
    st.text_area(
        "Transcribed Text", 
        value=st.session_state.transcribed_text_content, 
        key="transcribed_text_display_area", 
        height=200,  # Increased height
        disabled=True
    )
    st.markdown("---") # Visual separator
    st.subheader("3. Generated IPC Sections")
    st.text_area(
        "Generated IPC Sections", 
        value=st.session_state.ipc_codes_content, 
        key="ipc_codes_display_area", 
        height=300,  # Increased height
        disabled=True
    )
    st.markdown("---") # Visual separator
    # Disclaimer
    st.warning("""
    ⚠️ **Disclaimer:** The IPC sections generated by this tool are for informational purposes only and are based on AI interpretation. 
    They should not be considered legal advice. Always consult with a qualified legal professional for any legal matters.
    """)

st.markdown("---")
st.markdown("<p style='text-align: center;'>Powered by Streamlit and Groq</p>", unsafe_allow_html=True)
