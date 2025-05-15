import os
import requests
import streamlit as st
import speech_recognition as sr
from gtts import gTTS
from audio_recorder_streamlit import audio_recorder
from firebase_admin import firestore, credentials
import firebase_admin
import datetime
import traceback

st.set_page_config(page_title="MovieRag", page_icon="🎬")

st.title("MovieRag: GraphRAG Movie Recommendation Chatbot")

api_url = "http://127.0.0.1:8000"


if not firebase_admin._apps:
    try:
        cred = credentials.Certificate("movie-rag-firebase-adminsdk-fbsvc-a46f1f2595.json")
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Firebase başlatma hatası: {e}")
        st.stop()

db = firestore.client()


def save_chat_to_firestore(username, chat_id, messages):
    try:
        
        storable_messages = []
        for msg in messages:
            storable_msg = msg.copy()
           
            if "images" in storable_msg:
                storable_msg["images"] = {title: path for title, path in storable_msg.get("images", {}).items() if path}
            storable_messages.append(storable_msg)
        
        doc_ref = db.collection("users").document(username).collection("chats").document(chat_id)
        doc_ref.set({"messages": storable_messages, "created_at": chat_id})
    except Exception as e:
        st.error(f"Sohbet kaydedilirken hata: {e}")


def load_user_chats(username):
    try:
        chat_histories = {}
        chats_ref = db.collection("users").document(username).collection("chats")
        for chat_doc in chats_ref.stream():
            chat_histories[chat_doc.id] = chat_doc.to_dict().get("messages", [])
        return chat_histories
    except Exception as e:
        st.error(f"Sohbetler yüklenirken hata: {e}")
        return {}


def delete_chat_from_firestore(username, chat_id):
    try:
        doc_ref = db.collection("users").document(username).collection("chats").document(chat_id)
        doc_ref.delete()
        return True
    except Exception as e:
        st.error(f"Sohbet silinirken hata: {e}")
        return False


if "username" in st.session_state:
    username = st.session_state["username"]
    st.session_state["chat_histories"] = load_user_chats(username)
    st.subheader(f"Hello {username}! Which movie do you want to watch today?")
else:
    st.warning("Lütfen giriş yapın.")
    st.switch_page("pages/login.py")


if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "chat_histories" not in st.session_state:
    st.session_state["chat_histories"] = {}
if "current_chat" not in st.session_state:
    st.session_state["current_chat"] = None
if "confirm_delete" not in st.session_state:
    st.session_state["confirm_delete"] = None


def recognize_speech():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("Konuşmaya başlayabilirsiniz...")
        try:
            audio = recognizer.listen(source, timeout=5)
            text = recognizer.recognize_google(audio, language="tr-TR")
            st.success(f"Saptanan metin: {text}")
            return text
        except sr.UnknownValueError:
            st.error("Ses anlaşılamadı, lütfen tekrar deneyin.")
        except sr.RequestError as e:
            st.error(f"Ses tanıma servisiyle ilgili bir sorun oluştu: {e}")
        return None


def fetch_movie_recommendations(query):
    try:
        response = requests.get(f"{api_url}/movies/search/{query}")
        if response.status_code != 200:
            st.error(f"API Hatası: {response.json().get('detail', 'Bilinmeyen hata')}")
            return None, None
        data = response.json()
        response_text = data.get("response", "")
        images = data.get("images", {})
        return response_text, images
    except requests.exceptions.RequestException as e:
        st.error("Üzgünüm, bu soruya yanıt veremedim.")
        print(f"API bağlantı hatası: {e}")
        return None, None


st.sidebar.title("Sohbet Geçmişi")

button_container = st.sidebar.container()
col1, col2 = button_container.columns([1, 1])

with col1:
    new_chat_button = st.button("Yeni Sohbet", use_container_width=True)
with col2:
    logout_button = st.button("Çıkış Yap", use_container_width=True)


