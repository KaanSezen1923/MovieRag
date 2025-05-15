from fastapi import FastAPI, HTTPException
from neo4j import GraphDatabase
from typing import List, Dict, Optional
from pydantic import BaseModel
import google.generativeai as genai 
import os
from dotenv import load_dotenv
import traceback
import json


app = FastAPI()

load_dotenv()

gemini_api_key = os.getenv("GEMINI_API_KEY")
neo4j_uri = os.getenv("NEO4J_URI")
neo4j_user = os.getenv("NEO4J_USER")
neo4j_password = os.getenv("NEO4J_PASSWORD")

neo4j_driver = GraphDatabase.driver(
    neo4j_uri, auth=(neo4j_user, neo4j_password)
) 


    
def gemini_configuration(api_key, system_prompt, response_mime_type="text/plain"):
    genai.configure(api_key=api_key)
                    
    generation_config = {
        "temperature": 0.7,
        "top_p": 0.9,
        "top_k": 40,
        "max_output_tokens": 2048,
        "response_mime_type": response_mime_type,
    }

    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        generation_config=generation_config,
        system_instruction=system_prompt
    )
    
    chat_session = model.start_chat(history=[])
    return chat_session

def find_category_and_get_movies(api_key, user_input):
    system_prompt = f"""
Analyze the user query: '{user_input}' and categorize the mentioned term(s) into one or more of the following categories:

    - "Director" (e.g., Christopher Nolan, Quentin Tarantino)
    - "Actor" (e.g., Leonardo DiCaprio, Tom Hanks)
    - "Genre" (e.g., 'Action', 'Adventure', 'Fantasy', 'Science Fiction', 'Crime', 'Drama', 'Thriller', 'Animation', 'Family', 'Western', 'Comedy', 'Romance', 'Horror', 'Mystery', 'History', 'War', 'Music', 'Documentary', 'Foreign', 'TV Movie')
    - "Keyword" (e.g., 'culture clash', 'future', 'space war', 'space colony', 'society', 'space travel', 'futuristic', 'romance', 'space', 'alien', 'tribe', 'alien planet', 'cgi', 'marine', 'soldier', 'battle', 'love affair', 'anti war', 'power relations', 'mind and soul', '3d', 'ocean', 'drug abuse', 'exotic island', 'east india trading company', "love of one's life", 'traitor', 'shipwreck', 'strong woman', 'ship', 'alliance', 'calypso', 'afterlife', 'fighter', 'pirate', 'swashbuckler', 'aftercreditsstinger', 'spy', 'based on novel', 'secret agent', 'sequel', 'mi6', 'british secret service', 'united kingdom', 'dc comics', 'crime fighter', 'terrorist', 'secret identity', 'burglar', 'hostage drama', 'time bomb', 'gotham city', 'vigilante', 'cover-up', 'superhero', 'villainess', 'tragic hero', 'terrorism', 'destruction', 'catwoman', 'cat burglar', 'imax', 'flood', 'criminal underworld', 'batman', 'mars', 'medallion', 'princess', 'steampunk', 'martian', 'escape', 'edgar rice burroughs', 'alien race', 'superhuman strength', 'mars civilization', 'sword and planet', '19th century', 'dual identity', 'amnesia', 'sandstorm', 'forgiveness', 'spider', 'wretch', 'death of a friend', 'egomania', 'sand', 'narcism', 'hostility', 'marvel comic', 'revenge', 'hostage', 'magic', 'horse', 'fairy tale', 'musical', 'animation', 'tower', 'blonde woman', 'selfishness', 'healing power', 'based on fairy tale', 'duringcreditsstinger', 'healing gift', 'animal sidekick', 'based on comic book', 'vision', 'superhero team', 'marvel cinematic universe', 'witch', 'broom', 'school of witchcraft', 'wizardry', 'apparition', 'teenage crush', 'werewolf', 'super powers','vampire')
    - "Movie" (e.g., Inception, Interstellar)

Return the results in JSON format like this:
{{
    "categories": [
        {{"category": "Director", "name": "Christopher Nolan"}}
    ]
}}
"""
    chat_session = gemini_configuration(api_key, system_prompt, response_mime_type="application/json")
    try:
        response = chat_session.send_message(user_input)
        response_json = json.loads(response.parts[0].text)
    except Exception as e:
        return {"error": f"Failed to parse Gemini response: {str(e)}"}
    
    categories = response_json.get("categories", [])
    if not categories:
        return {"error": "Category not found. Please be more specific."}
    
    category = categories[0]["category"]
    name = categories[0]["name"]
        
    query_map = {
        "Actor": """MATCH (a:Actor)-[:ACTED_IN]->(m:Movie) WHERE toLower(a.name) 
        CONTAINS toLower($param) RETURN m.movie_id, m.title, m.overview,m.genres,m.actors,m.director, m.vote_average,m.image_path LIMIT 10""",
        "Director": """MATCH (d:Director)-[:DIRECTED]->(m:Movie) WHERE toLower(d.name) 
        CONTAINS toLower($param) RETURN m.movie_id, m.title, m.overview,m.genres,m.actors,m.director, m.vote_average,m.image_path LIMIT 10""",
        "Genre": """MATCH (g:Genre)-[:HAS_GENRE]->(m:Movie) WHERE toLower(g.name) 
        CONTAINS toLower($param) RETURN m.movie_id, m.title, m.overview,m.genres,m.actors,m.director, m.vote_average,m.image_path LIMIT 10""",
        "Keyword": """MATCH (k:Keyword)-[:HAS_KEYWORD]->(m:Movie) WHERE toLower(k.name) 
        CONTAINS toLower($param) RETURN m.movie_id, m.title, m.overview,m.genres,m.actors,m.director, m.vote_average,m.image_path LIMIT 10""",
        "Movie": """MATCH (m:Movie) WHERE toLower(m.title) CONTAINS toLower($param) 
        WITH m MATCH (similar:Movie) WHERE toLower(similar.overview) CONTAINS toLower(m.overview) 
        RETURN similar.movie_id, similar.title, similar.overview, similar.vote_average LIMIT 10"""
    }
    
    query = query_map.get(category)
    if not query:
        return {"error": "Invalid category detected"}

    with neo4j_driver.session() as session:
        results = session.run(query, {"param": name}).data()
        return results
    
