
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
LOG_FILE = "caseclock_log.json"
EXPENSE_FILE = "caseclock_expenses.json"

EXPENSE_CATEGORIES = [
    "Gas Mileage", "Postage", "Filing Fees", "Tolls", "Lodging", "Meals",
    "Travel", "Court Copies", "Printing", "Service of Process", "Parking", "Other"
]

# === Load/save helpers ===
def load_json(path, fallback):
    if Path(path).exists():
        with open(path, "r") as f:
            return json.load(f)
    return fallback

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

case_names = load_json(CASE_FILE, [])
logs = load_json(LOG_FILE, [])
expenses = load_json(EXPENSE_FILE, [])

# === Streamlit Setup ===
st.set_page_config(page_title="CaseClock", layout="centered")
st.title("⚖️ CaseClock - Voice-Driven Legal Time & Expense Tracker")

# === Editable Case List ===
with st.expander("🗂️ Manage Case List"):
    new_case = st.text_input("➕ Add a new case")
    if st.button("Add Case") and new_case:
        if new_case not in case_names:
            case_names.append(new_case)
            save_json(CASE_FILE, case_names)
            st.success(f"Added: {new_case}")
    del_case = st.selectbox("🗑️ Delete a case", [""] + case_names)
    if st.button("Delete Selected") and del_case:
        case_names.remove(del_case)
        save_json(CASE_FILE, case_names)
        st.success(f"Deleted: {del_case}")

# === Voice Input ===
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
            st.error("Sorry, couldn't understand.")
        except sr.RequestError:
            transcript = ""
            st.error("Mic or internet issue.")
    except Exception as e:
        transcript = ""
        st.error(f"Mic error: {e}")
else:
    transcript = ""

def match_case(text):
    match, score, _ = process.extractOne(text, case_names)
    return match if score >= 80 else text.strip()

def extract_case_name(text):
    import re
    text = text.lower()
    for pattern in [
        r"(start|begin|log|logging|track|billing|start billing)( time)?( for)? ",
        r"(switch to|change to) ",
        r"(stop|end)( logging| tracking)?( for)? ",
        r"(bill|add|log)( expense)?( for)? "
    ]:
        text = re.sub(pattern, "", text)
    return text.strip()

# === Timer State ===
if 'is_timing' not in st.session_state:
    st.session_state.is_timing = False
    st.session_state.start_time = None
    st.session_state.client = ""
    st.session_state.logs = logs
    st.session_state.expenses = expenses

# === Voice Parsing Logic ===
if transcript:
    lower = transcript.lower()
    if any(word in lower for word in ["start", "begin", "log", "track", "billing", "switch"]):
        case = match_case(extract_case_name(lower))
        st.session_state.is_timing = True
        st.session_state.start_time = time.time()
        st.session_state.client = case
        st.success(f"✅ Timer started for: {case}")
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
            task_type = st.selectbox("Task type?", ["", "briefing", "meeting", "research", "prep", "email", "call", "other"])
            notes = st.text_input("Notes (optional):")
            if st.button("✅ Save Entry"):
                log_entry["task_type"] = task_type
                log_entry["notes"] = notes
                st.session_state.logs.append(log_entry)
                save_json(LOG_FILE, st.session_state.logs)
                st.success(f"🛑 Logged {log_entry['duration']} for {log_entry['client']}")
                st.session_state.is_timing = False
                st.session_state.client = ""
    elif "bill" in lower or "add" in lower or "expense" in lower:
        for cat in EXPENSE_CATEGORIES:
            if cat.lower() in lower:
                category = cat
                break
        else:
            category = "Other"
        case = match_case(extract_case_name(lower))
        st.subheader("🧾 Log Expense")
        st.text(f"Client: {case}")
        st.text(f"Category: {category}")
        amount = st.text_input("Amount (e.g., 32.50):", key="expense_amt")
        note = st.text_input("Notes (optional):", key="expense_note")
        if st.button("✅ Save Expense"):
            entry = {
                "client": case,
                "category": category,
                "amount": amount,
                "notes": note,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            st.session_state.expenses.append(entry)
            save_json(EXPENSE_FILE, st.session_state.expenses)
            st.success(f"Logged expense for {case}: {category} (${amount})")

# === Timer Status ===
if st.session_state.is_timing:
    st.info(f"⏱️ Timer running for: {st.session_state.client}")

# === Logs ===
if st.session_state.logs:
    st.subheader("📋 Time Log")
    for e in st.session_state.logs:
        row = f"{e['client']}: {e['start']} → {e['end']} ({e['duration']})"
        if e.get("task_type"): row += f" — {e['task_type']}"
        if e.get("notes"): row += f" | Notes: {e['notes']}"
        st.write(row)

    st.download_button("📤 Download Time CSV", data="client,start,end,duration,task_type,notes\n" + "\n".join(
        f"{e['client']},{e['start']},{e['end']},{e['duration']},{e.get('task_type','')},{e.get('notes','')}" for e in st.session_state.logs
    ), file_name="caseclock_log.csv")

# === Expenses ===
if st.session_state.expenses:
    st.subheader("💸 Expense Log")
    for e in st.session_state.expenses:
        st.write(f"{e['client']} — {e['category']}: ${e['amount']} | {e['timestamp']} {('- ' + e['notes']) if e['notes'] else ''}")

    st.download_button("📥 Download Expenses CSV", data="client,category,amount,timestamp,notes\n" + "\n".join(
        f"{e['client']},{e['category']},{e['amount']},{e['timestamp']},{e.get('notes','')}" for e in st.session_state.expenses
    ), file_name="caseclock_expenses.csv")

# === Total Time Per Case Summary ===
if st.session_state.logs:
    st.subheader("📊 Total Hours per Case")
    from collections import defaultdict
    totals = defaultdict(float)
    for e in st.session_state.logs:
        t = e['duration'].split(':')
        hours = int(t[0]) + int(t[1])/60 + int(t[2])/3600
        totals[e['client']] += hours
    for c, h in totals.items():
        st.write(f"🕒 {c}: {round(h, 2)} hours")
