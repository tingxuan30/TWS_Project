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
    "magic": ["Fantasy", "magic", "wizard", "sorcerer", "Harry Potter"],
    "real life": ["NonFiction", "nonfiction", "biography", "memoir", "true story"],
    "true story": ["NonFiction", "biography", "memoir"],
    "future": ["Science Fiction", "sci-fi", "speculative", "dystopian"],
    "detective": ["Mystery", "crime", "thriller", "suspense"],
    "coding": ["Technical", "programming", "computer science", "Clean Code"],
    "software": ["Technical", "programming"],
    "history": ["NonFiction", "historical", "Sapiens"],
    "adventure": ["Fantasy", "action", "adventure", "The Hobbit"],
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

def get_bestseller_recommendations(graph):
    """Get books marked as bestsellers"""
    query = """
    PREFIX : <http://www.example.org/bookstore#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    
    SELECT ?title ?author ?price WHERE {
        ?book rdf:type :Bestseller .
        ?book :title ?title .
        ?book :author ?author .
        ?book :price ?price .
    }
    """
    results = []
    
    try:
        for row in graph.query(query):
            results.append({
                "Title": str(row.title),
                "Author": str(row.author),
                "Price (RM)": float(row.price)
            })
        
        if results:
            st.info(f"✅ Found {len(results)} bestsellers")
        
        return pd.DataFrame(results)
        
    except Exception as e:
        st.error(f"Error in get_bestseller_recommendations: {e}")
        return pd.DataFrame(columns=["Title", "Author", "Price (RM)"])

def search_by_keyword(graph, keyword):
    """Search books by title, author, or genre with synonym expansion.
    
    Args:
        graph: RDF graph (rdflib.Graph) containing book data
        keyword: Search term entered by user
        
    Returns:
        pandas.DataFrame with columns: Title, Author, Genre, Price (RM)
    """
    keyword_lower = keyword.lower().strip()
    
    # ============================================
    # STEP 1: Expand search terms using existing SYNONYM_MAP and REVERSE_SYNONYM_MAP
    # ============================================
    expanded_terms = set([keyword_lower])
    
    # Method 1: Direct mapping (keyword matches primary key)
    for k, synonyms in SYNONYM_MAP.items():
        if k in keyword_lower or keyword_lower in k:
            for syn in synonyms:
                expanded_terms.add(syn.lower())
            expanded_terms.add(k.lower())
    
    # Method 2: Reverse mapping using your existing REVERSE_SYNONYM_MAP
    if keyword_lower in REVERSE_SYNONYM_MAP:
        primary_category = REVERSE_SYNONYM_MAP[keyword_lower]
        expanded_terms.add(primary_category.lower())
        if primary_category in SYNONYM_MAP:
            for syn in SYNONYM_MAP[primary_category]:
                expanded_terms.add(syn.lower())
    
    # Method 3: Add capitalized and title-case versions for genre matching
    terms_to_add = []
    for term in expanded_terms:
        terms_to_add.append(term.capitalize())
        terms_to_add.append(term.title())
        # Add without spaces (for multi-word genres)
        if ' ' in term:
            terms_to_add.append(term.replace(' ', ''))
    
    for term in terms_to_add:
        expanded_terms.add(term.lower())
    
    # Remove empty strings and very short terms (length < 2)
    expanded_terms = [t for t in expanded_terms if t and len(t) >= 2]
    
    # If no terms expanded, fall back to simple search
    if not expanded_terms:
        return simple_keyword_search(graph, keyword)
    
    # ============================================
    # STEP 2: Build genre candidates from expanded terms
    # ============================================
    genre_candidates = set()
    for term in expanded_terms:
        # Clean term for genre matching
        clean = term.replace(" ", "").replace("-", "").replace("_", "")
        if clean.isalpha() and len(clean) > 2:
            genre_candidates.add(clean.capitalize())
            genre_candidates.add(clean)
    
    # Add explicit genre mappings from synonym map primary keys
    for primary_key in SYNONYM_MAP.keys():
        primary_lower = primary_key.lower()
        if any(primary_lower in term or term in primary_lower for term in expanded_terms):
            genre_candidates.add(primary_key)
    
    # ============================================
    # STEP 3: Build SPARQL query with proper syntax
    # ============================================
    # Build title/author filter conditions
    title_author_conditions = []
    for term in expanded_terms[:15]:  # Limit to 15 terms for performance
        term_clean = term.lower().replace("'", "\\'").replace('"', '\\"')
        title_author_conditions.append(f'CONTAINS(LCASE(?title), "{term_clean}")')
        title_author_conditions.append(f'CONTAINS(LCASE(?author), "{term_clean}")')
    
    # Remove duplicates
    title_author_conditions = list(set(title_author_conditions))
    
    # Build genre filter conditions
    genre_conditions = []
    for genre in genre_candidates:
        genre_conditions.append(f'?type = <http://www.example.org/bookstore#{genre}>')
    
    # Build the WHERE clause parts (only include non-empty filters)
    where_parts = []
    
    if title_author_conditions:
        title_author_filter = " || ".join(title_author_conditions)
        where_parts.append(f"{{ FILTER({title_author_filter}) }}")
    
    if genre_conditions:
        genre_filter = " || ".join(genre_conditions)
        where_parts.append(f"{{ FILTER({genre_filter}) }}")
    
    # If no filters, fall back to simple search
    if not where_parts:
        return simple_keyword_search(graph, keyword)
    
    # Build the complete query with UNION
    if len(where_parts) == 1:
        where_clause = where_parts[0]
    else:
        where_clause = "{ " + " UNION ".join(where_parts) + " }"
    
    query = f"""
    PREFIX : <http://www.example.org/bookstore#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    
    SELECT DISTINCT ?title ?author ?price ?type WHERE {{
        ?book rdf:type :Book ;
              :title ?title ;
              :author ?author ;
              :price ?price .
        ?book :hasGenre ?type .
        FILTER(?type != :Book && ?type != :Bestseller)
        {where_clause}
    }}
    """
    
    # ============================================
    # STEP 4: Execute query and process results
    # ============================================
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
        
        # Remove duplicates by title
        seen = set()
        unique_results = []
        for r in results:
            if r["Title"] not in seen:
                seen.add(r["Title"])
                unique_results.append(r)
        
        return pd.DataFrame(unique_results)
        
    except Exception as e:
        st.error(f"Synonym search error: {e}. Falling back to simple keyword search.")
        return simple_keyword_search(graph, keyword)

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
        return {
            "total_books": 0,
            "authors": [],
            "bestseller_count": 0
        }
    
    bestseller_query = """
    PREFIX : <http://www.example.org/bookstore#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    
    SELECT ?title WHERE {
        ?book rdf:type :Bestseller .
        ?book :title ?title .
    }
    """
    global_bestsellers = {str(row.title) for row in graph.query(bestseller_query)}
    
    bestseller_count = sum(1 for _, book in df.iterrows() if book['Title'] in global_bestsellers)
    
    return {
        "total_books": len(df),
        "authors": df['Author'].unique().tolist(),
        "bestseller_count": bestseller_count
    }

