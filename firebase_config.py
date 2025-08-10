# firebase_config.py
import streamlit as st
import pyrebase

@st.cache_resource  # replaces deprecated st.cache
def _init_firebase():
    cfg = {
        "apiKey": st.secrets["FIREBASE_API_KEY"],
        "authDomain": st.secrets["FIREBASE_AUTH_DOMAIN"],
        "databaseURL": st.secrets["FIREBASE_DATABASE_URL"],
        "projectId": st.secrets["FIREBASE_PROJECT_ID"],
        "storageBucket": st.secrets["FIREBASE_STORAGE_BUCKET"],
        "messagingSenderId": st.secrets["FIREBASE_MESSAGING_SENDER_ID"],
        "appId": st.secrets["FIREBASE_APP_ID"],
    }
    app = pyrebase.initialize_app(cfg)
    return app, app.auth(), app.database()

firebase_app, auth, db = _init_firebase()