def get_movie_image_path_from_neo4j(title):
    query = """
    MATCH (m:Movie) 
    WHERE toLower(m.title) = toLower($title)
    RETURN m.image_path AS image_path LIMIT 1
    """
    with neo4j_driver.session() as session:
        result = session.run(query, {"title": title}).single()
        return result["image_path"] if result else None



def get_recommendations_with_llm(user_input, context):
    system_instruction = f"""
    You are MovieRag, a warm, friendly, and empathetic movie recommendation chatbot that acts like the user's best friend. The user said: '{user_input}'. Your goal is to recommend 3-5 movies tailored to their interests and mood in a concise, engaging chat, avoiding unnecessary questions.

    How to Respond:
    1. **Analyze Input**: Check if the user mentioned a specific genre, director, actor, keyword, or movie (e.g., 'action', 'Christopher Nolan', 'Inception'). If so, use this information and the provided context ({context}) to suggest relevant movies immediately.
    2. **Handle Vague Input**: If the input is vague (e.g., 'I'm bored', 'I don’t know'), infer the mood (e.g., boredom → fun/uplifting movies) and ask *at most one* clarifying question (e.g., 'Looking for something funny or adventurous?'). If no response is provided, proceed with recommendations based on the inferred mood.
    3. **Be Empathetic**: Reflect the user's emotions warmly (e.g., 'Feeling stressed? Let’s find something relaxing!').
    4. **Use Context**: Seamlessly incorporate the provided database results ({context}) into your suggestions without breaking the conversational flow.
    5. **Recommend Movies**: Suggest 3-5 movies, each with:
    - Title
    - Director
    - Main Actors
    - Short Summary (2-3 sentences)
    - Why It Fits (how it matches the user’s mood or request)
    6. **Highlight a Favorite**: Pick one movie as the 'star of the day' and explain why it’s perfect for the user.
    7. **Keep It Friendly**: Use a relaxed, fun tone, like chatting over coffee. Avoid formal language.
    8. **Avoid Question Loops**: Do not ask more than two question, and only if absolutely necessary. If the user has provided enough detail, go straight to recommendations.

    Additional Rules:
    - If the user mentions a specific genre, director, actor, or keyword, prioritize those in your recommendations and avoid asking for clarification.
    - If the context ({context}) contains relevant movies, use them to ground your suggestions.
    - Keep responses concise but sincere to maintain engagement.
    - If the user shares very little, make an educated guess about their mood and suggest movies after one question at most.

    Sample Dialogue:
    User: "I want action movies"
    Chatbot: "Awesome, let’s dive into some action-packed fun! 😎 Here are my picks:\n
    1. **Mad Max: Fury Road**  
    **Director**: George Miller  
    **Cast**: Tom Hardy, Charlize Theron  
    **Summary**: A high-octane chase through a post-apocalyptic wasteland with jaw-dropping stunts.  
    **Why**: Pure adrenaline to satisfy your action craving!  
    2. **John Wick**  
    **Director**: Chad Stahelski  
    **Cast**: Keanu Reeves  
    **Summary**: A retired hitman seeks vengeance in a stylish, action-packed thriller.  
    **Why**: Perfect for intense, edge-of-your-seat vibes.  
    3. **Die Hard**  
    **Director**: John McTiernan  
    **Cast**: Bruce Willis  
    **Summary**: A cop battles terrorists in a skyscraper during Christmas.  
    **Why**: A classic action flick with humor and heart.  
    My star pick is **Mad Max: Fury Road** – its non-stop energy is an action lover’s dream! Enjoy! 🎬"

    Sample Dialogue (Vague Input):
    User: "I’m bored."
    Chatbot: "Boredom’s no fun! 😕 Want something funny or maybe adventurous to spice things up? Or I can pick some uplifting movies for you!\n
    User:Adventorus .
    Chatbot:Here  a few adventorus movie for you :
        1. **The Grand Budapest Hotel**  
    **Director**: Wes Anderson  
    **Cast**: Ralph Fiennes, Tony Revolori  
    **Summary**: A quirky hotel concierge gets caught in a wild adventure.  
    **Why**: Its colorful humor will chase boredom away!  
    2. **Superbad**  
    **Director**: Greg Mottola  
    **Cast**: Jonah Hill, Michael Cera  
    **Summary**: Two teens embark on a hilarious night of party-chasing chaos.  
    **Why**: Perfect for a laugh-filled escape.  
    3. **Crazy Rich Asians**  
    **Director**: Jon M. Chu  
    **Cast**: Constance Wu, Henry Golding  
    **Summary**: A woman navigates her boyfriend’s ultra-rich family in a fun rom-com.  
    **Why**: Light and uplifting to boost your mood.  
    My star pick is **The Grand Budapest Hotel** – its whimsical vibe is a boredom-buster! What do you think?"

    Let’s make your movie night amazing! 
    
    User: "I feel sad."
    Chatbot: "I'm sorry to hear you're feeling down today. 😔 Would you like some uplifting movies that might help cheer you up? Or perhaps something funny to distract you from those feelings?"
    User: "Uplifting movies please."
    Chatbot: "Here are a few uplifting movies that might help brighten your mood:

    The Secret Life of Walter Mitty
    Director: Ben Stiller
    Cast: Ben Stiller, Kristen Wiig
    Summary: A daydreamer embarks on an unexpected adventure of self-discovery.
    Why: Its beautiful scenery and inspiring message about taking chances might lift your spirits.
    Soul
    Director: Pete Docter
    Cast: Jamie Foxx, Tina Fey
    Summary: A musician discovers what makes life worth living.
    Why: Heartwarming with profound messages about appreciating life.
    Little Miss Sunshine
    Director: Jonathan Dayton, Valerie Faris
    Cast: Abigail Breslin, Steve Carell
    Summary: A dysfunctional family takes a road trip to support their daughter's pageant dreams.
    Why: Shows how even when life gets messy, there's still joy to be found.

    My top recommendation is The Secret Life of Walter Mitty – its journey from sadness to inspiration might resonate with you right now. What do you think?"
    
    User: "I feel upset."
    Chatbot: "I'm sorry you're feeling upset today. 😔 Sometimes a good movie can help provide a mental escape or shift your perspective. Would you prefer something light and distracting, or perhaps something inspiring that might help lift your spirits?"
    User: "Something inspiring please."
    Chatbot: "Here are a few inspiring movies that might help when you're feeling upset:

    Good Will Hunting
    Director: Gus Van Sant
    Cast: Robin Williams, Matt Damon
    Summary: A janitor with extraordinary mathematical abilities finds guidance from a therapist who helps him face his past.
    Why: Shows how we can overcome emotional barriers with support and courage.
    The Pursuit of Happyness
    Director: Gabriele Muccino
    Cast: Will Smith, Jaden Smith
    Summary: A struggling salesman takes custody of his son as he's poised to begin a life-changing career.
    Why: A powerful reminder that perseverance can help us through difficult times.
    Inside Out
    Director: Pete Docter
    Cast: Amy Poehler, Phyllis Smith
    Summary: A young girl's emotions work together to help her adjust to a new life.
    Why: Helps normalize all emotions and shows how even sadness has an important role.

    My recommendation would be Inside Out – it's especially good when you're processing difficult emotions. What do you think?"
    
    User: "I feel bad."
    Chatbot: "I'm sorry to hear you're not feeling well today. 😟 Sometimes a good movie can be a helpful distraction when you're feeling down. Would you prefer something lighthearted to lift your mood, or maybe something inspiring that might give you a new perspective?"
    User: "Something lighthearted please."
    Chatbot: "Here are a few lighthearted movies that might help when you're feeling bad:

    Paddington
    Director: Paul King
    Cast: Ben Whishaw, Hugh Bonneville
    Summary: A charming bear finds a new home with a London family.
    Why: Its warmth and gentle humor make it perfect comfort viewing.
    School of Rock
    Director: Richard Linklater
    Cast: Jack Black, Joan Cusack
    Summary: A fake substitute teacher turns students into rock stars.
    Why: Jack Black's energy and the fun music are sure to boost your mood.
    The Princess Bride
    Director: Rob Reiner
    Cast: Cary Elwes, Robin Wright
    Summary: A classic tale of true love and high adventure.
    Why: A perfect blend of comedy, romance, and fantasy to take your mind off troubles.

    My top pick would be Paddington – its heartwarming story and gentle humor are like a cozy blanket for the soul when you're feeling bad. What do you think?"
😊"""


    llm = gemini_configuration(gemini_api_key, system_instruction, response_mime_type="text/plain")
    try:
        response = llm.send_message(user_input)
        recommendations_text = response.parts[0].text
        return recommendations_text
    except Exception as e:
        print(f"Debug: Unexpected error in LLM = {str(e)}")
        return f"An error occurred: {str(e)}"
    
def extract_movie_title(text, gemini_api_key):
    system_prompt = f"""
    Your task is to extract five movie titles from the given text.
    Example output:
    Avatar\nAvengers: Age of Ultron\nMan of Steel\nMen in Black 3\nJurassic World
    """
    llm = gemini_configuration(gemini_api_key, system_prompt)
    llm_response = llm.send_message(text)
    if hasattr(llm_response, 'text'):
        return [movie.strip() for movie in llm_response.text.strip().split("\n") if movie.strip()]
    return []

@app.get("/movies/search/{query}")
async def search_movies(query: str) -> Dict:
    try:
        results = find_category_and_get_movies(gemini_api_key, query)
        if "error" in results:
            raise HTTPException(status_code=400, detail=results["error"])

        recommendations = get_recommendations_with_llm(query, results)
        titles= extract_movie_title(recommendations, gemini_api_key)
        image_paths = {}
        for title in titles:
            image_path = get_movie_image_path_from_neo4j(title)
            image_paths[title] = image_path if image_path else None
                
        if "An error occurred" in recommendations:
            raise HTTPException(status_code=500, detail=recommendations)
        
        return {"question": query, "context": results, "response": recommendations,"images":image_paths}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error")
    


    

