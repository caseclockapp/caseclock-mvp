
from dotenv import load_dotenv
import os
import openai
import streamlit as st
import time
import datetime
import speech_recognition as sr
from rapidfuzz import process
import json
from pathlib import Path

# Load environment and OpenAI API key
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

CASE_FILE = "caseclock_cases.json"

def load_case_names():
    path = Path(CASE_FILE)
    if path.exists():
        with open(path, "r") as f:
            return json.load(f)
    return []

def save_case_names(case_list):
    with open(CASE_FILE, "w") as f:
        json.dump(case_list, f, indent=2)

case_names = load_case_names()

st.set_page_config(page_title="CaseClock", layout="centered")
st.title("⚖️ CaseClock - Voice Timer with Persistent Logs")

st.subheader("🎙️ Voice Command (uses your Mac's mic)")
st.markdown("""
**Try voice commands like:**
- `Start logging Sierra Club`
- `Switch to Three Rivers`
- `Stop logging`
""")

def match_case(input_text, case_list):
    match, score, _ = process.extractOne(input_text, case_list)
    return match if score >= 80 else input_text.strip()

def extract_case_name(text):
    import re
    text = text.lower()
    for pattern in [
        r"(start|begin|log|logging|track|billing|start billing)( time)?( for)? ",
        r"(switch to|change to) ",
        r"(stop|end)( logging| tracking)?( for)? "
    ]:
        text = re.sub(pattern, "", text)
    return text.strip()

def save_logs(logs):
    with open("caseclock_log.json", "w") as f:
        json.dump(logs, f, indent=2)

def load_logs():
    path = Path("caseclock_log.json")
    if path.exists():
        with open(path, "r") as f:
            return json.load(f)
    return []

# Case management
with st.expander("🗂️ Manage Case List"):
    new_case = st.text_input("➕ Add a new case")
    if st.button("Add Case") and new_case:
        if new_case not in case_names:
            case_names.append(new_case)
            save_case_names(case_names)
            st.success(f"Added: {new_case}")
        else:
            st.warning("Case already exists.")

    delete_case = st.selectbox("🗑️ Delete a case", [""] + case_names)
    if st.button("Delete Selected") and delete_case and delete_case in case_names:
        case_names.remove(delete_case)
        save_case_names(case_names)
        st.success(f"Deleted: {delete_case}")

    if st.button("🔄 Reload Case List"):
        st.rerun()

# Initialize session state
if 'is_timing' not in st.session_state:
    st.session_state.is_timing = False
    st.session_state.start_time = None
    st.session_state.client = ""
    st.session_state.logs = load_logs()

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

if transcript:
    lower = transcript.lower()
    if any(trigger in lower for trigger in ["start", "begin", "log", "track", "billing", "switch"]):
        name_fragment = extract_case_name(lower)
        client = match_case(name_fragment, case_names)
        st.session_state.is_timing = True
        st.session_state.start_time = time.time()
        st.session_state.client = client
        st.success(f"✅ Timer started for: {client}")
    elif "stop" in lower:
        if st.session_state.is_timing:
            duration = round(time.time() - st.session_state.start_time)
            start_dt = datetime.datetime.fromtimestamp(st.session_state.start_time)
            end_dt = datetime.datetime.now()

            log_entry = {
                "client": st.session_state.client,
                "start": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "end": end_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "duration": str(datetime.timedelta(seconds=duration))
            }

            task_type = st.selectbox("What type of task was this?", ["", "briefing", "meeting", "research", "prep", "email", "call", "other"])
            notes = st.text_input("Add any notes (optional):")

            if st.button("✅ Save Entry"):
                log_entry["task_type"] = task_type
                log_entry["notes"] = notes
                st.session_state.logs.append(log_entry)
                save_logs(st.session_state.logs)
                st.success(f"🛑 Timer stopped. Logged {log_entry['duration']} for {log_entry['client']} as {task_type or 'unspecified'}")
                st.session_state.is_timing = False
                st.session_state.client = ""

if st.session_state.is_timing:
    st.info(f"⏱️ Timer running for: {st.session_state.client}")

if st.session_state.logs:
    st.subheader("📋 Time Log")
    for i, entry in enumerate(st.session_state.logs):
        display = f"{entry['client']}: {entry['start']} → {entry['end']} ({entry['duration']})"
        if entry.get("task_type"):
            display += f" — {entry['task_type']}"
        if entry.get("notes"):
            display += f" | Notes: {entry['notes']}"
        st.write(display)

    if st.download_button("📤 Download Log as CSV", data="client,start,end,duration,task_type,notes\n" + "\n".join(
        f"{e['client']},{e['start']},{e['end']},{e['duration']},{e.get('task_type','')},{e.get('notes','')}" for e in st.session_state.logs
    ), file_name="caseclock_log.csv"):
        st.success("Log downloaded!")

    if st.button("🗑️ Clear All Logs"):
        st.session_state.logs = []
        save_logs([])
        st.success("All logs cleared.")
