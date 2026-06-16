import streamlit as st
import rdflib
import pandas as pd
import random
import os
from PIL import Image
from owlrl import RDFS_OWLRL_Semantics
from rdflib.namespace import RDF, RDFS, OWL

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
DATA_PATH = os.path.join(ROOT_DIR, "data", "books.ttl")
ONTOLOGY_PATH = os.path.join(ROOT_DIR, "ontology", "book_ontology.owl")
IMAGE_DIR = os.path.join(BASE_DIR, "image")

# This is the testing synonym dictionary
SYNONYM_MAP = {
    "Fantasy": [
        "fantasy", "magic", "wizard", "sorcerer", "witch", "curse",
        "elf", "dwarf", "knight", "castle", "enchanted",
        "mythical", "legend", "fairy", "tale", "adventure"
    ],
    
    "Mystery": [
        "mystery", "detective", "crime", "thriller", "suspense",
        "whodunnit", "investigation", "murder", "clue", "puzzle"
    ],
    
    "Romance": [
        "romance", "love", "couple", "relationship", "heart",
        "passion", "affair", "wedding", "affection", "soul mate"
    ],
    
    "Young Adult": [
        "young adult", "adventure", "speculative", "dystopian",
        "teen", "youngster"
    ],
    
    "Thriller": [
        "thriller", "suspense", "psychological", "horror", "ghost",
        "super natural", "scary", "spooky", "monster", "intense"
    ],
    
    "History": [
        "history", "historical", "ancient", "medieval", "modern",
        "world war", "civilization", "empire", "archaeology", "documentary"
    ],
    
    "Biography": [
        "biography", "memoir", "autobiography", "life story",
        "diary", "journey", "inspirational", "journal", "real life"
    ],
    
    "Technical": [
        "technical", "coding", "code", "programming", "computer",
        "software", "algorithm", "developer", "engineering",
        "clean code", "python", "java", "c++", "data structure", 
        "machine learning", "ai", "cloud", "artificial intelligence"
    ],
    
    "Cookbook": [
        "cookbook", "delicacy", "food", "culinary", "recipe",
        "kitchen", "chef", "cuisine", "baking", "cooking", "gourmet"
    ],
    
    "Education": [
        "education", "learning", "teaching", "school", "study",
        "knowledge", "mindset", "psychology", "motivation", 
        "inspiration", "improvement"
    ],
}

# Build reverse synonym lookup (e.g., "wizard" <-> "magic")
def build_reverse_synonym_map():
    """Create a mapping from any synonym to its primary category/genre"""
    reverse_map = {}
    
    for primary_key, synonym_list in SYNONYM_MAP.items():
        # Map each synonym back to the primary key
        for syn in synonym_list:
            reverse_map[syn.lower()] = primary_key
        # Also map the primary key to itself
        reverse_map[primary_key.lower()] = primary_key
    
    return reverse_map

REVERSE_SYNONYM_MAP = build_reverse_synonym_map()

# ---------------------------
# 1. LOAD RDF DATA
# ---------------------------
@st.cache_resource
def load_data():
    """Load RDF data and ontology"""
    g = rdflib.Graph()
    

    g.bind("", "http://www.example.org/bookstore#")
    g.bind("rdf", "http://www.w3.org/1999/02/22-rdf-syntax-ns#")
    g.bind("rdfs", "http://www.w3.org/2000/01/rdf-schema#")
    g.bind("owl", "http://www.w3.org/2002/07/owl#")
    g.bind("xsd", "http://www.w3.org/2001/XMLSchema#")
    
    try:
        g.parse(DATA_PATH, format="turtle")
        g.parse(ONTOLOGY_PATH, format="turtle")
    except Exception as e:
        st.error(f"Error loading data: {e}")
    
    return g

# ---------------------------
# 2. REASONING WITH RDFS_OWLRL_Semantics
# ---------------------------
@st.cache_resource
def init_reasoning_graph():
    """OWL Reasoning (RDFS_OWLRL_Semantics)"""
    if "inferred_graph" not in st.session_state:
        with st.spinner("🔮 Running OWL reasoner..."):
            try:
                g = rdflib.Graph()
                g.parse(DATA_PATH, format="turtle")
                g.parse(ONTOLOGY_PATH, format="turtle")

                inferred = rdflib.Graph()
                for triple in g:
                    inferred.add(triple)

                reasoner = RDFS_OWLRL_Semantics(inferred, axioms=True, daxioms=False, rdfs=True)
                reasoner.closure()

                st.success(f"✅ OWL reasoning completed. Added {len(inferred) - len(g)} inferred triples.")
                
                st.session_state.original_graph = g
                st.session_state.inferred_graph = inferred
                st.session_state.reasoning_enabled = True
                return True

            except Exception as e:
                st.error(f"Reasoning initialization failed: {e}")
                g = rdflib.Graph()
                g.parse(DATA_PATH, format="turtle")
                g.parse(ONTOLOGY_PATH, format="turtle")
                st.session_state.original_graph = g
                st.session_state.inferred_graph = g
                st.session_state.reasoning_enabled = False
                return False

    return st.session_state.get("reasoning_enabled", False)

def get_active_graph():
    """Get the currently active graph (prefer inferred graph)"""
    if st.session_state.get("reasoning_enabled", False):
        return st.session_state.get("inferred_graph", None)
    else:
        return st.session_state.get("original_graph", None)
    
# ---------------------------
# 3. SPARQL QUERY FUNCTIONS
# ---------------------------

def get_all_books(graph):
    """Get all books in the catalog"""
    query = """
    PREFIX : <http://www.example.org/bookstore#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    
    SELECT ?title ?author ?price WHERE {
        ?book rdf:type :Book .
        ?book :title ?title .
        ?book :author ?author .
        ?book :price ?price .
        OPTIONAL { ?book :rating ?rating . }
    }
    """
    results = []
    
    try:
        for row in graph.query(query):
            genre_query = f"""
            PREFIX : <http://www.example.org/bookstore#>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            
            SELECT ?type WHERE {{
                ?book :title "{str(row.title)}" .
                ?book :hasGenre ?type .
                FILTER(?type != :Book && ?type != :Bestseller)
            }}
            LIMIT 1
            """
            
            genre = "Unknown"
            genre_results = list(graph.query(genre_query))
            if genre_results:
                genre_uri = str(genre_results[0][0])
                genre = genre_uri.split("#")[-1]
            
            results.append({
                "Title": str(row.title),
                "Author": str(row.author),
                "Genre": genre,
                "Price (RM)": float(row.price)
            })
        
        df = pd.DataFrame(results)
        
        if df.empty:
            st.warning("No books found in the catalog")
            return pd.DataFrame(columns=["Title", "Author", "Genre", "Price (RM)"])
        else:
            st.info(f"✅ Loaded {len(df)} books from catalog")
            return df
        
    except Exception as e:
        st.error(f"Error in get_all_books: {e}")
        return pd.DataFrame(columns=["Title", "Author", "Genre", "Price (RM)"])

