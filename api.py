from fastapi import FastAPI, HTTPException
from neo4j import GraphDatabase
from typing import List, Dict, Optional
from pydantic import BaseModel
import google.generativeai as genai 
import os
from dotenv import load_dotenv
import traceback
import json
import uvicorn


app = FastAPI()

load_dotenv()

gemini_api_key = os.getenv("GEMINI_API_KEY")
neo4j_uri = os.getenv("NEO4J_URI")
neo4j_user = os.getenv("NEO4J_USER")
neo4j_password = os.getenv("NEO4J_PASSWORD")

neo4j_driver = GraphDatabase.driver(
    neo4j_uri, auth=(neo4j_user, neo4j_password)
)

class MovieResponse(BaseModel):
    title: str
    overview: str
    genres:List[str]
    actors:List[str]
    director:str
    vote_average: str
    reason: str
    image:str
    
def gemini_configuration(api_key, system_prompt):
    genai.configure(api_key=api_key)
                    
    generation_config = {
        "temperature": 0.7,
        "top_p": 0.9,
        "top_k": 40,
        "max_output_tokens": 2048,
        "response_mime_type": "application/json",
    }

    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        generation_config=generation_config,
        system_instruction=system_prompt
    )
    
    chat_session = model.start_chat(history=[])
    
    return chat_session


def find_category_and_get_movies(api_key,user_input):
    
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


    chat_session = gemini_configuration(api_key,system_prompt)
    try:
        response = chat_session.send_message(user_input)
        response_json = json.loads(response.parts[0].text)
    except Exception as e:
        return {"error": "Failed to parse Gemini response"}
    categories=response_json.get("categories", [])
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
    Greetings, movie lover! I’m your enthusiastic, film-obsessed assistant here to sprinkle some cinematic magic into your day. My mission? To dive into your query and a batch of retrieved movies (my treasure map of film goodies) and handpick exactly 5 stellar recommendations just for you. I’ll sniff out your vibe—whether it’s a genre obsession, a favorite actor, a quirky director, or a mood you’re chasing—and mix it with patterns I spot in the movie stash to craft a list that’ll make you say, “Wow, this bot gets me!”

    ### User Query: {user_input}
    ### Retrieved Movies: {json.dumps(context, indent=2)}

    #### How I Roll:
    1. **Cracking Your Query:** I’ll decode what you’re craving—maybe a spine-chilling ‘horror’ flick, a punchy ‘action’ ride, or a dose of ‘funny’ to lighten your day. You name it, I’m on it!
    2. **Movie Stash Sleuthing:** I’ll rummage through the retrieved films, spotting juicy connections—shared genres, star power, visionary directors, or hidden themes—to build my recommendation recipe.
    3. **Picking the Gems:** I’ll serve up 5 films that vibe with your query and echo the best bits from the stash. If the stash is a bit thin, I’ll flex my movie nerd muscles and guess what you’d love anyway.
    4. **Why I Chose ‘Em:** For each pick, I’ll spill the tea on why it’s perfect—think, “This one’s got vampire chills galore, just like you wanted!”—tying it to your query and the stash’s sparkle.
    5. **How I Serve It Up:** You’ll get a neat JSON platter with exactly 5 films, loaded with all the must-know details. No fluff, just the good stuff!

    #### Your JSON Goodie Bag:
    [
        {{
            "title": "string",
            "overview": "string (a quick peek at the movie’s soul)",
            "genres": ["string (genre flavors I know you’ll dig)"],
            "actors": ["string (the stars lighting up the screen)"],
            "director": "string (the genius behind the camera)",
            "vote_average": "string (like ‘8.1’—a little score to brag about)",
            "reason": "string (my excited pitch on why this one’s a winner for you)",
            "image_path": "string (a snazzy TMDB link like 'https://image.tmdb.org/t/p/w500/vL5LR6WdxWPjLPFRLe133jXWsh5.jpg')"
        }},
        ...
    ]

    #### My Cinephile Code:
    - I keep it fresh and varied, but always on point with what you’re into.
    - Vague query like ‘good movie’? No sweat—I’ll peek at the stash and guess your taste like a pro.
    - Every field’s filled with legit, juicy details, even if I have to get creative with what’s on hand.
    - ‘Vote_average’ stays sharp with decimals (e.g., ‘7.5’, not just ‘7’—I’m precise like that!).
    - My ‘image_path’ picks are unique, TMDB-style, and look so real you’ll want to frame ‘em.
    - You’ll always get exactly 5 picks—because who doesn’t love a perfect handful of movie magic?

    So, grab some popcorn and let’s find your next favorite flick together!
    """
    llm = gemini_configuration(gemini_api_key, system_instruction)
    try:
        response = llm.send_message(user_input)
        raw_response = response.parts[0].text
        response_json = json.loads(raw_response)
       
        if not isinstance(response_json, list) or len(response_json) != 5:
            raise ValueError("Response must contain exactly 5 recommendations")
        for movie in response_json:
            neo4j_image_path = get_movie_image_path_from_neo4j(movie["title"])
            movie["image_path"] = neo4j_image_path
        return response_json
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Debug: LLM response parsing error = {str(e)}")  
        

    except Exception as e:
        print(f"Debug: Unexpected error in LLM = {str(e)}")
        return {"error": f"Unexpected error: {str(e)}"}


    

    




@app.get("/movies/search/{query}")
async def search_movies(query: str) -> Dict:
    try:
        results = find_category_and_get_movies(gemini_api_key, query)
        if "error" in results:
            raise HTTPException(status_code=400, detail=results["error"])

        recommendations = get_recommendations_with_llm(query, results)
        if "error" in recommendations:
            raise HTTPException(status_code=500, detail=recommendations["error"])

        return {"question": query, "context": results, "response": recommendations}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error")
    

