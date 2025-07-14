
from dotenv import load_dotenv
import os
import openai
import streamlit as st
import time
import datetime
import speech_recognition as sr
from difflib import get_close_matches

# Load environment and OpenAI API key
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

st.set_page_config(page_title="CaseClock", layout="centered")
st.title("⚖️ CaseClock - Voice Timer with Fuzzy Case Names")

# 🎙️ Voice Command Input
st.subheader("🎙️ Voice Command (uses your Mac's mic)")

st.markdown("""
**Try one of these voice commands:**
- `Start logging Sierra Club`
- `Switch to Big Sewickley Creek`
- `Begin timer for Three Rivers Keeper`
- `Stop timer`
- `Stop logging`
""")

if st.button("🎧 Start Listening"):
    recognizer = sr.Recognizer()

    try:
        with sr.Microphone() as source:
            st.info("Listening for 10 seconds...")
            audio = recognizer.listen(source, timeout=10, phrase_time_limit=10)

        try:
            transcript = recognizer.recognize_google(audio)
            st.success(f"You said: '{transcript}'")
        except sr.UnknownValueError:
            transcript = ""
            st.error("Sorry, could not understand the audio.")
        except sr.RequestError:
            transcript = ""
            st.error("Mic or internet issue. Try again.")
    except sr.WaitTimeoutError:
        transcript = ""
        st.warning("⏱️ Listening timed out — no speech detected.")
    except Exception as e:
        transcript = ""
        st.error(f"Mic failed: {e}")
else:
    transcript = ""

# Session state
if "is_timing" not in st.session_state:
    st.session_state.is_timing = False
    st.session_state.start_time = None
    st.session_state.client = ""
    st.session_state.logs = []

known_cases = ["Sierra Club", "Big Sewickley Creek", "Three Rivers Keeper"]

# Interpret voice command
def interpret_command(transcript):
    transcript = transcript.lower().strip()
    start_phrases = ["start logging", "begin timer for", "track time for", "switch to"]
    stop_phrases = ["stop timer", "end time", "pause logging", "stop logging"]

    for phrase in start_phrases:
        if transcript.startswith(phrase):
            client_part = transcript[len(phrase):].strip()
            match = get_close_matches(client_part, known_cases, n=1, cutoff=0.5)
            if match:
                return "start", match[0]
            else:
                return "start", client_part

    for phrase in stop_phrases:
        if phrase in transcript:
            return "stop", None

    return "unrecognized", None

# Handle logic
if transcript:
    action, client = interpret_command(transcript)
    if action == "start":
        st.session_state.is_timing = True
        st.session_state.start_time = time.time()
        st.session_state.client = client
        st.success(f"✅ Timer started for: {client}")
    elif action == "stop":
        if st.session_state.is_timing:
            duration = int(time.time() - st.session_state.start_time)
            log_entry = {
                "client": st.session_state.client,
                "start": datetime.datetime.fromtimestamp(st.session_state.start_time).strftime("%Y-%m-%d %H:%M:%S"),
                "end": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "duration": str(datetime.timedelta(seconds=duration))
            }
            st.session_state.logs.append(log_entry)
            st.success(f"🛑 Timer stopped. Duration: {log_entry['duration']}")
            st.session_state.is_timing = False
            st.session_state.client = ""
        else:
            st.warning("No timer is currently running.")
    else:
        st.warning("Command not recognized.")

# Display timer
if st.session_state.is_timing:
    st.info(f"⏱️ Timer running for: {st.session_state.client}")

# Show log
if st.session_state.logs:
    st.subheader("📋 Time Log")
    st.table(st.session_state.logs)

    if st.download_button("📤 Export Log", data="\n".join([
        "client,start,end,duration"
    ] + [f"{row['client']},{row['start']},{row['end']},{row['duration']}" for row in st.session_state.logs]),
    file_name="caseclock_log.csv"):
        st.success("Log downloaded!")

    if st.button("🧠 Summarize Log with AI"):
        log_text = "\n".join([
            f"{row['client']} from {row['start']} to {row['end']} ({row['duration']})"
            for row in st.session_state.logs
        ])
        with st.spinner("Summoning GPT..."):
            try:
                response = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You're a helpful assistant who summarizes legal time logs."},
                        {"role": "user", "content": f"Summarize this log in 1-2 sentences:\n{log_text}"}
                    ]
                )
                summary = response['choices'][0]['message']['content']
                st.success("📄 Summary:")
                st.write(summary)
            except Exception as e:
                st.error(f"Error: {e}")
