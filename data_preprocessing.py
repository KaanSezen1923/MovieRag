import numpy as np
import pandas as pd
from neo4j import GraphDatabase
import traceback
from tqdm import tqdm
from typing import List, Dict, Any

class DataPreprocessor:
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        
        self.neo4j_driver = GraphDatabase.driver(
            neo4j_uri, auth=(neo4j_user, neo4j_password)
        )
        
    def parse_csv(self, filepath: str) -> pd.DataFrame:
        
        try:
            print("\nStep 1: Loading and validating CSV...")
            
            
            df = pd.read_csv(filepath)
            
            
            required_columns = ['movie_id', 'title', 'director', 'genres', 'cast', 'overview','keywords','release_date','vote_average']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")
            
            
            df['movie_id'] = df['movie_id'].astype(str)
            df['title'] = df['title'].fillna('')
            df['director'] = df['director'].fillna('')
            df['genres'] = df['genres'].fillna('')
            df['overview'] = df['overview'].fillna('')
            df['keywords'] = df['keywords'].fillna('')
            df['cast'] = df['cast'].fillna('')
            
            
            df['cast'] = df['cast'].apply(lambda x: [] if pd.isna(x) else [a.strip() for a in str(x).split(',')])
            df['genres'] = df['genres'].apply(lambda x: [] if pd.isna(x) else [a.strip() for a in str(x).split(',')])
            df['keywords'] = df['keywords'].apply(lambda x: [] if pd.isna(x) else [a.strip() for a in str(x).split(',')])
            
            
            print("\nSample data after processing:")
            print(df[['movie_id', 'title', 'cast','genres','keywords']].head())
            print(f"\nLoaded {len(df)} records from CSV")
            
            return df
        
        except Exception as e:
            print(f"Error reading CSV file: {str(e)}")
            print("\nDetailed error information:")
            traceback.print_exc()
            raise
      
    def load_neo4j(self,df:pd.DataFrame) :

        try:
                with self.neo4j_driver.session() as session:
                    print("\nStep 2: Loading to Neo4j...")
                    
                    
                    session.run("MATCH (n) DETACH DELETE n")
                    
                    
                    print("\nCreating indexes...")
                    session.run("CREATE INDEX movie_id IF NOT EXISTS FOR (m:Movie) ON (m.movie_id)")
                    session.run("CREATE INDEX actor_name IF NOT EXISTS FOR (a:Actor) ON (a.name)")
                    session.run("CREATE INDEX director_name IF NOT EXISTS FOR (d:Director) ON (d.name)")
                    session.run("CREATE INDEX genre IF NOT EXISTS FOR (g:Genre) ON (g.name)")
                    session.run("CREATE INDEX keyword IF NOT EXISTS FOR (k:Keyword) ON (k.name)")
                    
                    df["keywords"].fillna("", inplace=True) 
                    df["cast"].fillna("", inplace=True) 
                    df["genres"].fillna("", inplace=True) 
                    
                   
                    for _, row in tqdm(df.iterrows(),total=len(df),desc="Processing Movies"):
                        
                        movie_query = """
                        CREATE (m:Movie {
                            movie_id: $movie_id,
                            title: $title,
                            genres: $genres,
                            overview: $overview,
                            actors: $actors,
                            director: $director,
                            release_date:$release_date,
                            vote_average:$vote_average,
                            image_path:$image_path
                        })
                        """
                        session.run(movie_query, {
                            'movie_id': row['movie_id'],
                            'title': row['title'],
                            'genres': row['genres'],
                            'actors': row['cast'],
                            'director': row['director'],
                            'overview': row['overview'],
                            'release_date': row['release_date'],
                            'vote_average': row['vote_average'],
                            'image_path': row['image_path'],
                            
                        })
                        
                        
                        director_query = """
                        MERGE (d:Director {name: $director})
                        WITH d
                        MATCH (m:Movie {movie_id: $movie_id})
                        CREATE (d)-[:DIRECTED]->(m)
                        """
                        session.run(director_query, {
                            'director': row['director'],
                            'movie_id': row['movie_id']
                        })
                        
                        
                        for actor in row["cast"]:
                            actor_query = """
                                MERGE (a:Actor {name: $actor})
                                WITH a
                                MATCH (m:Movie {movie_id: $movie_id})
                                CREATE (a)-[:ACTED_IN]->(m)
                                """
                            session.run(actor_query, {
                                    'actor': actor,
                                    'movie_id': row['movie_id']
                                })
                            
                        for genre in row["genres"]:
                            genre_query = """
                                MERGE (g:Genre {name: $genre})
                                WITH g
                                MATCH (m:Movie {movie_id: $movie_id})
                                CREATE (g)-[:HAS_GENRE]->(m)
                            """
                            session.run(genre_query, {
                                    'genre': genre,
                                    'movie_id': row['movie_id']
                                })
                            
                            
                    
                        for keyword in row["keywords"]:
                            keyword_query = """
                                MERGE (k:Keyword {name: $keyword})
                                WITH k
                                MATCH (m:Movie {movie_id: $movie_id})
                                CREATE (k)-[:HAS_KEYWORD]->(m)
                                """
                            session.run(keyword_query, {
                                    'keyword': keyword,
                                    'movie_id': row['movie_id']
                                })
                            
                    movie_count = session.run("MATCH (m:Movie) RETURN count(m) as count").single()["count"]
                    actor_count = session.run("MATCH (a:Actor) RETURN count(a) as count").single()["count"]
                    director_count = session.run("MATCH (d:Director) RETURN count(d) as count").single()["count"]
                    genre_count = session.run("MATCH (g:Genre) RETURN count(g) as count").single()["count"]
                    keyword_count = session.run("MATCH (k:Keyword) RETURN count(k) as count").single()["count"]
                                
                    print(f"\nSuccessfully loaded:")
                    print(f"- {movie_count} movies")
                    print(f"- {actor_count} actors")
                    print(f"- {director_count} directors")
                    print(f"- {genre_count} genres")
                    print(f"- {keyword_count} keywords")
                                
                        
                    print("\nSample data in Neo4j:")
                    sample = session.run("""
                                    MATCH (m:Movie)<-[:ACTED_IN]-(a:Actor)
                                    RETURN m.title as movie, collect(a.name) as actors
                                    LIMIT 3
                                """).data()
                    print(sample)
                
        except Exception as e:
            print(f"Error loading to Neo4j: {str(e)}")
            print("\nDetailed error information:")
            traceback.print_exc()
            raise
        
    
    
        
    def close(self):
        self.neo4j_driver.close()
        
        
def main():
   
    processor = DataPreprocessor(
        neo4j_uri="neo4j+s://7a408134.databases.neo4j.io",
        neo4j_user="neo4j",
        neo4j_password="XSM4FrodZN65pqV0fPGgvvOCcCjcPIhSLeURiMh1XVY"
    )
    
    try:
        df = processor.parse_csv('movies.csv')
        processor.load_neo4j(df)
        
    except Exception as e:
        print(f"Error in main process: {str(e)}")
        traceback.print_exc()
        
    finally:
        processor.close()

if __name__ == "__main__":
    main()