def get_top_rated_recommendations(graph):
    query = """
    PREFIX : <http://www.example.org/bookstore#>
    SELECT ?title ?author ?price ?rating WHERE {
        ?book :title ?title ;
              :author ?author ;
              :price ?price ;
              :rating ?rating .
        FILTER(?rating >= 4.5)
    }
    """
    results = []
    for row in graph.query(query):
        results.append({
            "Title": str(row.title),
            "Author": str(row.author),
            "Price (RM)": float(row.price)
        })
    return pd.DataFrame(results)

def search_by_keyword(graph, keyword):
    """
    Advanced keyword search that handles:
    1. Genre search with synonym expansion (PRIMARY)
    2. Category search (Fiction / NonFiction using inferred genre classes)
    3. Title/Author search (book name) - FALLBACK
    """
    keyword_original = keyword.strip()
    keyword_lower = keyword_original.lower().strip()
    
    # ============================================
    # STEP 1: DIRECT GENRE MATCHING
    # ============================================
    matched_genres = set()
    
    for genre_name in SYNONYM_MAP.keys():
        genre_lower = genre_name.lower()
        # Check exact match with genre name
        if keyword_lower == genre_lower:
            matched_genres.add(genre_name)
            continue
        
        # Check if keyword is a synonym
        for syn in SYNONYM_MAP[genre_name]:
            syn_lower = syn.lower()
            if keyword_lower == syn_lower:
                matched_genres.add(genre_name)
                break
            
        # Check partial matches (for multi-word like "young adult")
        if ' ' in keyword_lower:
            for syn in SYNONYM_MAP[genre_name]:
                syn_lower = syn.lower()
                if keyword_lower in syn_lower or syn_lower in keyword_lower:
                    matched_genres.add(genre_name)
                    break
    
    # ============================================
    # STEP 2: If genre matched, search by genre
    # ============================================
    if matched_genres:
        genre_conditions = []
        for genre in matched_genres:
            genre_clean = genre.replace(" ", "")
            genre_conditions.append(f'?type = <http://www.example.org/bookstore#{genre_clean}>')
        
        genre_filter = " || ".join(genre_conditions)
        query = f"""
        PREFIX : <http://www.example.org/bookstore#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        
        SELECT DISTINCT ?title ?author ?price ?type WHERE {{
            ?book rdf:type :Book ;
                  :title ?title ;
                  :author ?author ;
                  :price ?price .
            ?book :hasGenre ?type .
            FILTER({genre_filter})
        }}
        """
        
        results = []
        try:
            for row in graph.query(query):
                genre_uri = str(row.type)
                genre = genre_uri.split("#")[-1] if "#" in genre_uri else "Unknown"
                results.append({
                    "Title": str(row.title),
                    "Author": str(row.author),
                    "Genre": genre,
                    "Price (RM)": float(row.price)
                })
            
            seen = set()
            unique_results = []
            for r in results:
                if r["Title"] not in seen:
                    seen.add(r["Title"])
                    unique_results.append(r)
            
            if unique_results:
                st.success(f"🔍 Found {len(unique_results)} books in genre: {', '.join(matched_genres)}")
            return pd.DataFrame(unique_results)
            
        except Exception as e:
            st.error(f"Genre search error: {e}")
            return simple_keyword_search(graph, keyword_original)
    
    # ============================================
    # STEP 3: Category Search (Fiction / NonFiction)
    # ============================================
    # List of genres that belong to each category
    FICTION_GENRES = ["Fantasy", "Mystery", "Romance", "YoungAdult", "Thriller"]
    NONFICTION_GENRES = ["History", "Biography", "Technical", "Cookbook", "Education"]
    
    # FIXED: Check for NonFiction FIRST and use exact matching
    detected_category = None
    
    # First, check for NonFiction (exact matches only)
    nonfiction_terms = ["nonfiction", "non-fiction", "non fiction", "nonfictional"]
    for term in nonfiction_terms:
        if term in keyword_lower or keyword_lower in term:
            detected_category = "NonFiction"
            break
    
    # If not NonFiction, check for Fiction
    if not detected_category:
        fiction_terms = ["fiction", "fictional", "novel", "story", "tale"]
        for term in fiction_terms:
            if term == keyword_lower or keyword_lower == term:
                detected_category = "Fiction"
                break
    
    # If still not detected, check for category keywords with word boundaries
    if not detected_category:
        # Check if the keyword is a single word that matches a category
        if keyword_lower == "fiction":
            detected_category = "Fiction"
        elif keyword_lower in ["nonfiction", "non-fiction", "non fiction"]:
            detected_category = "NonFiction"
    
    if detected_category:
        # Get the list of genres for this category
        if detected_category == "Fiction":
            category_genres = FICTION_GENRES
        else:
            category_genres = NONFICTION_GENRES
        
        # Build genre conditions for all genres in this category
        genre_conditions = []
        for genre in category_genres:
            genre_clean = genre.replace(" ", "")
            genre_conditions.append(f'?type = <http://www.example.org/bookstore#{genre_clean}>')
        
        genre_filter = " || ".join(genre_conditions)
        
        query = f"""
        PREFIX : <http://www.example.org/bookstore#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        
        SELECT DISTINCT ?title ?author ?price ?type WHERE {{
            ?book rdf:type :Book ;
                  :title ?title ;
                  :author ?author ;
                  :price ?price .
            ?book :hasGenre ?type .
            FILTER({genre_filter})
        }}
        """
        
        results = []
        try:
            for row in graph.query(query):
                genre_uri = str(row.type)
                genre = genre_uri.split("#")[-1] if "#" in genre_uri else "Unknown"
                results.append({
                    "Title": str(row.title),
                    "Author": str(row.author),
                    "Genre": genre,
                    "Price (RM)": float(row.price)
                })
            
            seen = set()
            unique_results = []
            for r in results:
                if r["Title"] not in seen:
                    seen.add(r["Title"])
                    unique_results.append(r)
            
            st.success(f"📚 Found {len(unique_results)} books in category: {detected_category}")
            return pd.DataFrame(unique_results)
            
        except Exception as e:
            st.error(f"Category search error: {e}")
            return simple_keyword_search(graph, keyword_original)
    
    # ============================================
    # STEP 4: Fallback - Title/Author Search
    # ============================================
    return simple_keyword_search(graph, keyword_original)

