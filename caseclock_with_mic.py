from dotenv import load_dotenv
import os
import openai
import streamlit as st
import time
import datetime
import speech_recognition as sr
from rapidfuzz import process

# Load environment and OpenAI API key
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

st.set_page_config(page_title="CaseClock", layout="centered")
st.title("⚖️ CaseClock – Voice Timer with Fuzzy Case Matching")

st.markdown("""
**🎙️ Try voice commands like:**
- `Start logging Sierra Club`
- `Start Big Sewickley Creek`
- `Switch to Three Rivers`
- `Stop timer`
""")

# --- Known Case Names ---
known_cases = [
    "Sierra Club",
    "Big Sewickley Creek",
    "Three Rivers",
    "Ohio River",
    "Queen Creek",
    "Adams",
    "Johnson"
]

# Session state
if "is_timing" not in st.session_state:
    st.session_state.is_timing = False
    st.session_state.start_time = None
    st.session_state.client = ""
    st.session_state.logs = []

# Fuzzy match logic
def extract_case_name(command):
    lowered = command.lower()
    trigger_phrases = [
        "start logging", "start billing", "switch to", "track", "begin logging"
    ]
    for phrase in trigger_phrases:
        if lowered.startswith(phrase):
            return command[len(phrase):].strip()
    return command

def match_case(input_text):
    best_match = process.extractOne(input_text, known_cases, score_cutoff=75)
    if best_match:
        return best_match[0]
    return None

# Mic section
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
            st.error("Could not understand.")
        except sr.RequestError:
            transcript = ""
            st.error("Speech service error.")
    except sr.WaitTimeoutError:
        transcript = ""
        st.warning("⏱️ Timed out, no speech.")
else:
    transcript = ""

# Interpret and act
if transcript:
    lower = transcript.lower()
    if "stop" in lower and "start" not in lower:
        if st.session_state.is_timing:
            duration_sec = round(time.time() - st.session_state.start_time)
            duration_str = str(datetime.timedelta(seconds=duration_sec))
            st.session_state.logs.append({
                "client": st.session_state.client,
                "start": datetime.datetime.fromtimestamp(st.session_state.start_time).strftime("%Y-%m-%d %H:%M:%S"),
                "end": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "duration": duration_str
            })
            st.success(f"🛑 Stopped timer. Logged {duration_str} for {st.session_state.client}")
            st.session_state.is_timing = False
            st.session_state.client = ""
        else:
            st.warning("Timer wasn't running.")
    else:
        raw_case = extract_case_name(transcript)
        case_match = match_case(raw_case)
        if case_match:
            st.session_state.is_timing = True
            st.session_state.start_time = time.time()
            st.session_state.client = case_match
            st.success(f"✅ Timer started for: {case_match}")
        else:
            st.warning(f"Could not match to any known case: '{raw_case}'")

# Timer display
if st.session_state.is_timing:
    st.info(f"⏱️ Timer running for: {st.session_state.client}")

# Log display
if st.session_state.logs:
    st.subheader("📋 Time Log")
    st.table(st.session_state.logs)

    if st.download_button("📤 Export CSV", data="\n".join([
        "client,start,end,duration"
    ] + [f"{row['client']},{row['start']},{row['end']},{row['duration']}" for row in st.session_state.logs]),
    file_name="caseclock_log.csv"):
        st.success("Log downloaded!")

    if st.button("🧠 Summarize Log"):
        log_text = "\n".join([
            f"{row['client']} from {row['start']} to {row['end']} ({row['duration']})"
            for row in st.session_state.logs
        ])
        with st.spinner("Summarizing..."):
            try:
                response = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You're a helpful assistant who summarizes time logs."},
                        {"role": "user", "content": f"Summarize this log in 1-2 sentences:\n{log_text}"}
                    ]
                )
                st.write(response['choices'][0]['message']['content'])
            except Exception as e:
                st.error(f"Error: {e}")
...
