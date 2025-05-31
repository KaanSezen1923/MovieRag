# MovieRag 🎬

A GraphRAG-powered movie recommendation chatbot that combines Neo4j graph database, Google Gemini AI, and Streamlit to provide personalized movie recommendations based on user preferences, mood, and queries.

## Features

- 🤖 **Intelligent Recommendations**: Uses Google Gemini AI to understand user queries and provide contextual movie suggestions
- 🗄️ **Graph Database**: Leverages Neo4j to store and query movie relationships (actors, directors, genres, keywords)
- 🎯 **Multi-Category Search**: Supports search by director, actor, genre, keywords, or specific movies
- 💬 **Conversational Interface**: Natural language processing for intuitive user interactions
- 🔊 **Voice Input**: Speech recognition for hands-free movie queries
- 🖼️ **Visual Experience**: Displays movie posters and images alongside recommendations
- 👤 **User Authentication**: Firebase-based login and signup system
- 💾 **Chat History**: Persistent conversation storage across sessions
- 📱 **Responsive Design**: Streamlit-based web interface

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Streamlit UI  │────│   FastAPI       │────│   Neo4j DB      │
│   (Frontend)    │    │   (Backend)     │    │   (Graph Data)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │
         │                       │
┌─────────────────┐    ┌─────────────────┐
│   Firebase      │    │   Google        │
│   (Auth/Store)  │    │   Gemini AI     │
└─────────────────┘    └─────────────────┘
```

## Tech Stack

- **Backend**: FastAPI, Python
- **Frontend**: Streamlit
- **Database**: Neo4j (Graph Database)
- **AI/ML**: Google Gemini AI
- **Authentication**: Firebase Admin SDK
- **Voice**: SpeechRecognition, gTTS
- **Additional**: Pydantic, python-dotenv

## Installation

### Prerequisites

- Python 3.8+
- Neo4j Database
- Google Gemini API Key
- Firebase Project Setup

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/KaanSezen1923/movierag.git
   cd movierag
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Configuration**
   Create a `.env` file in the root directory:
   ```env
   GEMINI_API_KEY=your_gemini_api_key
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=your_neo4j_password
   ```

4. **Firebase Setup**
   - Create a Firebase project
   - Generate a service account key
   - Save it as `movie-rag-firebase-adminsdk-fbsvc-a46f1f2595.json` in the root directory

5. **Neo4j Database Setup**
   - Install and start Neo4j
   - Create the following node types and relationships:
     - Nodes: `Movie`, `Actor`, `Director`, `Genre`, `Keyword`
     - Relationships: `ACTED_IN`, `DIRECTED`, `HAS_GENRE`, `HAS_KEYWORD`

## Usage

### Start the Backend API

```bash
uvicorn api:app --reload
```

The API will be available at `http://127.0.0.1:8000`

### Launch the Streamlit App

```bash
streamlit run app.py
```

The web interface will open at `http://localhost:8501`

### API Endpoints

- `GET /movies/search/{query}` - Search and get movie recommendations

## Database Schema

### Neo4j Graph Structure

```cypher
// Example nodes and relationships
(m:Movie {title: "Inception", overview: "...", vote_average: 8.8, image_path: "..."})
(a:Actor {name: "Leonardo DiCaprio"})
(d:Director {name: "Christopher Nolan"})
(g:Genre {name: "Science Fiction"})
(k:Keyword {name: "dream"})

// Relationships
(a)-[:ACTED_IN]->(m)
(d)-[:DIRECTED]->(m)
(g)-[:HAS_GENRE]->(m)
(k)-[:HAS_KEYWORD]->(m)
```

## Key Components

### 1. Query Processing (`api.py`)
- **Category Detection**: Uses Gemini AI to classify user queries into categories (Director, Actor, Genre, Keyword, Movie)
- **Neo4j Queries**: Executes appropriate Cypher queries based on detected categories
- **LLM Integration**: Generates conversational responses with movie recommendations

### 2. User Interface (`app.py`)
- **Chat Interface**: Streamlit-based conversational UI
- **Voice Integration**: Speech-to-text and text-to-speech capabilities
- **Session Management**: Persistent chat history with Firebase
- **Image Display**: Movie poster integration

### 3. Authentication (`pages/login.py`)
- **Firebase Auth**: Secure user registration and login
- **Session Handling**: User state management across app sessions

## Features in Detail

### Intelligent Categorization
The system automatically detects whether user input refers to:
- **Directors**: "Christopher Nolan movies"
- **Actors**: "Leonardo DiCaprio films"
- **Genres**: "action movies", "romantic comedies"
- **Keywords**: "space travel", "time travel", "superhero"
- **Specific Movies**: "movies like Inception"

### Conversational AI
MovieRag acts as a friendly movie companion that:
- Understands mood and context
- Provides empathetic responses
- Asks minimal clarifying questions
- Suggests 3-5 tailored recommendations
- Highlights a "star pick" for each session

### Multimodal Interface
- **Text Input**: Traditional typing interface
- **Voice Input**: Speech recognition for hands-free interaction
- **Visual Output**: Movie posters and images
- **Persistent History**: Saved conversations across sessions

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Requirements

```txt
fastapi
neo4j
pydantic
google-generativeai
python-dotenv
streamlit
SpeechRecognition
gTTS
audio-recorder-streamlit
firebase-admin
requests
uvicorn
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GEMINI_API_KEY` | Google Gemini AI API key | Yes |
| `NEO4J_URI` | Neo4j database connection URI | Yes |
| `NEO4J_USER` | Neo4j database username | Yes |
| `NEO4J_PASSWORD` | Neo4j database password | Yes |

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Google Gemini AI for natural language processing
- Neo4j for graph database capabilities
- Streamlit for the web interface framework
- Firebase for authentication and storage services

## Contact

Kaan Sezen- kaantruk1923@gmail.com

Project Link: [https://github.com/yourusername/movierag](https://github.com/KaanSezen1923/movierag)

---

Made with ❤️ and 🎬 by [Kaan Sezen]
