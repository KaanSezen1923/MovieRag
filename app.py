import requests
import streamlit as st 

st.set_page_config(page_title="MovieRag",page_icon="🎬")

st.title("MovieRag: GraphRAG Movie Recommendation Chatbot")

api_url = "http://127.0.0.1:8000"


if "messages" not in st.session_state:
    st.session_state["messages"] = []


for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        if message["role"] == "user":
            st.write(message["content"])
        else:
           
            for movie in message["content"]:
                st.write(f"**Title:** {movie['title']}")
                st.write(f"**Overview:** {movie['overview']}")
                st.write("**Genres:**", ", ".join(movie['genres']))
                st.write("**Actors:**", ", ".join(movie['actors']))
                st.write(f"**Director:** {movie['director']}")
                st.write(f"**Vote Average:** {movie['vote_average']}")
                st.write(f"**Reason:** {movie['reason']}")
                
                if "image_available" in movie and movie["image_available"]:
                    st.image(movie["image_path"], caption=movie["title"], use_column_width=True)


if user_query := st.chat_input("What kind of movie do you want to watch?"):
    with st.chat_message("user"):
        st.write(user_query)

    
    st.session_state["messages"].append({"role": "user", "content": user_query})

    try:
        
        response_json = requests.get(f"{api_url}/movies/search/{user_query}")
        if response_json.status_code != 200:
            st.error(f"Error: {response_json.json()['detail']}")
        else:
            response = response_json.json()["response"]
            assistant_content = []

            
            with st.chat_message("assistant"):
                for movie in response:
                    st.write(f"**Title:** {movie['title']}")
                    st.write(f"**Overview:** {movie['overview']}")
                    st.write("**Genres:**", ", ".join(movie['genres']))
                    st.write("**Actors:**", ", ".join(movie['actors']))
                    st.write(f"**Director:** {movie['director']}")
                    st.write(f"**Vote Average:** {movie['vote_average']}")
                    st.write(f"**Reason:** {movie['reason']}")

                    
                    image_response = requests.get(movie["image_path"])
                    image_available = image_response.status_code == 200
                    if image_available:
                        st.image(movie["image_path"], caption=movie["title"], use_column_width=True)
                    st.write("-----------------------------")

                    
                    movie_data = movie.copy()
                    movie_data["image_available"] = image_available
                    assistant_content.append(movie_data)

            
            st.session_state["messages"].append({"role": "assistant", "content": assistant_content})

    except requests.exceptions.RequestException as e:
        st.error(f"Failed to connect to the API: {e}")






