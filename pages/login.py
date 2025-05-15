import streamlit as st
import firebase_admin
from firebase_admin import credentials, auth





if not firebase_admin._apps:
    cred = credentials.Certificate("movie-rag-firebase-adminsdk-fbsvc-a46f1f2595.json")
    firebase_admin.initialize_app(cred)

def login():
    with st.form("login"):
        email = st.text_input("Enter email")
        password = st.text_input("Enter password", type="password")  
        submit_button = st.form_submit_button("Login")
        if submit_button:
            if email and password:  
                try:
                    user = auth.get_user_by_email(email)
                    user_id = user.uid
                    st.success("Login successful")
                    st.session_state["username"] = user_id
                    st.switch_page("app.py")
                except firebase_admin.exceptions.FirebaseError as e:
                    st.error(f"Error logging in: {e}")
            else:
                st.warning("Please fill in all fields.")
                
def signup():
    with st.form("signup"):
        username = st.text_input("Enter unique username")
        email = st.text_input("Enter email")
        password = st.text_input("Enter password", type="password")  
        submit_button = st.form_submit_button("Sign Up")
        if submit_button:
            if username and email and password:  
                try:
                    user = auth.create_user(email=email, password=password, uid=username)
                    st.success("Sign up successful")
                    st.info("Please login with your email and password.")
                except firebase_admin.exceptions.FirebaseError as e:
                    st.error(f"Error signing up: {e}")
            else:
                st.warning("Please fill in all fields.")


option = st.selectbox("Log in or Sign up", ("Log in", "Sign up"))

if option == "Log in":
    login()

else:
    signup()