
from dotenv import load_dotenv
import os
import openai
import streamlit as st
import time
import datetime
import speech_recognition as sr
from rapidfuzz import process
import re

# Load environment and OpenAI API key
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

st.set_page_config(page_title="CaseClock", layout="centered")
st.title("⚖️ CaseClock - Voice Timer with Mic + Smart Fuzzy Matching")

# 🎙️ Voice Command Input
st.subheader("🎙️ Voice Command (uses your Mac's mic)")
st.markdown("""
**Try one of these voice commands:**
- `Start logging Sierra Club`
- `Switch to Three Rivers`
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

# List of known cases
KNOWN_CASES = [
    "Sierra Club",
    "Three Rivers",
    "Big Sewickley Creek",
    "Queen Creek",
    "Watson",
    "Johnson",
    "Adams"
]

# Helpers
def normalize_command(text):
    text = text.lower()
    patterns = [
        r"(start|begin|log|logging|track) (time )?(for )?",
        r"(switch to|change to) ",
        r"(stop|end) (logging|tracking)?( for)? "
    ]
    for pattern in patterns:
        text = re.sub(pattern, '', text)
    return text.strip()

def match_case(input_text):
    match, score, _ = process.extractOne(input_text, KNOWN_CASES)
    return match if score >= 75 else input_text  # fallback to new case name

# Initialize session state
if "is_timing" not in st.session_state:
    st.session_state.is_timing = False
    st.session_state.start_time = None
    st.session_state.client = ""
    st.session_state.logs = []

# Command logic
if transcript:
    cleaned = normalize_command(transcript)
    if any(kw in transcript.lower() for kw in ["start", "begin", "log", "track", "switch to"]):
        client = match_case(cleaned)
        st.session_state.is_timing = True
        st.session_state.start_time = time.time()
        st.session_state.client = client
        st.success(f"✅ Timer started for: {client}")
    elif "stop" in transcript.lower() or "end" in transcript.lower():
        if st.session_state.is_timing:
            duration = round(time.time() - st.session_state.start_time, 2)
            log_entry = {
                "client": st.session_state.client,
                "start": datetime.datetime.fromtimestamp(st.session_state.start_time).strftime('%H:%M:%S'),
                "end": datetime.datetime.now().strftime('%H:%M:%S'),
                "date": datetime.datetime.now().strftime('%Y-%m-%d'),
                "duration": str(datetime.timedelta(seconds=duration))
            }
            st.session_state.logs.append(log_entry)
            st.success(f"🛑 Timer stopped. Duration: {log_entry['duration']}")
            st.session_state.is_timing = False
            st.session_state.start_time = None
            st.session_state.client = ""
        else:
            st.warning("No timer was running.")
    else:
        st.warning("Command not recognized.")

# Show timer state
if st.session_state.is_timing:
    st.info(f"⏱️ Timer running for: {st.session_state.client}")

# Editable log table
if st.session_state.logs:
    st.subheader("📋 Time Log (Click to Edit or Delete)")

    for i, entry in enumerate(st.session_state.logs):
        with st.expander(f"{entry['client']} on {entry['date']}"):
            new_client = st.text_input(f"Edit Client Name {i}", value=entry['client'], key=f"edit_client_{i}")
            new_start = st.text_input(f"Edit Start Time {i}", value=entry['start'], key=f"edit_start_{i}")
            new_end = st.text_input(f"Edit End Time {i}", value=entry['end'], key=f"edit_end_{i}")
            new_duration = st.text_input(f"Edit Duration {i}", value=entry['duration'], key=f"edit_dur_{i}")
            new_date = st.text_input(f"Edit Date {i}", value=entry['date'], key=f"edit_date_{i}")
            if st.button(f"💾 Save Changes to Log {i}"):
                st.session_state.logs[i] = {
                    "client": new_client,
                    "start": new_start,
                    "end": new_end,
                    "duration": new_duration,
                    "date": new_date
                }
                st.success("Changes saved.")
            if st.button(f"🗑️ Delete Log {i}"):
                st.session_state.logs.pop(i)
                st.experimental_rerun()

    if st.download_button("📤 Export Log", data="\n".join([
        "client,start,end,duration,date"
    ] + [f"{row['client']},{row['start']},{row['end']},{row['duration']},{row['date']}" for row in st.session_state.logs]),
        file_name="caseclock_log.csv"):
        st.success("Log downloaded!")

    if st.button("🧠 Summarize Log with AI"):
        log_text = "\n".join([
            f"{row['client']} from {row['start']} to {row['end']} on {row['date']} ({row['duration']})"
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