def simple_keyword_search(graph, keyword):
    """Fallback: original keyword search (title/author only)."""
    query = f"""
    PREFIX : <http://www.example.org/bookstore#>
    SELECT ?title ?author ?price WHERE {{
        ?book :title ?title ;
              :author ?author ;
              :price ?price .
        FILTER(CONTAINS(LCASE(?title), LCASE("{keyword}")) || 
               CONTAINS(LCASE(?author), LCASE("{keyword}")))
    }}
    """
    results = []
    try:
        for row in graph.query(query):
            results.append({
                "Title": str(row.title),
                "Author": str(row.author),
                "Genre": "Unknown",
                "Price (RM)": float(row.price)
            })
        return pd.DataFrame(results)
    except Exception as e:
        st.error(f"Fallback search also failed: {e}")
        return pd.DataFrame(columns=["Title", "Author", "Genre", "Price (RM)"])

def filter_by_price(graph, min_price, max_price):
    """Filter books within price range"""
    query = f"""
    PREFIX : <http://www.example.org/bookstore#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    
    SELECT ?title ?author ?price WHERE {{
        ?book rdf:type :Book ;
              :title ?title ;
              :author ?author ;
              :price ?price .
        FILTER(?price >= {min_price} && ?price <= {max_price})
    }}
    ORDER BY ?price
    """
    results = []
    for row in graph.query(query):
        results.append({
            "Title": str(row.title),
            "Author": str(row.author),
            "Price (RM)": float(row.price)
        })
    return pd.DataFrame(results)

def get_similar_books(graph, book_title):
    """Find books similar to a given book using OWL reasoning"""

    # Retrieve information about the selected book
    info_query = f"""
    PREFIX : <http://www.example.org/bookstore#>

    SELECT ?author ?genre WHERE {{
        ?book :title "{book_title}" ;
              :author ?author .
        OPTIONAL {{ ?book :hasGenre ?genre . }}
    }}
    """

    book_info = list(graph.query(info_query))
    if not book_info:
        return pd.DataFrame()

    author = str(book_info[0][0])
    genre = str(book_info[0][1]) if book_info[0][1] else None
    genre_name = genre.split("#")[-1] if genre else None

    # Enhanced similarity calculation using reasoning
    if st.session_state.get("reasoning_enabled", False) and genre_name:
        # Method 1: Find books of the same genre using inferred classes
        query = f"""
        PREFIX : <http://www.example.org/bookstore#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        SELECT DISTINCT ?title ?author ?price WHERE {{
            {{
                # Same author
                ?book :title ?title ;
                      :author "{author}" ;
                      :price ?price .
            }}
            UNION
            {{
                # Same genre (using inferred class)
                ?book rdf:type :{genre_name}Book ;
                      :title ?title ;
                      :author ?author ;
                      :price ?price .
            }}
            FILTER(?title != "{book_title}")
        }}
        LIMIT 15
        """
    else:
        # Method 2: Original query based only on author similarity
        query = f"""
        PREFIX : <http://www.example.org/bookstore#>

        SELECT ?title ?author ?price WHERE {{
            ?book :title ?title ;
                  :author "{author}" ;
                  :price ?price .
            FILTER(?title != "{book_title}")
        }}
        LIMIT 10
        """

    results = []
    for row in graph.query(query):
        # Check if row.author is None or empty
        if row.author is None:
            # If author is missing in this result, fetch it separately
            author_query = f"""
            PREFIX : <http://www.example.org/bookstore#>
            
            SELECT ?author WHERE {{
                ?book :title "{str(row.title)}" ;
                      :author ?author .
            }}
            LIMIT 1
            """
            try:
                author_result = list(graph.query(author_query))
                book_author = str(author_result[0][0]) if author_result else "Unknown"
            except:
                book_author = "Unknown"
        else:
            book_author = str(row.author)
        
        book_genre_query = f"""
        PREFIX : <http://www.example.org/bookstore#>
        
        SELECT ?genre WHERE {{
            ?book :title "{str(row.title)}" ;
                  :hasGenre ?genre .
        }}
        LIMIT 1
        """
        
        book_genre = "Unknown"
        try:
            genre_result = list(graph.query(book_genre_query))
            if genre_result:
                genre_uri = str(genre_result[0][0])
                book_genre = genre_uri.split("#")[-1]
        except:
            pass
        
        results.append({
            "Title": str(row.title),
            "Author": book_author,
            "Genre": book_genre, 
            "Price (RM)": float(row.price) if row.price else 0
        })

    # Remove duplicate books
    seen = set()
    unique_results = []
    for r in results:
        if r["Title"] not in seen:
            seen.add(r["Title"])
            unique_results.append(r)

    if st.session_state.get("reasoning_enabled", False) and len(unique_results) > 0:
        st.info(f"🔮 The reasoning engine recommended {len(unique_results)} related books.")

    return pd.DataFrame(unique_results)

def get_genre_statistics(graph, genre):
    """Get statistics for a specific genre"""
    df = get_books_by_genre(graph, genre)
    if df.empty:
        return { "total_books": 0, "authors": [], "bestrecommend_count": 0 }
    
    bestrecommend_query = f"""
    PREFIX : <http://www.example.org/bookstore#>
    SELECT ?title WHERE {{
        ?book :title ?title ;
              :hasGenre :{genre} ;
              :rating ?rating .
        FILTER(?rating >= 4.5)
    }}
    """
    global_bestrecommend = {str(row.title) for row in graph.query(bestrecommend_query)}
    
    bestrecommend_count = sum(1 for _, book in df.iterrows() if book['Title'] in global_bestrecommend)
    
    return {
        "total_books": len(df),
        "authors": df['Author'].unique().tolist(),
        "bestrecommend_count": bestrecommend_count
    }

def get_author_statistics(graph, author_name):
    """Get statistics for a specific author, using rating >= 4.5 as best recommend."""
    query = f"""
    PREFIX : <http://www.example.org/bookstore#>
    SELECT ?title ?price ?rating WHERE {{
        ?book :title ?title ;
              :author "{author_name}" ;
              :price ?price ;
              :rating ?rating .
    }}
    """
    results = []
    bestrecommend_count = 0
    genres_set = set()

    for row in graph.query(query):
        book_title = str(row.title)
        rating = float(row.rating) if row.rating else 0.0

        genre_query = f"""
        PREFIX : <http://www.example.org/bookstore#>
        SELECT ?type WHERE {{
            ?book :title "{book_title}" .
            ?book :hasGenre ?type .
            FILTER(?type != :Book && ?type != :BestRecommend)
        }}
        LIMIT 1
        """
        genre = "Unknown"
        genre_results = list(graph.query(genre_query))
        if genre_results:
            genre_uri = str(genre_results[0][0])
            genre = genre_uri.split("#")[-1]
            genres_set.add(genre)

        is_bestrecommend = rating >= 4.5
        if is_bestrecommend:
            bestrecommend_count += 1

        results.append({
            "Title": book_title,
            "Genre": genre,
            "Price (RM)": float(row.price),
            "Best Recommend": "✅" if is_bestrecommend else "❌"
        })

    df = pd.DataFrame(results)
    return {
        "df": df,
        "total_books": len(df),
        "bestrecommend_count": bestrecommend_count,
        "genres": sorted(list(genres_set))
    }

