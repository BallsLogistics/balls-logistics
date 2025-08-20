# firebase_config.py
import streamlit as st
import pyrebase

# firebase_config.py
import streamlit as st
import pyrebase

@st.cache_resource
def _init_firebase():
    required = [
        "FIREBASE_API_KEY", "FIREBASE_AUTH_DOMAIN", "FIREBASE_DATABASE_URL",
        "FIREBASE_PROJECT_ID", "FIREBASE_STORAGE_BUCKET",
        "FIREBASE_MESSAGING_SENDER_ID", "FIREBASE_APP_ID"
    ]
    missing = [k for k in required if k not in st.secrets]
    if missing:
        raise RuntimeError(
            "Missing Streamlit secrets: "
            + ", ".join(missing)
            + ". Add them to .streamlit/secrets.toml"
        )

    cfg = {
        "apiKey": st.secrets["FIREBASE_API_KEY"],
        "authDomain": st.secrets["FIREBASE_AUTH_DOMAIN"],
        "databaseURL": st.secrets["FIREBASE_DATABASE_URL"],
        "projectId": st.secrets["FIREBASE_PROJECT_ID"],
        "storageBucket": st.secrets["FIREBASE_STORAGE_BUCKET"],  # must be *.appspot.com
        "messagingSenderId": st.secrets["FIREBASE_MESSAGING_SENDER_ID"],
        "appId": st.secrets["FIREBASE_APP_ID"],
    }
    app = pyrebase.initialize_app(cfg)
    return app, app.auth(), app.database()

firebase_app, auth, db = _init_firebase()



