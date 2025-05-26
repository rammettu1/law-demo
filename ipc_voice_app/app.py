import streamlit as st
import os
import groq
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
    # Replace audiorecorder with st.audio_input
    audio_bytes = st.audio_input(
        "Record crime description (click microphone icon to start/stop):", 
        key="audio_input_main"
    )

    # This logic will now trigger when audio_bytes becomes available from st.audio_input
    # The st.experimental_rerun() will be triggered by st.audio_input itself upon new audio.
    # We need to manage the state transition carefully.

    # Check if new audio has been uploaded and we haven't started processing it yet
    if audio_bytes and st.session_state.get("last_processed_audio_id") != id(audio_bytes):
        st.session_state.last_processed_audio_id = id(audio_bytes) # Mark this audio as being processed
        
        # Clear previous results and show processing state
        st.session_state.transcribed_text_content = "⏳ Transcribing audio..."
        st.session_state.ipc_codes_content = "Relevant IPC sections will appear here..."
        # Force immediate UI update for text areas
        st.rerun() # This rerun will move to the processing block below

    elif audio_bytes is None and "last_processed_audio_id" in st.session_state:
        # Clear the marker if audio_input is cleared (e.g. user removes the uploaded file)
        del st.session_state.last_processed_audio_id


# This block handles processing if audio_bytes exist and transcription is pending
# The audio_bytes here should be the one from the current run, which st.audio_input provides
if st.session_state.transcribed_text_content == "⏳ Transcribing audio..." and \
   client and st.session_state.get("client_initialized", False) and \
   audio_bytes: # audio_bytes from st.audio_input
    try:
        # No need for st.audio(audio_bytes, format="audio/wav") as st.audio_input handles its own UI for playback
        
        audio_buffer = io.BytesIO(audio_bytes)
        audio_buffer.name = "filename.wav"  # Groq API expects a name attribute for the file tuple

        # Perform transcription
        transcription_response = client.audio.transcriptions.create(
            file=(audio_buffer.name, audio_buffer.getvalue()), # Pass buffer.getvalue()
            model="whisper-large-v3", # Updated model
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
                st.rerun() # Rerun to show "Generating IPC codes..."
            else: # Transcription was not valid for IPC generation
                 st.session_state.ipc_codes_content = "Relevant IPC sections will appear here..." # Reset IPC
                 st.rerun()

        else: # Transcription response was empty or invalid
            st.session_state.transcribed_text_content = "Transcription failed: No text in response."
            st.warning("Transcription was not successful. Please try recording again.")
            st.session_state.ipc_codes_content = "Relevant IPC sections will appear here..." # Reset IPC
            st.rerun()

    except groq.APIError as e_transcribe:
        st.error(f"🔴 Groq API Error during transcription: {e_transcribe}")
        st.session_state.transcribed_text_content = f"API Error: {e_transcribe}"
        st.session_state.ipc_codes_content = "Relevant IPC sections will appear here..." # Reset IPC
        st.rerun()
    except Exception as e_general_transcribe:
        st.error(f"🔴 An unexpected error occurred during transcription: {e_general_transcribe}")
        st.session_state.transcribed_text_content = f"Unexpected Error: {e_general_transcribe}"
        st.session_state.ipc_codes_content = "Relevant IPC sections will appear here..." # Reset IPC
        st.rerun()

# Helper function to stream response from Groq
def stream_groq_response(api_response):
    full_response = []
    for chunk in api_response:
        content = chunk.choices[0].delta.content
        if content:
            full_response.append(content)
            yield content
    # After streaming, update session state with the complete response
    # This part needs to be called after st.write_stream has consumed the generator.
    # A direct call here won't work as the generator is consumed by write_stream.
    # Instead, we'll accumulate within the calling block of st.write_stream if possible,
    # or handle the full text storage differently.
    # For now, this generator is just for st.write_stream.
    # We will build the full_response string in the main logic block.

# This block handles IPC generation if transcription was successful from the previous run
if st.session_state.ipc_codes_content == "⏳ Generating IPC codes..." and client and st.session_state.get("client_initialized", False):
    st.session_state.ipc_streaming_complete = False # Flag to indicate streaming is not yet complete
    try:
        system_message = """You are a helpful legal assistant. Your task is to analyze the user's description of a crime and identify relevant sections from the Indian Penal Code (IPC). Only list the IPC section numbers and their titles (e.g., 'Section 302: Punishment for murder.'). Do not add any extra explanations, disclaimers, or introductory/concluding remarks unless they are part of the IPC section title itself. If no specific crime is described or the text is too vague, state 'No specific IPC sections applicable based on the description.'"""
        user_message = st.session_state.transcribed_text_content # Use the transcribed text

        # API call with streaming enabled
        response_stream = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ],
            model="meta-llama/llama-4-scout-17b-16e-instruct", # Updated model
            temperature=1, # Updated temperature
            max_tokens=1024, # Updated max_tokens
            stream=True # Enable streaming
        )
        
        # Prepare for streaming display in col2
        # The actual st.write_stream call will be in the col2 rendering block
        # We store the stream in session state to be accessed there.
        st.session_state.ipc_response_stream = response_stream
        # We don't set ipc_codes_content here with the stream,
        # it will be populated by accumulating the streamed chunks.
        # The "Generating IPC codes..." message will be shown until the stream starts rendering.
        
    except groq.APIError as ipc_e:
        st.error(f"🔴 Groq API Error during IPC code generation setup: {ipc_e}")
        st.session_state.ipc_codes_content = f"API Error during IPC generation: {ipc_e}"
        st.session_state.ipc_streaming_complete = True # Mark as complete to avoid trying to stream
    except Exception as ipc_gen_e:
        st.error(f"🔴 An unexpected error occurred during IPC code generation setup: {ipc_gen_e}")
        st.session_state.ipc_codes_content = f"Unexpected Error during IPC generation: {ipc_gen_e}"
        st.session_state.ipc_streaming_complete = True # Mark as complete
    st.rerun() # Rerun to move to the display block in col2 or show setup error


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

    # Display logic for IPC codes (streaming or static)
    if st.session_state.ipc_codes_content == "⏳ Generating IPC codes..." and "ipc_response_stream" in st.session_state:
        # If we are in the generating state and have a stream, display it
        def stream_wrapper(stream):
            full_response_chunks = []
            try:
                for chunk in stream_groq_response(st.session_state.ipc_response_stream):
                    full_response_chunks.append(chunk)
                    yield chunk
                st.session_state.ipc_codes_content = "".join(full_response_chunks)
            except Exception as e:
                st.error(f"Error during streaming IPC codes: {e}")
                st.session_state.ipc_codes_content = "Error occurred while streaming IPC codes."
            finally:
                st.session_state.ipc_streaming_complete = True
                if "ipc_response_stream" in st.session_state: # Clean up stream from session
                    del st.session_state.ipc_response_stream 
                st.rerun() # Rerun to display the accumulated content statically or an error
        
        st.write_stream(stream_wrapper(st.session_state.ipc_response_stream))

    elif not st.session_state.get("ipc_streaming_complete", True) and "ipc_response_stream" in st.session_state:
        # This case might be hit if a rerun happens mid-stream without the "Generating..." message
        # It's a fallback to ensure the stream is processed if UI gets into an odd state.
        # For simplicity, we'll rely on the main path above. This could be refined if needed.
        st.markdown(st.session_state.ipc_codes_content) # Show current accumulated or error
    
    else:
        # Display static content if not generating or stream is complete/failed at setup
        st.markdown(st.session_state.ipc_codes_content)


    st.markdown("---") # Visual separator
    # Disclaimer
    st.warning("""
    ⚠️ **Disclaimer:** The IPC sections generated by this tool are for informational purposes only and are based on AI interpretation. 
    They should not be considered legal advice. Always consult with a qualified legal professional for any legal matters.
    """)

st.markdown("---")
st.markdown("<p style='text-align: center;'>Powered by Streamlit and Groq</p>", unsafe_allow_html=True)