def get_author_genres(graph, author):
    """Get all genres for an author using OWL reasoning."""
    genres = set()

    query_has = f"""
    PREFIX : <http://www.example.org/bookstore#>
    SELECT DISTINCT ?genre WHERE {{
        ?book :author "{author}" ;
              :hasGenre ?genre .
    }}
    """
    for row in graph.query(query_has):
        genre_uri = str(row.genre)
        if "#" in genre_uri:
            genres.add(genre_uri.split("#")[-1])
        else:
            genres.add(genre_uri)

    query_type = f"""
    PREFIX : <http://www.example.org/bookstore#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    SELECT DISTINCT ?type WHERE {{
        ?book :author "{author}" ;
              rdf:type ?type .
        FILTER(?type != :Book && ?type != :BestRecommend)
    }}
    """
    for row in graph.query(query_type):
        type_uri = str(row.type)
        if "#" in type_uri:
            class_name = type_uri.split("#")[-1]
            genres.add(class_name)

    return genres


def get_similar_authors(graph, current_author, current_genres, authors_list):
    """Find authors who share at least one genre with the current author."""
    current_genre_set = set(current_genres) if current_genres else get_author_genres(graph, current_author)

    similar_authors = []
    for other_author in authors_list:
        if other_author == current_author:
            continue

        other_genres = get_author_genres(graph, other_author)
        shared = current_genre_set.intersection(other_genres)

        if shared:
            similar_authors.append({
                "name": other_author,
                "shared_genres": shared
            })

    return similar_authors

def get_books_by_genre(graph, genre):
    """Get books by genre using OWL reasoning"""
    query = f"""
    PREFIX : <http://www.example.org/bookstore#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    
    SELECT ?title ?author ?price WHERE {{
        ?book :hasGenre :{genre} ;
              :title ?title ;
              :author ?author ;
              :price ?price .
    }}
    """
    
    results = []
    for row in graph.query(query):
        results.append({
            "Title": str(row.title),
            "Author": str(row.author),
            "Genre": genre,
            "Price (RM)": float(row.price)
        })
    
    return pd.DataFrame(results)

def get_books_by_author(graph, author_name):
    """Get all books by a specific author"""
    query = f"""
    PREFIX : <http://www.example.org/bookstore#>
    
    SELECT ?title ?price WHERE {{
        ?book :title ?title ;
              :author "{author_name}" ;
              :price ?price .
    }}
    """
    results = []
    for row in graph.query(query):
        genre_query = f"""
        PREFIX : <http://www.example.org/bookstore#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        
        SELECT ?type WHERE {{
            ?book :title "{str(row.title)}" .
            ?book :hasGenre ?type .
            FILTER(?type != :Book && ?type != :BestRecommend)
        }}
        LIMIT 1
        """
        
        genre = "Unknown"
        genre_results = list(graph.query(genre_query))
        if genre_results:
            genre_uri = str(genre_results[0][0])
            genre = genre_uri.split("#")[-1]
        
        results.append({
            "Title": str(row.title),
            "Genre": genre,
            "Price (RM)": float(row.price)
        })
    return pd.DataFrame(results)

def simple_keyword_recommendation(description, category, graph):
    """Original keyword recommendation method"""
    all_books = get_all_books(graph)
    if all_books.empty:
        return pd.DataFrame()
    
    keywords = description.lower().split()
    scores = []
    for _, book in all_books.iterrows():
        score = 0
        book_text = f"{book['Title']} {book['Author']} {book['Genre']}".lower()
        for kw in keywords:
            if kw in book_text:
                score += 1
        if category != "All" and category.lower() in book['Genre'].lower():
            score += 3
        scores.append(score)
    
    all_books['Score'] = scores
    recommendations = all_books[all_books['Score'] > 0].sort_values('Score', ascending=False).head(15)
    return recommendations

def extract_genres_from_description(description):
    desc_lower = description.lower()

    target_genres = set()

    # check each word that the user has input
    words = desc_lower.split()

    for word in words:

        # wizard -> magic
        if word in REVERSE_SYNONYM_MAP:

            primary = REVERSE_SYNONYM_MAP[word]

            # magic -> Fantasy
            if primary == "magic":
                target_genres.add("Fantasy")

            elif primary == "detective":
                target_genres.add("Mystery")

            elif primary == "coding":
                target_genres.add("Technical")

            elif primary == "history":
                target_genres.add("History")

            elif primary == "real life":
                target_genres.add("NonFiction")

    return target_genres

def get_recommendations_by_description(description, category, graph):
    """
    OWL reasoning based book recommendation.
    Extracts genres from description, uses inferred types, and scores books.
    """
    if not st.session_state.get("reasoning_enabled", False):
        return simple_keyword_recommendation(description, category, graph)

    desc_lower = description.lower()

    # Extract target genres from the description 
    target_genres = set()
    # map each genre to its list of keywords
    target_genres = extract_genres_from_description(description)

    # If user explicitly selected a category, add it
    if category != "All":
        target_genres.add(category)

    # Extract meaningful keywords (skip stop words) 
    stopwords = {"a", "an", "the", "and", "of", "to", "for", "with", "on", "at", "by",
                 "is", "are", "was", "were", "i", "want", "about", "book", "books"}
    words = desc_lower.split()
    keywords = {w for w in words if w not in stopwords and len(w) > 2}

    # SPARQL query to get all books with their inferred genres 
    # We query both direct :hasGenre and the inferred rdf:type (e.g., :FantasyBook)
    query = """
    PREFIX : <http://www.example.org/bookstore#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    SELECT DISTINCT ?title ?author ?price ?directGenre ?type WHERE {
        ?book rdf:type :Book ;
              :title ?title ;
              :author ?author ;
              :price ?price .
        OPTIONAL { ?book :hasGenre ?directGenre . }
        OPTIONAL { ?book rdf:type ?type . FILTER(?type != :Book && ?type != :Bestseller) }
    }
    """
    try:
        results = []
        for row in graph.query(query):
            # Extract genre from inferred type (e.g., :FantasyBook → "Fantasy")
            inferred_genre = None
            if row.type:
                type_uri = str(row.type)
                if "#" in type_uri:
                    class_name = type_uri.split("#")[-1]
                    if class_name.endswith("Book"):
                        inferred_genre = class_name[:-4]   # remove "Book"
            # Fallback to direct genre if no inferred type
            if not inferred_genre and row.directGenre:
                direct_uri = str(row.directGenre)
                if "#" in direct_uri:
                    inferred_genre = direct_uri.split("#")[-1]

            # Only keep books that have a recognizable genre
            if inferred_genre and inferred_genre in {
                    "Fantasy", "Mystery", "Romance", "YoungAdult", "Thriller",
                    "History", "Biography", "Technical", "Cookbook", "Education", "NonFiction"
                }:
                results.append({
                    "Title": str(row.title),
                    "Author": str(row.author),
                    "Price (RM)": float(row.price),
                    "Genre": inferred_genre
                })

        seen = set()
        unique_results = []
        for book in results:
            if book["Title"] not in seen:
                seen.add(book["Title"])
                unique_results.append(book)
        results = unique_results

        if not results:
            return pd.DataFrame()

        # score each book 
        scored_books = []
        for book in results:
            score = 0
            book_text = f"{book['Title']} {book['Author']}".lower()

            # Genre match 
            if book['Genre'] in target_genres:
                score += 30

            # Keyword match in title/author
            for kw in keywords:
                if kw in book_text:
                    score += 5

            # Category override
            if category != "All" and category == book['Genre']:
                score += 20

            if score > 0:
                scored_books.append((score, book))

        # Sort by score descending
        scored_books.sort(key=lambda x: x[0], reverse=True)
        recommendations = [book for _, book in scored_books[:15]]

        if recommendations:
            df = pd.DataFrame(recommendations)
            st.info(f"🔮 Reasoning engine found {len(df)} relevant books for your description.")
            return df
        else:
            return pd.DataFrame()

    except Exception as e:
        st.error(f"Reasoning recommendation failed: {e}. Falling back to simple mode.")
        return simple_keyword_recommendation(description, category, graph)

