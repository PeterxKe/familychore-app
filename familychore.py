import streamlit as st
import datetime
import firebase_admin
from firebase_admin import credentials, db


cred = credentials.Certificate(st.secrets["firebase_key"])
firebase_admin.initialize_app(cred, {
    "databaseURL": "https://familychore-1f7d7-default-rtdb.europe-west1.firebasedatabase.app/"
})


st.set_page_config(page_title="Family Chore App", page_icon="🧹")

# --- Session State ---
if "role" not in st.session_state:
    st.session_state.role = None

if "family" not in st.session_state:
    st.session_state.family = None

if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = None

if "tasks" not in st.session_state:
    st.session_state.tasks = []

if "current_date" not in st.session_state:
    st.session_state.current_date = datetime.date.today()

if "note" not in st.session_state:
    st.session_state.note = ""

# --- Daily Reset (einfacher Reset, wenn Datum wechselt) ---
today = datetime.date.today()
if st.session_state.current_date != today and st.session_state.family is not None:
    st.session_state.current_date = today
    # Reset nur für eingeloggte Familie
    db.reference(f"families/{st.session_state.family}/tasks").set([])
    st.session_state.tasks = []

# --- Titel ---
st.title("Family Chore App 🧹")

# --- Auswahl: Login oder Registrieren ---
if st.session_state.auth_mode is None:
    col1, col2 = st.columns(2)
    if col1.button("🔐 Login"):
        st.session_state.auth_mode = "login"
        st.rerun()
    if col2.button("📝 Registrieren"):
        st.session_state.auth_mode = "register"
        st.rerun()
    st.stop()

# --- Registrierung ---
if st.session_state.auth_mode == "register":
    st.subheader("Familie registrieren")

    fam_name = st.text_input("Familienname:")
    parent_pw = st.text_input("Eltern-Passwort:", type="password")
    child_pw = st.text_input("Kinder-Passwort:", type="password")

    if st.button("Registrieren"):
        if fam_name == "" or parent_pw == "" or child_pw == "":
            st.error("Bitte alle Felder ausfüllen!")
        else:
            ref = db.reference(f"families/{fam_name}")
            ref.set({
                "parent_pw": parent_pw,
                "child_pw": child_pw,
                "tasks": [],
                "note": ""
            })
            st.success("Familie erfolgreich registriert!")
            st.session_state.auth_mode = "login"
            st.rerun()
    st.stop()

# --- Login (Familie + Rolle über Passwort) ---
if st.session_state.auth_mode == "login" and (st.session_state.family is None or st.session_state.role is None):
    st.subheader("Login")

    entered_pw = st.text_input("Passwort eingeben:", type="password")

    if st.button("Login"):
        families = db.reference("families").get()

        found_family = None
        found_role = None

        if families:
            for fam_name, fam_data in families.items():
                if entered_pw == fam_data.get("parent_pw"):
                    found_family = fam_name
                    found_role = "parent"
                    break
                if entered_pw == fam_data.get("child_pw"):
                    found_family = fam_name
                    found_role = "child"
                    break

        if found_family:
            st.session_state.family = found_family
            st.session_state.role = found_role
            st.success(f"Erfolgreich eingeloggt als {found_role} von {found_family}")
            st.rerun()
        else:
            st.error("Falsches Passwort!")
    st.stop()

# Ab hier sind Familie + Rolle gesetzt
CURRENT_FAMILY = st.session_state.family

# --- Preset Aufgaben ---
PRESET_TASKS = [
    "Abwasch machen",
    "Zimmer aufräumen",
    "Müll rausbringen",
    "Staubsaugen",
    "Tisch abwischen",
]

# --- Eltern-Sicht ---
if st.session_state.role == "parent":
    st.header("👨‍👧 Eltern-Dashboard")

    st.write("Heutiges Datum:", st.session_state.current_date)
    st.write(f"Familie: {CURRENT_FAMILY}")

    st.subheader("Heutige Aufgaben auswählen")

    selected_tasks = []
    for task in PRESET_TASKS:
        if st.checkbox(task, key=f"parent_{task}"):
            selected_tasks.append(task)

    st.subheader("Notiz für dein Kind")

    note_input = st.text_area("Notiz eingeben:", value=st.session_state.note)

    if st.button("💬 Notiz speichern"):
        db.reference(f"families/{CURRENT_FAMILY}/note").set(note_input)
        st.session_state.note = note_input
        st.success("Notiz gespeichert!")

    if st.button("📨 Aufgaben an Kind senden"):
        ref = db.reference(f"families/{CURRENT_FAMILY}/tasks")
        ref.set([
            {"title": t, "status": "pending"} for t in selected_tasks
        ])
        st.success("Aufgaben wurden gespeichert")

    st.subheader("Status der heutigen Aufgaben")

    firebase_tasks = db.reference(f"families/{CURRENT_FAMILY}/tasks").get()

    if not firebase_tasks:
        st.info("Noch keine Aufgaben für heute.")
    else:
        for t in firebase_tasks:
            status_icon = "✅" if t["status"] == "done" else "⏳"
            st.write(f"{status_icon} {t['title']} – {t['status']}")

# --- Kinder-Sicht ---
if st.session_state.role == "child":
    st.header("🧒 Kinder-Dashboard")
    st.write(f"Familie: {CURRENT_FAMILY}")

    # --- Notiz aus Firebase laden ---
    note_ref = db.reference(f"families/{CURRENT_FAMILY}/note")
    note = note_ref.get()

    if note:
        st.session_state.note = note
        st.info(f"Notiz von deinem Elternteil: {note}")

    st.subheader("Heutige Aufgaben")

    # --- Aufgaben aus Firebase laden ---
    tasks_ref = db.reference(f"families/{CURRENT_FAMILY}/tasks")
    firebase_tasks = tasks_ref.get()

    if not firebase_tasks:
        st.info("Heute wurden dir noch keine Aufgaben zugewiesen.")
    else:
        st.session_state.tasks = firebase_tasks

        for i, task in enumerate(st.session_state.tasks):
            cols = st.columns([3, 1])

            with cols[0]:
                status_icon = "✅" if task["status"] == "done" else "⏳"
                st.write(f"{status_icon} {task['title']}")

            with cols[1]:
                if task["status"] == "pending":
                    if st.button("Done", key=f"done_{i}"):
                        db.reference(f"families/{CURRENT_FAMILY}/tasks/{i}/status").set("done")
                        st.rerun()

# --- Sidebar ---
st.sidebar.header("Menü")
if st.sidebar.button("🔙 Logout"):
    st.session_state.role = None
    st.session_state.family = None
    st.session_state.auth_mode = None
    st.rerun()
