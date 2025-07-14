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
st.title("⚖️ CaseClock – Voice Timer with Mic + Fuzzy")

# 🎙️ Voice Command Input
st.subheader("🎙️ Voice Command (uses your Mac's mic)")
st.markdown("""
**Try one of these voice commands:**
- `Start logging Sierra Club`
- `Switch to Big Sewickley Creek`
- `Start billing Three Rivers`
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

# Session state init
if 'is_timing' not in st.session_state:
    st.session_state.is_timing = False
    st.session_state.start_time = None
    st.session_state.client = ""
    st.session_state.logs = []

# Fuzzy command interpreter
def interpret_command(transcript):
    transcript = transcript.lower().strip()
    start_phrases = ["start logging", "begin timer for", "track time for", "switch to", "start billing"]
    stop_phrases = ["stop timer", "end time", "pause logging", "stop logging"]

    for phrase in start_phrases:
        if transcript.startswith(phrase):
            client = transcript[len(phrase):].strip()
            return "start", client

    close_stop = get_close_matches(transcript, stop_phrases, n=1, cutoff=0.7)
    if transcript in stop_phrases or close_stop:
        return "stop", None

    return "unrecognized", None

# Command handling
if transcript:
    action, client = interpret_command(transcript)
    if action == "start":
        st.session_state.is_timing = True
        st.session_state.start_time = time.time()
        st.session_state.client = client
        st.success(f"✅ Timer started for: {client}")
    elif action == "stop":
        if st.session_state.is_timing:
            end_time = time.time()
            duration = int(end_time - st.session_state.start_time)
            minutes, seconds = divmod(duration, 60)
            human_duration = f"{minutes} min {seconds} sec" if minutes else f"{seconds} sec"

            st.session_state.logs.append({
    "date": datetime.datetime.now().strftime("%Y-%m-%d"),
    "client": st.session_state.client,
    "start": datetime.datetime.fromtimestamp(st.session_state.start_time).strftime("%H:%M:%S"),
    "end": datetime.datetime.now().strftime("%H:%M:%S"),
    "duration": human_duration,
    "task": ""
})
            st.success(f"🛑 Timer stopped. Duration: {human_duration}")
            st.session_state.is_timing = False
            st.session_state.client = ""
        else:
            st.warning("No timer running.")
    else:
        st.warning("Command not recognized.")

# Timer status
if st.session_state.is_timing:
    st.info(f"⏱️ Timer running for: {st.session_state.client}")

# Show logs as editable table with dropdown + delete + add
import pandas as pd

if st.session_state.logs:
    st.subheader("📋 Editable Time Log")

    log_df = pd.DataFrame(st.session_state.logs)

    # Ensure 'task' column exists
    if 'task' not in log_df.columns:
        log_df['task'] = ""

    task_options = ['Call', 'Meeting', 'Research', 'Drafting', 'Email', 'Other']

    # Editable log table
    edited_df = st.data_editor(
        log_df,
        num_rows="dynamic",
        column_config={
            "task": st.column_config.SelectboxColumn("Task", options=task_options)
        }
    )

    # Delete checkboxes
    st.write("🗑️ Select entries to delete:")
    delete_indices = []
    for i, row in edited_df.iterrows():
        if st.checkbox(f"Delete row {i+1}: {row['client']} ({row['duration']})", key=f"del_{i}"):
            delete_indices.append(i)

    if st.button("🚮 Delete Selected Rows"):
        edited_df = edited_df.drop(index=delete_indices).reset_index(drop=True)
        st.success(f"Deleted {len(delete_indices)} row(s).")

    # Save changes to session
    if st.button("💾 Save Edits to Log"):
        st.session_state.logs = edited_df.to_dict(orient="records")
        st.success("Edits saved!")

    # Export with 'task' column
    if st.download_button("📤 Export Log", data="\n".join([
        "date,client,start,end,duration,task"
    ] + [f"{row['date']},{row['client']},{row['start']},{row['end']},{row['duration']},{row.get('task','')}" for row in st.session_state.logs]),
    file_name="caseclock_log_human_readable.csv"):
        st.success("Log downloaded!")

# New entry form (always available)
st.markdown("➕ **Add New Log Entry**")

new_date = st.date_input("Date", value=datetime.date.today())
new_client = st.text_input("Client")
new_start = st.time_input("Start Time", value=datetime.time(9, 0))
new_end = st.time_input("End Time", value=datetime.time(10, 0))
new_task = st.selectbox("Task", ['Call', 'Meeting', 'Research', 'Drafting', 'Email', 'Other'])

# Calculate duration
start_dt = datetime.datetime.combine(new_date, new_start)
end_dt = datetime.datetime.combine(new_date, new_end)
delta = end_dt - start_dt

if delta.total_seconds() < 0:
    st.error("⚠️ End time must be after start time.")
    calculated_duration = None
else:
    minutes = int(delta.total_seconds() // 60)
    hours, mins = divmod(minutes, 60)
    if hours > 0:
        calculated_duration = f"{hours} hr {mins} min" if mins else f"{hours} hr"
    else:
        calculated_duration = f"{mins} min"
    st.info(f"🧮 Duration: {calculated_duration}")

if st.button("Add Entry"):
    if not new_client:
        st.warning("Please enter a client name.")
    elif calculated_duration is None:
        st.warning("Fix time entry before submitting.")
    else:
        new_entry = {
            "date": new_date.strftime("%Y-%m-%d"),
            "client": new_client,
            "start": new_start.strftime("%H:%M:%S"),
            "end": new_end.strftime("%H:%M:%S"),
            "duration": calculated_duration,
            "task": new_task
        }
        st.session_state.logs.append(new_entry)
        st.success("New entry added!")
        st.rerun()