def get_book_cover(book_title):
    """Get book cover image path"""
    cover_mapping = {
        # =========================================
        # FANTASY (7 books)
        # =========================================
        "Harry Potter and the Sorcerer's Stone": "HarryPotterandtheSorcerersStone",
        "Harry Potter and the Chamber of Secrets": "HarryPotterandtheChamberofSecrets",
        "Harry Potter and the Prisoner of Azkaban": "HarryPotterandthePrisonerofAzkaban",
        "A Game of Thrones": "AGameofThrones",
        "A Clash of Kings": "AClashofKings",
        "The Hobbit": "TheHobbit",
        "The Fellowship of the Ring": "TheFellowshipoftheRing",
        
        # =========================================
        # MYSTERY (5 books)
        # =========================================
        "The Da Vinci Code": "TheDaVinciCode",
        "Angels & Demons": "Angels&Demons",
        "Gone Girl": "GoneGirl",
        "The Girl with the Dragon Tattoo": "TheGirlWithDragonTattoo",
        "The Silence of the Lambs": "TheSilenceOfTheLambs",
        
        # =========================================
        # ROMANCE (4 books)
        # =========================================
        "Pride and Prejudice": "PrideAndPrejudice",
        "Jane Eyre": "JaneEyre",
        "Outlander": "Outlander",
        "The Notebook": "TheNotebook",
        
        # =========================================
        # YOUNG ADULT (4 books)
        # =========================================
        "The Hunger Games": "TheHungerGames",
        "Catching Fire": "CatchingFire",
        "The Fault in Our Stars": "TheFaultInOurStars",
        "Divergent": "Divergent",
        
        # =========================================
        # THRILLER (3 books)
        # =========================================
        "The Shining": "TheShining",
        "The Silent Patient": "TheSilentPatient",
        
        # =========================================
        # HISTORY (4 books)
        # =========================================
        "Sapiens: A Brief History of Humankind": "SapiensABriefHistoryofHumankind",
        "Homo Deus: A Brief History of Tomorrow": "HomoDeusABriefHistoryofTomorrow",
        "The Guns of August": "TheGunsOfAugust",
        "The Rise and Fall of Ancient Egypt": "RiseAndFallAncientEgypt",
        
        # =========================================
        # BIOGRAPHY (4 books)
        # =========================================
        "Becoming": "Becoming",
        "Steve Jobs": "SteveJobs",
        "The Diary of a Young Girl": "DiaryOfAnneFrank",
        "Long Walk to Freedom": "LongWalkToFreedom",
        
        # =========================================
        # TECHNICAL (4 books)
        # =========================================
        "Clean Code: A Handbook of Agile Software Craftsmanship": "CleanCodeAHandbookofAgileSoftwareCraftsmanship",
        "The Pragmatic Programmer": "ThePragmaticProgrammer",
        "Introduction to Algorithms": "IntroductionToAlgorithms",
        "Design Patterns: Elements of Reusable Object-Oriented Software": "DesignPatterns",
        
        # =========================================
        # COOKBOOK (3 books)
        # =========================================
        "The Joy of Cooking": "TheJoyOfCooking",
        "Mastering the Art of French Cooking": "MasteringFrenchCooking",
        "Ottolenghi Simple": "OttolenghiSimple",
        
        # =========================================
        # EDUCATION (3 books)
        # =========================================
        "Pedagogy of the Oppressed": "PedagogyOfTheOppressed",
        "Mindset: The New Psychology of Success": "Mindset",
        "How to Win Friends and Influence People": "HowToWinFriends",
    }

    filename = cover_mapping.get(book_title)

    if filename:
        extensions = [".jpg", ".jpeg", ".png", ".JPG"]

        for ext in extensions:
            cover_path = os.path.join(IMAGE_DIR, filename + ext)
            if os.path.exists(cover_path):
                return cover_path

    return None

def display_book_card(book_title, author, genre, price, show_cover=True):
    """Display a book card with cover image"""
    cover_path = get_book_cover(book_title) if show_cover else None
    col1, col2 = st.columns([1, 3])
    
    with col1:
        if cover_path:
            st.image(cover_path, width=120)
        else:
            st.write("📚")
    
    with col2:
        st.markdown(f"""
        **{book_title}**  
        *{author}*  
        {genre}  
        RM {price}
        """)

