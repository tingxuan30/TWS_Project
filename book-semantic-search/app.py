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
    """Search books by title, author, or genre with synonym expansion."""
    keyword_lower = keyword.lower().strip()
    
    # Expand keyword using the synonym map
    expanded_terms = [keyword_lower]
    for k, synonyms in SYNONYM_MAP.items():
        if k in keyword_lower or keyword_lower in k:
            expanded_terms.extend(synonyms)
    
    # Also add the keyword itself capitalized (for genre matching)
    expanded_terms.append(keyword_lower.capitalize())
    expanded_terms.append(keyword_lower.title())
    
    # Remove duplicates and empty strings
    expanded_terms = list(set([t for t in expanded_terms if t]))
    
    if not expanded_terms:
        return simple_keyword_search(graph, keyword)
    
    # Build SPARQL FILTER for title/author contains any term
    title_author_filters = " || ".join([
        f'CONTAINS(LCASE(?title), "{term.lower()}")' for term in expanded_terms
    ] + [
        f'CONTAINS(LCASE(?author), "{term.lower()}")' for term in expanded_terms
    ])
    
    # Build FILTER for genre types (exact match on genre URIs)
    # Only include terms that look like genre names (alphanumeric, no spaces)
    genre_candidates = set()
    for term in expanded_terms:
        # Clean term: remove spaces and capitalize properly for genre name
        clean = term.replace(" ", "").replace("-", "")
        if clean.isalpha():
            genre_candidates.add(clean.capitalize())
            genre_candidates.add(clean)
    
    if genre_candidates:
        genre_filters = " || ".join([
            f'?type = <http://www.example.org/bookstore#{g}>' for g in genre_candidates
        ])
    else:
        genre_filters = "false"  # no genre filter, but keep query valid
    
    # Only include title/author filter if non-empty
    if title_author_filters:
        title_author_part = f"{{ FILTER({title_author_filters}) }}"
    else:
        title_author_part = "{{ }}"
    
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
        {{
            {title_author_part}
            UNION
            {{
                FILTER({genre_filters})
            }}
        }}
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
            "Author": str(row.author),
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

def get_recommendations_by_description(description, category, graph):
    """Get book recommendations based on user description and category"""
    all_books = get_all_books(graph)
    
    if all_books.empty:
        return pd.DataFrame()
    
    # Simple recommendation logic based on keywords
    keywords = description.lower().split()
    
    # Score each book based on keyword matches
    scores = []
    for _, book in all_books.iterrows():
        score = 0
        book_text = f"{book['Title']} {book['Author']} {book['Genre']}".lower()
        
        for keyword in keywords:
            if keyword in book_text:
                score += 1
        
        # Category matching
        if category != "All" and category.lower() in book['Genre'].lower():
            score += 3
        
        scores.append(score)
    
    all_books['Score'] = scores
    recommendations = all_books[all_books['Score'] > 0].sort_values('Score', ascending=False).head(15)
    
    return recommendations

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
def main():
    st.set_page_config(page_title="Semantic Book Recommender", layout="wide", page_icon="📚")
    
    # Initialize reasoning graph (run only once)
    reasoning_active = init_reasoning_graph()

    # Display reasoning status in the sidebar
    if reasoning_active:
        st.sidebar.success("🔮 OWL Reasoning: Enabled")
        st.sidebar.info("All searches use reasoning-enhanced semantic relationships")
    else:
        st.sidebar.warning("⚠️ OWL Reasoning: Disabled")

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