def get_author_statistics(graph, author_name):
    """Get statistics for a specific author"""
    bestseller_query = """
    PREFIX : <http://www.example.org/bookstore#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    
    SELECT ?title WHERE {
        ?book rdf:type :Bestseller .
        ?book :title ?title .
    }
    """
    global_bestsellers = {str(row.title) for row in graph.query(bestseller_query)}
    
    query = f"""
    PREFIX : <http://www.example.org/bookstore#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    
    SELECT ?title ?price WHERE {{
        ?book :title ?title ;
              :author "{author_name}" ;
              :price ?price .
    }}
    """
    
    results = []
    bestseller_count = 0
    genres_set = set()
    
    for row in graph.query(query):
        book_title = str(row.title)
        
        genre_query = f"""
        PREFIX : <http://www.example.org/bookstore#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        
        SELECT ?type WHERE {{
            ?book :title "{book_title}" .
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
            genres_set.add(genre)
        
        is_bestseller = book_title in global_bestsellers
        if is_bestseller:
            bestseller_count += 1
        
        results.append({
            "Title": book_title,
            "Genre": genre,
            "Price (RM)": float(row.price),
            "Bestseller": "✅" if is_bestseller else "❌"
        })
    
    df = pd.DataFrame(results)
    
    return {
        "df": df,
        "total_books": len(df),
        "bestseller_count": bestseller_count,
        "genres": sorted(list(genres_set))
    }

def get_similar_authors(graph, current_author, current_genres, authors_list):
    """Get similar authors based on shared genres"""
    similar_authors = []
    
    for other_author in authors_list:
        if other_author != current_author:
            other_query = f"""
            PREFIX : <http://www.example.org/bookstore#>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            
            SELECT ?title WHERE {{
                ?book :title ?title ;
                      :author "{other_author}" .
            }}
            """
            
            other_genres = set()
            for other_row in graph.query(other_query):
                other_genre_query = f"""
                PREFIX : <http://www.example.org/bookstore#>
                PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                
                SELECT ?type WHERE {{
                    ?book :title "{str(other_row.title)}" .
                    ?book :hasGenre ?type .
                    FILTER(?type != :Book && ?type != :Bestseller)
                }}
                LIMIT 1
                """
                
                other_genre_results = list(graph.query(other_genre_query))
                if other_genre_results:
                    other_genre_uri = str(other_genre_results[0][0])
                    other_genre = other_genre_uri.split("#")[-1]
                    other_genres.add(other_genre)
            
            shared_genres = current_genres.intersection(other_genres)
            if shared_genres:
                similar_authors.append({
                    "name": other_author,
                    "shared_genres": shared_genres
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
            if inferred_genre and inferred_genre in {"Fantasy", "Mystery", "History", "Biography", "Technical", "NonFiction"}:
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
        "Harry Potter and the Sorcerer's Stone": "HP1",
        "Harry Potter and the Chamber of Secrets": "HP2",
        "Harry Potter and the Prisoner of Azkaban": "HP3",
        "A Game of Thrones": "GT",
        "A Clash of Kings": "CK",
        "The Hobbit": "TheHobbit",
        "The Fellowship of the Ring": "The_Fellowship_of_the_Ring",
        "The Da Vinci Code": "DaVinciCode",
        "Angels & Demons": "Angels&Demons",
        "Gone Girl": "GG",
        "Sapiens: A Brief History of Humankind": "Sapiens",
        "Homo Deus: A Brief History of Tomorrow": "HomoDeus",
        "Becoming": "Becoming",
        "Clean Code: A Handbook of Agile Software Craftsmanship": "CleanCode",
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
        categories = ["All", "NonFiction", "Fantasy", "Mystery", "History", "Biography", "Technical"]
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
    st.subheader("Featured Bestsellers")

    bestsellers = get_bestseller_recommendations(graph)

    if not bestsellers.empty:
        cols = st.columns(4)
        for idx, (_, book) in enumerate(bestsellers.head(4).iterrows()):
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
    
    bestsellers_count = len(bestsellers) if not bestsellers.empty else 0
    
    with col1:
        st.metric("Total Books", total_books)
    with col2:
        st.metric("Authors", unique_authors)
    with col3:
        st.metric("Genres", unique_genres)
    with col4:
        st.metric("Bestsellers", bestsellers_count)

# ---------------------------
# 5. SEARCH PAGE UI
# ---------------------------
def show_search_page():
    """Display the advanced search page"""
    
    st.title("Advanced Book Search")
    st.markdown("Use the sidebar to search for books by keyword, price, genre, author, or browse bestsellers!")
    
    # Use reasoning
    graph = get_active_graph() 
    if graph is None:
        with st.spinner("Loading book catalog..."):
            graph = load_data()
    
    # Sidebar navigation
    st.sidebar.header("Search Options")
    search_type = st.sidebar.radio(
        "Choose search method:",
        ["Keyword Search", "Price Range", "Browse by Genre", "Browse by Author", "Similar Books", "Bestsellers"]
    )
    
    # 1. KEYWORD SEARCH
    if search_type == "Keyword Search":
        st.subheader("Search Books by Title, Author, or Genre")
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
        genres = ["Fantasy", "Mystery", "History", "Biography", "Technical"]
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
        authors_list = ["J.K. Rowling", "George R.R. Martin", "J.R.R. Tolkien", "Dan Brown", "Yuval Noah Harari", "Gillian Flynn", "Michelle Obama", "Robert C. Martin"]
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
                    st.metric("Bestseller Books", author_stats["bestseller_count"])
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
                    display_df = df[['Title', 'Genre', 'Price (RM)', 'Bestseller']].copy()
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
                                    if book['Bestseller'] == "✅":
                                        st.markdown("⭐ Bestseller")
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
                                            st.markdown("⭐ Bestseller")
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
    
    # 6. BESTSELLERS
    elif search_type == "Bestsellers":
        st.subheader("Bestseller Recommendations")
        st.info("These books are classified as Bestsellers using OWL reasoning")
        
        df = get_bestseller_recommendations(graph)
        if not df.empty:
            display_df = df[['Title', 'Author', 'Price (RM)']].copy()
            display_df.index = range(1, len(display_df) + 1)
            display_df['Price (RM)'] = display_df['Price (RM)'].apply(lambda x: f"{x:.2f}")
            st.dataframe(display_df, use_container_width=True)
            st.balloons()
        else:
            st.warning("No bestseller data available.")

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