# ---------------------------
# 4. HOMEPAGE UI
# ---------------------------
def show_homepage():
    """Display the main homepage with recommendation system"""
    
    # Hero Section
    st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 20px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .book-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid #667eea;
    }
    .recommendation-title {
        font-size: 0.9rem;
        font-weight: bold;
        margin-bottom: 0.2rem;
    }
    .recommendation-author {
        font-size: 0.8rem;
        color: #6c757d;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown('<div class="main-header"><h1>📚 Semantic Book Recommender</h1><p>Discover your next favorite book using AI-powered semantic search</p></div>', unsafe_allow_html=True)
    
    # Use reasoning
    graph = get_active_graph() 
    if graph is None:
        with st.spinner("Loading book catalog..."):
            graph = load_data()
    
    # Create two columns for input
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("##### Please enter a description of a book you like")
        description = st.text_area(
            "",
            placeholder="e.g., A tale of friendship, magic, and adventure...",
            height=50,
            label_visibility="collapsed"
        )

    with col2:
        st.write("##### Select a category")
        categories = ["All", "NonFiction", "Fantasy", "Mystery", "Romance", "YoungAdult", 
                      "Thriller", "History", "Biography", "Technical", "Cookbook", "Education"]
        category = st.selectbox(
            "",
            categories,
            label_visibility="collapsed"
        )
    
    # Recommend button
    if st.button("Recommend Books", type="primary", use_container_width=True):
        if description.strip():
            with st.spinner("Finding your perfect books..."):
                recommendations = get_recommendations_by_description(description, category, graph)
                
                if not recommendations.empty:
                    st.success(f"Found {len(recommendations)} recommendations for you!")
                    
                    # Display recommendations in columns
                    st.subheader("Recommended Books")
                    
                    # Create rows of 3 columns each
                    cols = st.columns(3)
                    for idx, (_, book) in enumerate(recommendations.iterrows()):
                        with cols[idx % 3]:
                            st.markdown(f"""
                            <div class="book-card">
                                <div class="recommendation-title">{book['Title'][:40]}...</div>
                                <div class="recommendation-author">{book['Author']}</div>
                                <div class="recommendation-author">{book['Genre']}</div>
                                <div class="recommendation-author">RM {book['Price (RM)']}</div>
                            </div>
                            """, unsafe_allow_html=True)
                    
                    # Show full table
                    with st.expander("View all recommendations in table"):
                        st.dataframe(recommendations[['Title', 'Author', 'Genre', 'Price (RM)']], use_container_width=True)
                else:
                    st.warning("No recommendations found. Try different keywords!")
        else:
            st.warning("Please enter a description of a book you like!")
    
    # Featured Books Section
    st.markdown("---")
    st.subheader("Best Recommend Books")

    best_recommend = get_top_rated_recommendations(graph)

    if not best_recommend.empty:
        cols = st.columns(4)
        for idx, (_, book) in enumerate(best_recommend.head(4).iterrows()):
            with cols[idx]:
                cover_path = get_book_cover(book['Title'])
                with st.container():
                    if cover_path:
                        st.image(cover_path, width=140)
                    else:
                        st.write("📚")
                    st.markdown(f"""
                    **{book['Title']}**  
                    *{book['Author']}*  
                    RM {book['Price (RM)']}
                    """)
    else:
        st.info("No bestsellers found.")
    
    # Quick Stats
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    
    all_books = get_all_books(graph)
    
    if not all_books.empty and 'Author' in all_books.columns and 'Genre' in all_books.columns:
        unique_authors = all_books['Author'].nunique()
        unique_genres = all_books['Genre'].nunique()
        total_books = len(all_books)
    else:
        unique_authors = 0
        unique_genres = 0
        total_books = 0
        st.warning("Unable to load book statistics. Please check data files.")
    
    top_rated_count = len(best_recommend) if not best_recommend.empty else 0
    
    with col1:
        st.metric("Total Books", total_books)
    with col2:
        st.metric("Authors", unique_authors)
    with col3:
        st.metric("Genres", unique_genres)
    with col4:
        st.metric("Top Rated", top_rated_count)

# ---------------------------
# 5. SEARCH PAGE UI
# ---------------------------
def show_search_page():
    """Display the advanced search page"""
    
    st.title("Advanced Book Search")
    st.markdown("Use the sidebar to search for books by keyword, price, genre or author!")
    
    # Use reasoning
    graph = get_active_graph() 
    if graph is None:
        with st.spinner("Loading book catalog..."):
            graph = load_data()
    
    # Sidebar navigation
    st.sidebar.header("Search Options")
    search_type = st.sidebar.radio(
        "Choose search method:",
        ["Keyword Search", "Price Range", "Browse by Genre", "Browse by Author", "Similar Books"]
    )
    
    # 1. KEYWORD SEARCH
    if search_type == "Keyword Search":
        st.subheader("Search Books by Title, Category or Genre")
        keyword = st.text_input("Enter book title, author name, or genre:", "Harry Potter")
        if keyword:
            df = search_by_keyword(graph, keyword)
            if not df.empty:
                for _, book in df.iterrows():
                    display_book_card(
                        book_title=book['Title'],
                        author=book['Author'],
                        genre=book.get('Genre', 'Unknown'),
                        price=book['Price (RM)'],
                        show_cover=True
                    )
                with st.expander("View as table"):
                    display_df = df[['Title', 'Author', 'Genre', 'Price (RM)']].copy()
                    display_df.index = range(1, len(display_df) + 1)
                    display_df['Price (RM)'] = display_df['Price (RM)'].apply(lambda x: f"{x:.2f}")
                    st.dataframe(display_df, use_container_width=True)
                st.success(f"Found {len(df)} books matching '{keyword}'")
            else:
                st.warning("No books found. Try a different keyword.")
    
    # 2. PRICE FILTER
    elif search_type == "Price Range":
        st.subheader("Filter Books by Price")
        col1, col2 = st.columns(2)
        with col1:
            min_price = st.number_input("Min Price (RM)", min_value=0, value=0, step=5)
        with col2:
            max_price = st.number_input("Max Price (RM)", min_value=0, value=100, step=5)
        
        if st.button("Search", type="primary"):
            df = filter_by_price(graph, min_price, max_price)
            if not df.empty:
                for _, book in df.iterrows():
                    display_book_card(
                        book_title=book['Title'],
                        author=book['Author'],
                        genre=book.get('Genre', 'Unknown'),
                        price=book['Price (RM)'],
                        show_cover=True
                    )
                with st.expander("View as table"):
                    display_df = df[['Title', 'Author', 'Price (RM)']].copy()
                    display_df.index = range(1, len(display_df) + 1)
                    display_df['Price (RM)'] = display_df['Price (RM)'].apply(lambda x: f"{x:.2f}")
                    st.dataframe(display_df, use_container_width=True)
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("Average Price", f"RM{df['Price (RM)'].mean():.2f}")
                with col_b:
                    st.metric("Total Books", len(df))
                with col_c:
                    st.metric("Cheapest Book", f"RM{df['Price (RM)'].min():.2f}")
            else:
                st.warning("No books found in this price range.")
    
    # 3. BROWSE BY GENRE
    elif search_type == "Browse by Genre":
        st.subheader("Browse Books by Genre")
        genres = ["Fantasy", "Mystery", "Romance", "YoungAdult", "Thriller", 
                  "History", "Biography", "Technical", "Cookbook", "Education"]
        genre = st.selectbox("Select a genre:", genres)
        
        stats = get_genre_statistics(graph, genre)
        
        if stats["total_books"] > 0:
            df = get_books_by_genre(graph, genre)
            st.info(f"✅ Found {len(df)} books in {genre}")
            st.markdown("---")
            st.markdown(f"### Genre Summary: {genre}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Books", stats["total_books"])
            with col2:
                st.metric("Authors", len(stats["authors"]))
            
            st.markdown("---")
            
            for _, book in df.iterrows():
                display_book_card(
                    book_title=book['Title'],
                    author=book['Author'],
                    genre=book['Genre'],
                    price=book['Price (RM)'],
                    show_cover=True
                )
            
            with st.expander("View as table"):
                display_df = df[['Title', 'Author', 'Genre', 'Price (RM)']].copy()
                display_df.index = range(1, len(display_df) + 1)
                display_df['Price (RM)'] = display_df['Price (RM)'].apply(lambda x: f"{x:.2f}")
                st.dataframe(display_df, use_container_width=True)
            
        else:
            st.warning(f"No books found in {genre}")

    # 4. BROWSE BY AUTHOR
    elif search_type == "Browse by Author":
        st.subheader("Browse Books by Author")
        authors_list = [
                            # FANTASY
                            "J.K. Rowling",
                            "George R.R. Martin",
                            "J.R.R. Tolkien",
                            # MYSTERY
                            "Dan Brown",
                            "Stieg Larsson",
                            "Thomas Harris",
                            # ROMANCE
                            "Jane Austen",
                            "Charlotte Bronte",
                            "Diana Gabaldon",
                            "Nicholas Sparks",
                            # YOUNG ADULT
                            "Suzanne Collins",
                            "John Green",
                            "Veronica Roth",
                            # THRILLER
                            "Stephen King",
                            "Alex Michaelides",
                            "Gillian Flynn",
                            # HISTORY
                            "Yuval Noah Harari",
                            "Barbara W. Tuchman",
                            "Toby Wilkinson",
                            # BIOGRAPHY
                            "Michelle Obama",
                            "Walter Isaacson",
                            "Anne Frank",
                            "Nelson Mandela",
                            # TECHNICAL
                            "Robert C. Martin",
                            "David Thomas",
                            "Thomas H. Cormen",
                            "Erich Gamma",
                            # COOKBOOK
                            "Irma S. Rombauer",
                            "Julia Child",
                            "Yotam Ottolenghi",
                            # EDUCATION
                            "Paulo Freire",
                            "Carol S. Dweck",
                            "Dale Carnegie",
                        ]
        author_name = st.selectbox("Select an author:", authors_list)
        
        if author_name:
            author_stats = get_author_statistics(graph, author_name)
            
            if author_stats["total_books"] > 0:
                df = author_stats["df"]
                st.info(f"✅ Found {len(df)} books by {author_name}")
                st.markdown("---")
                st.markdown(f"### Author Summary: {author_name}")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Books", author_stats["total_books"])
                with col2:
                    st.metric("Best Recommend Books", author_stats["bestrecommend_count"])
                with col3:
                    st.metric("Genres", ", ".join(author_stats["genres"]) if author_stats["genres"] else "Unknown")
                
                st.markdown("---")
                
                for _, book in df.iterrows():
                    display_book_card(
                        book_title=book['Title'],
                        author=author_name,
                        genre=book['Genre'],
                        price=book['Price (RM)'],
                        show_cover=True
                    )
                
                with st.expander("View as table"):
                    display_df = df[['Title', 'Genre', 'Price (RM)', 'Best Recommend']].copy()
                    display_df.index = range(1, len(display_df) + 1)
                    display_df['Price (RM)'] = display_df['Price (RM)'].apply(lambda x: f"{x:.2f}")
                    st.dataframe(display_df, use_container_width=True)
                                
                if author_stats["genres"]:
                    st.markdown("---")
                    st.markdown("## 🔍 Similar Authors You Might Like")
                    
                    similar_authors = get_similar_authors(
                        graph, 
                        author_name, 
                        set(author_stats["genres"]), 
                        authors_list
                    )
                    
                if similar_authors:
                    for sim_author in similar_authors:
                        with st.expander(f"**{sim_author['name']}** | **Genre:** {', '.join(sorted(sim_author['shared_genres']))}"):
                            
                            sim_author_stats = get_author_statistics(graph, sim_author['name'])
                            sim_df = sim_author_stats["df"]
                            
                            st.markdown("**Featured Books**")
                            
                            for _, book in sim_df.head(3).iterrows():
                                col1, col2 = st.columns([1, 3])
                                with col1:
                                    cover_path = get_book_cover(book['Title'])
                                    st.image(cover_path, width=100)
                                
                                with col2:
                                    st.markdown(f"**{book['Title']}**")
                                    st.markdown(f"*{book['Genre']}*")
                                    st.markdown(f"RM {book['Price (RM)']:.2f}")
                                    if book['Best Recommend'] == "✅":
                                        st.markdown("⭐ Best Recommend")
                                st.markdown("---")
                            
                            if len(sim_df) > 3:
                                with st.expander(f"View all {len(sim_df)} books"):
                                    for _, book in sim_df.iterrows():
                                        col1, col2 = st.columns([1, 3])
                                        with col1:
                                            cover_path = get_book_cover(book['Title'])
                                            st.image(cover_path, width=100)
                                            st.markdown("---")
                                        
                                        with col2:
                                            st.markdown(f"**{book['Title']}**")
                                            st.markdown(f"*{book['Genre']}*")
                                            st.markdown(f"RM {book['Price (RM)']:.2f}")
                                            st.markdown("⭐ Best Recommend")
                                            st.markdown("---")
                else:
                    st.info("No similar authors found based on shared genres.")
            else:
                st.warning(f"No books found by {author_name}")

    # 5. SIMILAR BOOKS
    elif search_type == "Similar Books":
        st.subheader("Find Similar Books")
        st.caption("Based on same author and genre (powered by OWL reasoning)")
        
        all_books = get_all_books(graph)
        if not all_books.empty:
            book_titles = all_books['Title'].tolist()
            book_title = st.selectbox("Select a book you like:", book_titles)
            
            if book_title:
                df = get_similar_books(graph, book_title)
                if not df.empty:
                    st.success(f"Readers who liked '{book_title}' also enjoyed:")
                    for _, book in df.iterrows():
                        display_book_card(
                            book_title=book['Title'],
                            author=book['Author'],
                            genre=book['Genre'],
                            price=book['Price (RM)'], 
                            show_cover=True
                        )
                else:
                    st.info("No similar books found in the catalog yet.")
        else:
            st.warning("No books available.")

# ---------------------------
# 6. MAIN APP
# ---------------------------
# Add these helper functions near the beginning of the file
def verify_file_paths():
    """Verify that all required files exist"""
    issues = []
    
    # Check whether files exist
    if not os.path.exists(DATA_PATH):
        issues.append(f"Data file not found: {DATA_PATH}")
    else:
        st.sidebar.success(f"✅ Data file found: {os.path.basename(DATA_PATH)}")
    
    if not os.path.exists(ONTOLOGY_PATH):
        issues.append(f"Ontology file not found: {ONTOLOGY_PATH}")
    else:
        st.sidebar.success(f"✅ Ontology file found: {os.path.basename(ONTOLOGY_PATH)}")
    
    # Check image directory
    if not os.path.exists(IMAGE_DIR):
        st.sidebar.warning(f"Image directory not found: {IMAGE_DIR}")
    
    return issues

@st.cache_resource
def load_books_graph_only():
    """Load original RDF data only (for testing)"""
    try:
        g = rdflib.Graph()
        
        # Bind namespaces
        g.bind("", "http://www.example.org/bookstore#")
        g.bind("rdf", "http://www.w3.org/1999/02/22-rdf-syntax-ns#")
        g.bind("rdfs", "http://www.w3.org/2000/01/rdf-schema#")
        g.bind("owl", "http://www.w3.org/2002/07/owl#")
        g.bind("xsd", "http://www.w3.org/2001/XMLSchema#")
        
        # Check whether files exist
        if not os.path.exists(DATA_PATH):
            st.error(f"Data file not found at: {DATA_PATH}")
            st.info(f"Current working directory: {os.getcwd()}")
            st.info(f"Looking for: books.ttl")
            return None
        
        if not os.path.exists(ONTOLOGY_PATH):
            st.error(f"Ontology file not found at: {ONTOLOGY_PATH}")
            return None
        
        # Parse files
        g.parse(DATA_PATH, format="turtle")
        g.parse(ONTOLOGY_PATH, format="turtle")
        
        # Verify loaded data
        test_query = list(g.query("""
            PREFIX : <http://www.example.org/bookstore#>
            SELECT ?title WHERE { ?book :title ?title } LIMIT 1
        """))
        
        if not test_query:
            st.error("No books found in the data file")
            st.info("Please check if books.ttl contains valid book data")
            return None
        
        st.success(f"✅ Successfully loaded {len(g)} triples")
        return g
        
    except Exception as e:
        st.error(f"Error loading graph: {e}")
        return None

def main():
    st.set_page_config(page_title="Semantic Book Recommender", layout="wide", page_icon="📚")
    
    # Display file path information (for debugging)
    with st.sidebar.expander("🔧 Debug Info", expanded=False):
        st.write(f"**App path:** `{BASE_DIR}`")
        st.write(f"**Root path:** `{ROOT_DIR}`")
        st.write(f"**Data path:** `{DATA_PATH}`")
        st.write(f"**Ontology path:** `{ONTOLOGY_PATH}`")
        st.write(f"**Image path:** `{IMAGE_DIR}`")
        st.write(f"**Working dir:** `{os.getcwd()}`")
    
    # Verify file paths
    file_issues = verify_file_paths()
    if file_issues:
        for issue in file_issues:
            st.error(issue)
        st.stop()  # Stop execution
    
    # Initialize session state
    if 'initialized' not in st.session_state:
        st.session_state.initialized = False
        st.session_state.load_error = None
    
    # Use a placeholder to display loading progress
    loading_placeholder = st.empty()
    
    if not st.session_state.initialized:
        with loading_placeholder.container():
            st.info("📚 Initializing book catalog and reasoning engine...")
            progress_bar = st.progress(0)
            
            # Step 1: Load RDF data
            progress_bar.progress(20)
            st.info("Loading book data...")
            
            # Load data directly
            g = load_data()
            
            if g is None or len(g) == 0:
                st.error("Failed to load data - graph is empty")
                st.session_state.load_error = "Empty graph"
                return
            
            progress_bar.progress(50)
            st.info("Verifying data...")
            
            # Validate loaded data
            try:
                test_query = list(g.query("""
                    PREFIX : <http://www.example.org/bookstore#>
                    SELECT ?title ?author WHERE { 
                        ?book a :Book .
                        ?book :title ?title .
                        ?book :author ?author .
                    } LIMIT 5
                """))
                
                if not test_query:
                    st.error("No books found in the catalog")
                    st.info("Please check that books.ttl contains valid :Book entries")
                    return
                
                st.success(f"✅ Found {len(test_query)} sample books")
                
            except Exception as e:
                st.error(f"Query verification failed: {e}")
                return
            
            # Step 2: Run reasoning
            progress_bar.progress(70)
            st.info("Running reasoning engine...")
            
            try:
                # Create a copy of the graph for reasoning
                inferred = rdflib.Graph()
                for triple in g:
                    inferred.add(triple)
                
                # Run OWL reasoning (may take some time)
                with st.spinner("Running OWL reasoner (this may take a moment)..."):
                    reasoner = RDFS_OWLRL_Semantics(inferred, axioms=True, daxioms=False, rdfs=True)
                    reasoner.closure()
                    
                    inferred_triples = len(inferred) - len(g)
                    if inferred_triples > 0:
                        st.success(f"✅ Added {inferred_triples} inferred triples")
                    else:
                        st.info("No additional inferences made")
                
                st.session_state.original_graph = g
                st.session_state.inferred_graph = inferred
                st.session_state.reasoning_enabled = True
                
            except Exception as e:
                st.warning(f"Reasoning failed: {e}. Running in basic mode.")
                st.session_state.original_graph = g
                st.session_state.inferred_graph = g
                st.session_state.reasoning_enabled = False
            
            progress_bar.progress(100)
            st.session_state.initialized = True
            
            # Brief delay so users can see the completion message
            import time
            time.sleep(0.5)
            loading_placeholder.empty()
            st.rerun()  # Rerun to display the full interface
            return
    
    # Normal application interface
    # Retrieve active graph
    if st.session_state.get("reasoning_enabled", False):
        graph = st.session_state.get("inferred_graph")
    else:
        graph = st.session_state.get("original_graph")
    
    # Final validation
    if graph is None:
        st.error("Graph is None - initialization failed")
        if st.button("Retry Loading"):
            st.session_state.initialized = False
            st.rerun()
        return
    
    # Display reasoning status
    if st.session_state.get("reasoning_enabled", False):
        st.sidebar.success("🔮 OWL Reasoning: Enabled")
        st.sidebar.info("All searches use reasoning-enhanced semantic relationships")
    else:
        st.sidebar.warning("⚠️ OWL Reasoning: Disabled (basic mode)")
    
    # Custom CSS for better styling
    st.markdown("""
    <style>
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        font-weight: bold;
    }
    .stButton > button:hover {
        transform: scale(1.02);
        transition: 0.3s;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Sidebar navigation between Homepage and Search
    st.sidebar.image("https://img.icons8.com/fluency/96/book.png", width=80)
    st.sidebar.title("Navigation")
    
    page = st.sidebar.radio(
        "Go to:",
        ["Homepage", "Advanced Search"]
    )
    
    if page == "Homepage":
        show_homepage()
    else:
        show_search_page()
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666;'><strong>Semantic Book Store</strong> | Powered by RDFlib, Streamlit | RDF + SPARQL + OWL Inference</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