if new_chat_button:
    new_chat_id = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state["chat_histories"][new_chat_id] = []
    st.session_state["current_chat"] = new_chat_id
    st.session_state["messages"] = []
    
    save_chat_to_firestore(username, new_chat_id, [])
    st.rerun()


if logout_button:
    st.session_state.clear()
    st.switch_page("pages/login.py")


sorted_chat_histories = sorted(
    st.session_state["chat_histories"].items(),
    key=lambda x: x[0],
    reverse=True
)


for chat_id, chat_history in sorted_chat_histories:
    with st.sidebar.container():
        try:
            chat_date = datetime.datetime.strptime(chat_id, "%Y-%m-%d %H:%M:%S")
            display_date = chat_date.strftime("%d %b %Y, %H:%M")
        except ValueError:
            display_date = chat_id

        user_query_preview = (
            chat_history[0]["content"]
            if chat_history and isinstance(chat_history[0]["content"], str)
            else f"Sohbet ({display_date})"
        )
        if len(user_query_preview) > 30:
            user_query_preview = user_query_preview[:27] + "..."

        col1, col2 = st.columns([4, 1])
        with col1:
            if st.button(f"{user_query_preview} ({display_date})", key=chat_id):
                st.session_state["current_chat"] = chat_id
                st.session_state["messages"] = chat_history
                st.session_state["confirm_delete"] = None  
                st.rerun()

        with col2:
            if st.button("🗑️", key=f"delete_{chat_id}"):
                st.session_state["confirm_delete"] = chat_id
                st.rerun()

    if st.session_state["confirm_delete"] == chat_id:
        with st.sidebar.container():
            st.warning(f"'{user_query_preview}' sohbetini silmek istediğinize emin misiniz?")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Evet, Sil", key=f"confirm_delete_{chat_id}"):
                    if delete_chat_from_firestore(username, chat_id):
                        st.session_state["chat_histories"].pop(chat_id, None)
                        
                        if st.session_state["current_chat"] == chat_id:
                            st.session_state["current_chat"] = None
                            st.session_state["messages"] = []
                        
                        st.session_state["chat_histories"] = load_user_chats(username)
                        
                        st.session_state["confirm_delete"] = None
                        
                        st.success("Sohbet silindi.")
                        st.rerun()
            
            with col2:
                if st.button("İptal", key=f"cancel_delete_{chat_id}"):
                    st.session_state["confirm_delete"] = None
                    st.rerun()



for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.write(message["content"])
        
        
        if message.get("images"):
            for title, image_path in message["images"].items():
                if image_path:
                    try:
                        st.image(image_path, caption=title, use_column_width=True)
                    except Exception as e:
                        print(f"Resim yüklenirken hata oluştu: {e}")


user_query = st.chat_input("Hangi filmi izlemek istersin?")
record_audio = audio_recorder()

if user_query or record_audio:
    if record_audio and not user_query:
        user_query = recognize_speech()

    if user_query:
        with st.chat_message("user"):
            st.write(user_query)

        st.session_state["messages"].append({"role": "user", "content": user_query})

        recommendations, images = fetch_movie_recommendations(user_query)
        if recommendations:
            with st.chat_message("assistant"):
                st.write(recommendations)
                
                
                if images:
                    for title, image_path in images.items():
                        if image_path:
                            try:
                                st.image(image_path, caption=title, use_column_width=True)
                            except Exception as e:
                                print(f"Resim yüklenirken hata oluştu: {e}")

            
            st.session_state["messages"].append({
                "role": "assistant", 
                "content": recommendations,
                "images": images
            })

        else:
            st.error("Öneri bulunamadı.")

        
        if st.session_state["current_chat"]:
            st.session_state["chat_histories"][st.session_state["current_chat"]] = st.session_state["messages"]
            save_chat_to_firestore(username, st.session_state["current_chat"], st.session_state["messages"])
        else:
            
            new_chat_id = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.session_state["current_chat"] = new_chat_id
            st.session_state["chat_histories"][new_chat_id] = st.session_state["messages"]
            save_chat_to_firestore(username, new_chat_id, st.session_state["messages"])






