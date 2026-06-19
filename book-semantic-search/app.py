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

# ===========================================
# Semantic Book Search and Recommendation UI 
# ===========================================

def css():
    st.markdown("""
    <style>
    /* ===== IMPORT FONTS ===== */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    /* ===== RESET & BASE ===== */
    .stApp {
        background: #f8fafc;
        font-family: 'Inter', sans-serif;
    }
    
    /* ===== HEADER ===== */
    .system-header {
        background: linear-gradient(135deg, #0c0e1a 0%, #1a1c3a 50%, #2d1b4e 100%);
        padding: 3.5rem 3rem;
        border-radius: 20px;
        margin-bottom: 2.5rem;
        position: relative;
        overflow: hidden;
        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
    }
    
    .system-header::before {
        content: '';
        position: absolute;
        top: -50%;
        right: -20%;
        width: 70%;
        height: 200%;
        background: radial-gradient(ellipse at 70% 50%, rgba(99, 102, 241, 0.15) 0%, transparent 60%);
        pointer-events: none;
    }
    
    .system-header::after {
        content: '';
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, #818cf8, #a78bfa, #c084fc, #818cf8);
        background-size: 300% 100%;
        animation: shimmerHeader 4s ease-in-out infinite;
    }
    
    @keyframes shimmerHeader {
        0%, 100% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
    }
    
    .system-header .logo-container {
        display: flex;
        align-items: center;
        gap: 1rem;
        position: relative;
        z-index: 1;
    }
    
    .system-header .logo-icon {
        font-size: 3.5rem;
        filter: drop-shadow(0 0 20px rgba(129, 140, 248, 0.3));
    }
    
    .system-header h1 {
        font-size: 2.8rem;
        font-weight: 800;
        color: white;
        margin: 0;
        letter-spacing: -0.5px;
        position: relative;
        z-index: 1;
    }
    
    .system-header h1 .highlight {
        background: linear-gradient(135deg, #818cf8, #a78bfa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .system-header .tagline {
        color: rgba(255,255,255,0.7);
        font-size: 1.1rem;
        font-weight: 300;
        margin-top: 0.25rem;
        position: relative;
        z-index: 1;
        letter-spacing: 0.3px;
    }
    
    .system-header .badge-container {
        display: flex;
        gap: 1rem;
        margin-top: 1rem;
        position: relative;
        z-index: 1;
        flex-wrap: wrap;
    }
    
    .system-header .badge {
        background: rgba(255,255,255,0.08);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255,255,255,0.1);
        padding: 0.4rem 1.2rem;
        border-radius: 50px;
        font-size: 0.8rem;
        color: rgba(255,255,255,0.8);
        font-weight: 500;
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .system-header .badge .dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #4ade80;
        display: inline-block;
        animation: pulse 2s ease-in-out infinite;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.5; transform: scale(0.8); }
    }
    
    /* ===== SEARCH SECTION ===== */
    .search-section {
        background: white;
        padding: 2.5rem;
        border-radius: 16px;
        box-shadow: 0 4px 24px rgba(0,0,0,0.06);
        margin-bottom: 2.5rem;
        border: 1px solid rgba(0,0,0,0.04);
    }
    
    .search-section .section-label {
        font-weight: 600;
        color: #1a1a2e;
        font-size: 0.95rem;
        margin-bottom: 0.75rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .search-section .section-label .icon {
        font-size: 1.2rem;
    }
    
    /* ===== RESULTS GRID ===== */
    .results-container {
        margin-top: 1.5rem;
    }
    
    .results-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 1.5rem;
        padding-bottom: 0.75rem;
        border-bottom: 2px solid #f0f4ff;
    }
    
    .results-header h3 {
        font-size: 1.3rem;
        font-weight: 700;
        color: #1a1a2e;
        margin: 0;
    }
    
    .results-header .count-badge {
        background: #eef2ff;
        color: #4f46e5;
        padding: 0.3rem 1rem;
        border-radius: 50px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    
    /* ===== BOOK CARDS - GRID LAYOUT ===== */
    .book-grid {
        display: grid;
        grid-template-columns: repeat(6, 1fr);
        gap: 1rem;
        margin: 1.5rem 0;
    }

    .book-card {
        background: white;
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 2px 12px rgba(0,0,0,0.04);
        border: 1px solid rgba(0,0,0,0.04);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
        display: flex;
        flex-direction: column;
        height: 100%;
        min-height: 200px;
    }

    .book-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        bottom: 0;
        width: 4px;
        background: linear-gradient(180deg, #818cf8, #a78bfa);
        border-radius: 4px 0 0 4px;
        opacity: 0;
        transition: opacity 0.3s ease;
    }

    .book-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 40px rgba(99, 102, 241, 0.12);
        border-color: rgba(129, 140, 248, 0.2);
    }

    .book-card:hover::before {
        opacity: 1;
    }

    .book-card .book-top {
        display: flex;
        align-items: flex-start;
        gap: 0.75rem;
        margin-bottom: 0.5rem;
    }

    .book-card .book-info {
        flex: 1;
        min-width: 0;
        display: flex;
        flex-direction: column;
    }

    .book-card .book-title {
        font-weight: 600;
        color: #1a1a2e;
        font-size: 0.85rem;
        line-height: 1.3;
        margin-bottom: 0.1rem;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        min-height: 2.2rem;
    }

    .book-card .book-author {
        color: #6b7280;
        font-size: 0.75rem;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .book-card .book-meta {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        flex-wrap: wrap;
        margin-top: auto;
        padding-top: 0.5rem;
        border-top: 1px solid #f3f4f6;
    }

    .book-card .genre-tag {
        display: inline-block;
        background: #eef2ff;
        color: #4f46e5;
        font-size: 0.6rem;
        padding: 0.15rem 0.7rem;
        border-radius: 50px;
        font-weight: 600;
        white-space: nowrap;
    }

    .book-card .price-tag {
        font-weight: 700;
        color: #1a1a2e;
        font-size: 0.9rem;
        margin-left: auto;
        white-space: nowrap;
    }

    .book-card .price-tag .currency {
        font-size: 0.7rem;
        color: #6b7280;
        font-weight: 400;
    }
    
    /* ===== STAT CARDS ===== */
    .stat-card {
        background: white;
        padding: 1.75rem 1.5rem;
        border-radius: 14px;
        text-align: center;
        box-shadow: 0 2px 12px rgba(0,0,0,0.04);
        border: 1px solid rgba(0,0,0,0.04);
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    
    .stat-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, #818cf8, #a78bfa);
        opacity: 0;
        transition: opacity 0.3s ease;
    }
    
    .stat-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 40px rgba(0,0,0,0.08);
    }
    
    .stat-card:hover::before {
        opacity: 1;
    }
    
    .stat-card .stat-number {
        font-size: 2.4rem;
        font-weight: 800;
        color: #1a1a2e;
        display: block;
        line-height: 1.2;
    }
    
    .stat-card .stat-number .accent {
        color: #4f46e5;
    }
    
    .stat-card .stat-label {
        font-size: 0.85rem;
        color: #6b7280;
        font-weight: 500;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        margin-top: 0.25rem;
    }
    
    /* ===== SECTION HEADERS ===== */
    .section-header-premium {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1a1a2e;
        margin: 2.5rem 0 1.5rem 0;
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }
    
    .section-header-premium .highlight {
        color: #4f46e5;
    }
    
    .section-header-premium .line {
        flex: 1;
        height: 2px;
        background: linear-gradient(90deg, #e5e7eb, transparent);
        margin-left: 1rem;
    }
    
    /* ===== BUTTONS ===== */
    .btn-premium {
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
        color: white;
        border: none;
        padding: 0.75rem 2.5rem;
        border-radius: 10px;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s ease;
        width: 100%;
        box-shadow: 0 4px 16px rgba(79, 70, 229, 0.25);
    }
    
    .btn-premium:hover {
        transform: scale(1.02);
        box-shadow: 0 8px 32px rgba(79, 70, 229, 0.35);
    }
    
    .btn-premium:active {
        transform: scale(0.98);
    }
    
    /* ===== TABS ===== */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        background: white;
        padding: 0.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.04);
        border: 1px solid rgba(0,0,0,0.04);
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 0.5rem 1.25rem;
        font-weight: 500;
        color: #6b7280;
        transition: all 0.3s ease;
    }
    
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
        color: white;
        box-shadow: 0 4px 16px rgba(79, 70, 229, 0.25);
    }
    
    .stTabs [data-baseweb="tab"]:hover:not([aria-selected="true"]) {
        background: #f3f4f6;
        color: #1a1a2e;
    }
    
    /* ===== FOOTER ===== */
    .store-footer {
        text-align: center;
        padding: 2.5rem 2rem;
        margin-top: 3rem;
        border-top: 1px solid rgba(0,0,0,0.06);
        color: #6b7280;
    }
    
    .store-footer .brand {
        font-weight: 700;
        color: #1a1a2e;
    }
    
    .store-footer .brand .accent {
        color: #4f46e5;
    }
    
    .store-footer .footer-links {
        display: flex;
        justify-content: center;
        gap: 2rem;
        margin-top: 0.75rem;
        flex-wrap: wrap;
    }
    
    .store-footer .footer-links span {
        font-size: 0.85rem;
        color: #9ca3af;
    }
    
    .store-footer .footer-links .link {
        color: #4f46e5;
        text-decoration: none;
        font-weight: 500;
        font-size: 0.85rem;
    }
    
    .store-footer .footer-links .link:hover {
        color: #7c3aed;
    }
    
    /* ===== SIDEBAR ===== */
    .css-1d391kg, .css-1aumxhk {
        background: white;
        border-right: 1px solid rgba(0,0,0,0.04);
    }
    
    .sidebar-brand {
        text-align: center;
        padding: 1.5rem 0 1rem 0;
    }
    
    .sidebar-brand .icon {
        font-size: 3rem;
    }
    
    .sidebar-brand h3 {
        color: #1a1a2e;
        font-weight: 700;
        margin: 0.25rem 0 0 0;
    }
    
    .sidebar-brand p {
        color: #6b7280;
        font-size: 0.85rem;
        margin: 0;
    }
    
    /* ===== RESPONSIVE ===== */
    @media (max-width: 768px) {
        .system-header h1 {
            font-size: 1.8rem;
        }
        .system-header {
            padding: 2rem 1.5rem;
        }
        .search-section {
            padding: 1.5rem;
        }
        .book-grid {
            grid-template-columns: 1fr;
        }
    }
    
    @media (min-width: 769px) and (max-width: 1024px) {
        .book-grid {
            grid-template-columns: repeat(2, 1fr);
        }
    }
    
    /* ===== SCROLLBAR ===== */
    ::-webkit-scrollbar {
        width: 8px;
    }
    ::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 10px;
    }
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, #818cf8, #a78bfa);
        border-radius: 10px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(180deg, #6366f1, #8b5cf6);
    }
    </style>
    """, unsafe_allow_html=True)

# ====================================================
# This is the synonym dictionary
# ====================================================
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

# ====================================================
# Build reverse synonym lookup (e.g., "wizard" <-> "magic")
# ====================================================
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

# ====================================================
# Load RDF Data
# ====================================================
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

# ====================================================
# Reasoning with RDFS_OWLRL_Semantics
# ====================================================
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
    
# ====================================================
# SPARQL Query Fucntions
# ====================================================

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
            return df
        
    except Exception as e:
        st.error(f"Error in get_all_books: {e}")
        return pd.DataFrame(columns=["Title", "Author", "Genre", "Price (RM)"])
    
# ====================================================
# Other Funtions
# ====================================================

# ========================= Get the Top Rated Books =========================
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

# ========================= Search by Keyword =========================
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
        if keyword_lower == term or term in keyword_lower:
            detected_category = "NonFiction"
            break
    
    # If not NonFiction, check for Fiction
    if not detected_category:
        fiction_terms = ["fiction", "fictional", "novel", "story", "tale"]
        for term in fiction_terms:
            if keyword_lower == term:
                detected_category = "Fiction"
                break
    
    # If still not detected, check for category keywords with word boundaries
    if not detected_category:
        # Check if the keyword is a single word that matches a category
        if keyword_lower == "fiction":
            detected_category = "Fiction"
        elif keyword_lower in ["nonfiction", "non-fiction", "non fiction"]:
            detected_category = "NonFiction"
    
    # IMPORTANT: Only proceed if a category was detected
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
            
            if unique_results:
                st.success(f"📚 Found {len(unique_results)} books in category: {detected_category}")
            else:
                st.info(f"No books found in category: {detected_category}")
            return pd.DataFrame(unique_results)
            
        except Exception as e:
            st.error(f"Category search error: {e}")
            return simple_keyword_search(graph, keyword_original)
    
    # ============================================
    # STEP 4: Fallback - Title/Author Search
    # ============================================
    return simple_keyword_search(graph, keyword_original)

# ========================= Simple Keyword Search =========================
def simple_keyword_search(graph, keyword):
    """Fallback: keyword search (title/author) with genre lookup."""
    keyword_clean = keyword.strip().replace("'", "\\'").replace('"', '\\"')
    query = f"""
    PREFIX : <http://www.example.org/bookstore#>
    SELECT ?title ?author ?price WHERE {{
        ?book :title ?title ;
              :author ?author ;
              :price ?price .
        FILTER(CONTAINS(LCASE(?title), LCASE("{keyword_clean}")) || 
               CONTAINS(LCASE(?author), LCASE("{keyword_clean}")))
    }}
    """
    results = []
    try:
        for row in graph.query(query):
            # Look up the genre for this book
            genre_query = f"""
            PREFIX : <http://www.example.org/bookstore#>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            
            SELECT ?type WHERE {{
                ?book :title "{str(row.title)}" .
                ?book :hasGenre ?type .
                FILTER(?type != :Book && ?type != :Bestseller && ?type != :BestRecommend)
            }}
            LIMIT 1
            """
            
            genre = "Unknown"
            try:
                genre_results = list(graph.query(genre_query))
                if genre_results:
                    genre_uri = str(genre_results[0][0])
                    genre = genre_uri.split("#")[-1] if "#" in genre_uri else "Unknown"
            except:
                pass
            
            results.append({
                "Title": str(row.title),
                "Author": str(row.author),
                "Genre": genre,
                "Price (RM)": float(row.price)
            })
        
        if not results:
            st.info("No books found matching your search.")
        return pd.DataFrame(results)
        
    except Exception as e:
        st.error(f"Fallback search failed: {e}")
        return pd.DataFrame(columns=["Title", "Author", "Genre", "Price (RM)"])

# ========================= Filter by Price =========================
def filter_by_price(graph, min_price, max_price):
    """Filter books within price range"""
    query = f"""
    PREFIX : <http://www.example.org/bookstore#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    
    SELECT ?title ?author ?price ?genre WHERE {{
        ?book rdf:type :Book ;
              :title ?title ;
              :author ?author ;
              :price ?price .
        OPTIONAL {{ ?book :hasGenre ?genre . }}
        FILTER(?price >= {min_price} && ?price <= {max_price})
    }}
    ORDER BY ?price
    """
    results = []
    try:
        for row in graph.query(query):
            genre = "Unknown"
            if row.genre:
                genre_uri = str(row.genre)
                if "#" in genre_uri:
                    genre = genre_uri.split("#")[-1]
                    if genre in ["Book", "Bestseller", "BestRecommend"]:
                        genre = "Unknown"
            
            results.append({
                "Title": str(row.title),
                "Author": str(row.author),
                "Genre": genre,
                "Price (RM)": float(row.price)
            })
    except Exception as e:
        st.error(f"Error in filter_by_price: {e}")
        return pd.DataFrame(columns=["Title", "Author", "Genre", "Price (RM)"])
    
    return pd.DataFrame(results)

# ========================= Get the Similar Books =========================
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

    return pd.DataFrame(unique_results)

# ========================= Get the Genre Statistics =========================
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
# ========================= Get the Author Statistics =========================
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

# ========================= Get the Author and Genre =========================
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

# ========================= Get the Similar Authors =========================
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

# ========================= Get the Books by Genre =========================
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

# ========================= Get the Books by Author =========================
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

# ========================= Simple Keyword Recommendation =========================
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

# ========================= Extract the Genres from Description =========================
def extract_genres_from_description(description):
    """
    Extract ALL genres from the description by checking each word against the synonym map.
    """
    desc_lower = description.lower()
    target_genres = set()

    # Method 1: Check each word in the description
    words = desc_lower.split()

    for word in words:
        # Check if this word is in the reverse synonym map
        if word in REVERSE_SYNONYM_MAP:
            primary = REVERSE_SYNONYM_MAP[word]
            
            # Map the primary key to the actual genre name
            genre_mapping = {
                "Fantasy": "Fantasy",
                "Mystery": "Mystery", 
                "Romance": "Romance",
                "Young Adult": "YoungAdult",
                "Thriller": "Thriller",
                "History": "History",
                "Biography": "Biography",
                "Technical": "Technical",
                "Cookbook": "Cookbook",
                "Education": "Education"
            }
            
            if primary in genre_mapping:
                target_genres.add(genre_mapping[primary])

    # Method 2: Check multi-word phrases
    multi_word_phrases = {
        "young adult": "YoungAdult",
        "world war": "History",
        "life story": "Biography",
        "soul mate": "Romance",
        "clean code": "Technical",
        "machine learning": "Technical",
        "data structure": "Technical"
    }
    
    for phrase, genre in multi_word_phrases.items():
        if phrase in desc_lower:
            target_genres.add(genre)
    
    # Method 3: Directly examine all the genre keywords in the entire description
    for genre_name, synonyms in SYNONYM_MAP.items():
        for syn in synonyms:
            if syn.lower() in desc_lower:
                # Standardize the genre names
                if genre_name == "Young Adult":
                    target_genres.add("YoungAdult")
                else:
                    target_genres.add(genre_name)
                break  # Once a synonym is found, exit the inner loop
    
    return target_genres

# ========================= Get the Recommendation by Description =========================
def get_recommendations_by_description(description, category, graph):
    """
    OWL reasoning based book recommendation.
    Extracts genres from description, uses inferred types, and scores books.
    """
    if not st.session_state.get("reasoning_enabled", False):
        return simple_keyword_recommendation(description, category, graph)

    desc_lower = description.lower()

    # Extract target genres from the description
    target_genres = extract_genres_from_description(description)
    
    # If user explicitly selected a category, add it
    if category != "All":
        target_genres.add(category)

    # If no genres detected, use fallback
    if not target_genres:
        st.info("No specific genres detected. Showing general recommendations.")
        return simple_keyword_recommendation(description, category, graph)

    # Extract meaningful keywords (skip stop words)
    stopwords = {"a", "an", "the", "and", "of", "to", "for", "with", "on", "at", "by",
                 "is", "are", "was", "were", "i", "want", "about", "book", "books",
                 "like", "read", "reading", "story", "tale", "love", "enjoy", "looking"}
    words = desc_lower.split()
    keywords = {w for w in words if w not in stopwords and len(w) > 2}

    # SPARQL query to get all books with their inferred genres
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
                    "History", "Biography", "Technical", "Cookbook", "Education"
                }:
                results.append({
                    "Title": str(row.title),
                    "Author": str(row.author),
                    "Price (RM)": float(row.price),
                    "Genre": inferred_genre
                })

        # Remove duplicates
        seen = set()
        unique_results = []
        for book in results:
            if book["Title"] not in seen:
                seen.add(book["Title"])
                unique_results.append(book)
        results = unique_results

        if not results:
            return pd.DataFrame()

        # Score each book
        scored_books = []
        for book in results:
            score = 0
            book_text = f"{book['Title']} {book['Author']}".lower()

            # Genre match - give points for EACH matching genre
            if book['Genre'] in target_genres:
                score += 30
                
                # Bonus: If multiple genres match, give extra points
                matching_genres = len(target_genres.intersection({book['Genre']}))
                if matching_genres > 0:
                    score += 10 * matching_genres

            # Keyword match in title/author
            for kw in keywords:
                if kw in book_text:
                    score += 5

            # Category override bonus
            if category != "All" and category == book['Genre']:
                score += 20

            # Additional bonus for books that match the most requested genres
            if len(target_genres) > 1 and book['Genre'] in target_genres:
                score += 15

            if score > 0:
                scored_books.append((score, book))

        # Sort by score descending
        scored_books.sort(key=lambda x: x[0], reverse=True)
        
        # If multiple genres requested, ensure each genre has representation
        if len(target_genres) > 1:
            # Group by genre
            genre_groups = {}
            for score, book in scored_books:
                if book['Genre'] not in genre_groups:
                    genre_groups[book['Genre']] = []
                genre_groups[book['Genre']].append((score, book))
            
            # Take books from each genre
            final_books = []
            books_per_genre = max(2, 15 // len(target_genres))
            
            for genre in sorted(target_genres):
                if genre in genre_groups:
                    take_count = min(books_per_genre, len(genre_groups[genre]))
                    final_books.extend(genre_groups[genre][:take_count])
            
            # Fill remaining slots
            if len(final_books) < 15:
                remaining = []
                for genre, books in genre_groups.items():
                    remaining.extend([item for item in books if item not in final_books])
                final_books.extend(remaining[:15 - len(final_books)])
            
            # Sort by score
            final_books.sort(key=lambda x: x[0], reverse=True)
            recommendations = [book for _, book in final_books[:15]]
        else:
            recommendations = [book for _, book in scored_books[:15]]

        if recommendations:
            df = pd.DataFrame(recommendations)
            return df
        else:
            return pd.DataFrame()

    except Exception as e:
        st.error(f"Reasoning recommendation failed: {e}. Falling back to simple mode.")
        return simple_keyword_recommendation(description, category, graph)

# ========================= Get the Books Cover Image =========================
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

# ========================= Display the Book Card =========================
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
        RM {price:.2f}
        """)

# ========================= Homepage =========================
def show_homepage():
    """Display the main homepage with system UI"""
    
    css()
    
    # === Main Semantic Recommendation ===
    graph = get_active_graph() 
    if graph is None:
        with st.spinner("Loading book catalog..."):
            graph = load_data()
    
    st.markdown("""
    <div class="system-header">
        <div class="logo-container">
            <div>
                <h1>Semantic Web-Based <span class="highlight"> Book Search and Recommendation System</span></h1>
                <p class="tagline">Discover your next favorite read through semantic web-based search and recommendation</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Search Book Section
    col1, col2 = st.columns([2.5, 1.5])
    
    with col1:
        st.markdown('<div class="section-label">What kind of book are you looking for?</div>', unsafe_allow_html=True)
        description = st.text_area(
            "",
            placeholder="Describe your ideal book... e.g., A magical adventure with wizards and mythical creatures",
            height=60,
            label_visibility="collapsed",
            key="search_input"
        )

    # Select Genre Section
    with col2:
        st.markdown('<div class="section-label">Filter by genre</div>', unsafe_allow_html=True)
        categories = ["All", "NonFiction", "Fantasy", "Mystery", "Romance", "YoungAdult", 
                    "Thriller", "History", "Biography", "Technical", "Cookbook", "Education"]
        category = st.selectbox(
            "",
            categories,
            label_visibility="collapsed",
            key="category_select"
        )

    # Centered button
    col_btn1, col_btn2, col_btn3 = st.columns([1, 50, 1])
    with col_btn2:
        if st.button("Find Books", type="primary", use_container_width=True, key="search_btn"):
            if description.strip():
                with st.spinner("Analyzing your preferences with semantic web-based search..."):
                    recommendations = get_recommendations_by_description(description, category, graph)
                    
                    if not recommendations.empty:
                        # Results header with count
                        st.markdown(f"""
                        <div class="results-header">
                            <h3>Your Recommendations</h3>
                            <span class="count-badge">{len(recommendations)} books found</span>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        cols = st.columns(6)
                        
                        for idx, (_, book) in enumerate(recommendations.iterrows()):
                            with cols[idx % 6]: 
                                cover_path = get_book_cover(book['Title'])
                                
                                if cover_path and os.path.exists(cover_path):
                                    st.image(cover_path, width=120)
                                else:
                                    st.markdown('<div style="text-align: center; font-size: 3rem;">📚</div>', unsafe_allow_html=True)

                                st.markdown(f"""
                                <div style="padding: 0.5rem 0;">
                                    <div style="font-weight: 600; color: #1a1a2e; font-size: 0.85rem; line-height: 1.3; min-height: 2.4rem;">{book['Title']}</div>
                                    <div style="color: #6b7280; font-size: 0.75rem;">by {book['Author']}</div>
                                    <div style="margin-top: 0.3rem;">
                                        <span style="display: inline-block; background: #eef2ff; color: #4f46e5; font-size: 0.6rem; padding: 0.1rem 0.6rem; border-radius: 50px; font-weight: 600;">{book['Genre']}</span>
                                        <span style="float: right; font-weight: 700; color: #1a1a2e; font-size: 0.9rem;">RM {book['Price (RM)']:.2f}</span>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)

                        with st.expander("View Complete List as Table"):
                            st.dataframe(
                                recommendations[['Title', 'Author', 'Genre', 'Price (RM)']], 
                                use_container_width=True,
                                hide_index=True
                            )
                    else:
                        st.warning("No recommendations found. Please try different keywords.")
            else:
                st.warning("Please describe the kind of book you're looking for.")

    st.markdown('</div>', unsafe_allow_html=True)
    
    # === Best Recommend Books Section ===
    st.markdown("""
    <div class="section-header-premium">
        <span class="highlight">Best Recommend</span> Books
        <span class="line"></span>
    </div>
    """, unsafe_allow_html=True)

    best_recommend = get_top_rated_recommendations(graph)

    if not best_recommend.empty:
        show_count = 6  
        show_all = st.checkbox("Show All Books", value=False)
        
        if show_all:
            display_books = best_recommend
        else:
            display_books = best_recommend.head(show_count)
            if len(best_recommend) > show_count:
                st.caption(f"Showing first {show_count} books. Check the box above to view all {len(best_recommend)} books.")
        
        cols = st.columns(6) 
        for idx, (_, book) in enumerate(display_books.iterrows()):
            with cols[idx % 6]: 
                cover_path = get_book_cover(book['Title'])
                with st.container():
                    if cover_path and os.path.exists(cover_path):
                        st.image(cover_path, width=120)
                    else:
                        st.markdown('<div style="text-align: center; font-size: 3rem; margin-bottom: 0.5rem;">📚</div>', unsafe_allow_html=True)
                    
                    st.markdown(f"""
                    <div class="featured-item" style="padding-top: 0.5rem;">
                        <div class="book-title" style="font-size: 0.8rem;">{book['Title'][:25]}{'...' if len(book['Title']) > 25 else ''}</div>
                        <div class="book-author" style="font-size: 0.7rem;">{book['Author']}</div>
                        <div class="book-price" style="font-size: 0.85rem;">RM {book['Price (RM)']:.2f}</div>
                    </div>
                    """, unsafe_allow_html=True)
        
        with st.expander("View as Table"):
            display_df = best_recommend[['Title', 'Author', 'Price (RM)']].copy()
            display_df.index = range(1, len(display_df) + 1)
            display_df['Price (RM)'] = display_df['Price (RM)'].apply(lambda x: f"{x:.2f}")
            st.dataframe(display_df, use_container_width=True, height=400)
    else:
        st.info("No books with rating ≥ 4.5 found.")
    
    # === Statistics Section ===
    st.markdown("""
    <div class="section-header-premium">
        <span class="highlight">System</span> Statistics
        <span class="line"></span>
    </div>
    """, unsafe_allow_html=True)
    
    all_books = get_all_books(graph)
    
    if not all_books.empty and 'Author' in all_books.columns and 'Genre' in all_books.columns:
        unique_authors = all_books['Author'].nunique()
        unique_genres = all_books['Genre'].nunique()
        total_books = len(all_books)
    else:
        unique_authors = 0
        unique_genres = 0
        total_books = 0
    
    top_rated_count = len(best_recommend) if not best_recommend.empty else 0
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <span class="stat-number">{total_books}</span>
            <span class="stat-label">Total Books</span>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="stat-card">
            <span class="stat-number"><span class="accent">{unique_authors}</span></span>
            <span class="stat-label">Authors</span>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="stat-card">
            <span class="stat-number">{unique_genres}</span>
            <span class="stat-label">Genres</span>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="stat-card">
            <span class="stat-number"><span class="accent">{top_rated_count}</span></span>
            <span class="stat-label">Top Rated</span>
        </div>
        """, unsafe_allow_html=True)

def show_search_content(graph):
    """Display advanced search with UI"""
    
    st.markdown("""
    <div class="section-header-premium">
        <span class="highlight">Advanced</span> Search
        <span class="line"></span>
    </div>
    <p style="color: #6b7280; margin-bottom: 1.5rem;">Explore our curated collection with powerful search tools</p>
    """, unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Keyword", 
        "Price Range", 
        "Genre", 
        "Author", 
        "Similar Books"
    ])
    
    # === Search by Keyword ===
    with tab1:
        st.subheader("Keyword Search")
        keyword = st.text_input("Enter a book title, author name, or genre:", "Harry Potter", key="keyword_search")
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
                with st.expander("View as Table"):
                    display_df = df[['Title', 'Author', 'Genre', 'Price (RM)']].copy()
                    display_df.index = range(1, len(display_df) + 1)
                    display_df['Price (RM)'] = display_df['Price (RM)'].apply(lambda x: f"{x:.2f}")
                    st.dataframe(display_df, use_container_width=True)
            else:
                st.warning("No books found. Try a different keyword.")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # === Price Range ===
    with tab2:
        st.subheader("Filter by Price")
        col1, col2 = st.columns(2)
        with col1:
            min_price = st.number_input("Minimum Price (RM)", min_value=0, value=0, step=5, key="min_price")
        with col2:
            max_price = st.number_input("Maximum Price (RM)", min_value=0, value=100, step=5, key="max_price")
        
        if st.button("Search by Price", type="primary", key="price_search"):
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
                with st.expander("View as Table"):
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
                    st.metric("Cheapest", f"RM{df['Price (RM)'].min():.2f}")
            else:
                st.warning("No books found in this price range.")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # === Browse by Genre ===
    with tab3:
        st.subheader("Browse by Genre")
        genres = ["Fantasy", "Mystery", "Romance", "YoungAdult", "Thriller", 
                  "History", "Biography", "Technical", "Cookbook", "Education"]
        genres = sorted(genres)
        genre = st.selectbox("Select a genre:", genres, key="genre_select")
        
        stats = get_genre_statistics(graph, genre)
        
        if stats["total_books"] > 0:
            df = get_books_by_genre(graph, genre)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Books", stats["total_books"])
            with col2:
                st.metric("Authors", len(stats["authors"]))
            with col3:
                st.metric("Top Rated", stats["bestrecommend_count"])
            
            st.markdown("---")
            
            for _, book in df.iterrows():
                display_book_card(
                    book_title=book['Title'],
                    author=book['Author'],
                    genre=book['Genre'],
                    price=book['Price (RM)'],
                    show_cover=True
                )
            
            with st.expander("View as Table"):
                display_df = df[['Title', 'Author', 'Genre', 'Price (RM)']].copy()
                display_df.index = range(1, len(display_df) + 1)
                display_df['Price (RM)'] = display_df['Price (RM)'].apply(lambda x: f"{x:.2f}")
                st.dataframe(display_df, use_container_width=True)
            
        else:
            st.warning(f"No books found in {genre}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # === Browse by Author ===
    with tab4:
        st.subheader("Browse by Author")
        authors_list = [
            "J.K. Rowling", "George R.R. Martin", "J.R.R. Tolkien",
            "Dan Brown", "Stieg Larsson", "Thomas Harris",
            "Jane Austen", "Charlotte Bronte", "Diana Gabaldon", "Nicholas Sparks",
            "Suzanne Collins", "John Green", "Veronica Roth",
            "Stephen King", "Alex Michaelides", "Gillian Flynn",
            "Yuval Noah Harari", "Barbara W. Tuchman", "Toby Wilkinson",
            "Michelle Obama", "Walter Isaacson", "Anne Frank", "Nelson Mandela",
            "Robert C. Martin", "David Thomas", "Thomas H. Cormen", "Erich Gamma",
            "Irma S. Rombauer", "Julia Child", "Yotam Ottolenghi",
            "Paulo Freire", "Carol S. Dweck", "Dale Carnegie",
        ]
        authors_list = sorted(authors_list)
        author_name = st.selectbox("Select an author:", authors_list, key="author_select")
        
        if author_name:
            author_stats = get_author_statistics(graph, author_name)
            
            if author_stats["total_books"] > 0:
                df = author_stats["df"]
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Books", author_stats["total_books"])
                with col2:
                    st.metric("Top Rated", author_stats["bestrecommend_count"])
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
                
                with st.expander("View as Table"):
                    display_df = df[['Title', 'Genre', 'Price (RM)', 'Best Recommend']].copy()
                    display_df.index = range(1, len(display_df) + 1)
                    display_df['Price (RM)'] = display_df['Price (RM)'].apply(lambda x: f"{x:.2f}")
                    st.dataframe(display_df, use_container_width=True)
                                
                if author_stats["genres"]:
                    st.markdown("---")
                    st.markdown("### Similar Authors You Might Like")
                    
                    similar_authors = get_similar_authors(
                        graph, 
                        author_name, 
                        set(author_stats["genres"]), 
                        authors_list
                    )
                    
                    if similar_authors:
                        for sim_author in similar_authors:
                            with st.expander(f"**{sim_author['name']}** — {', '.join(sorted(sim_author['shared_genres']))}"):
                                
                                sim_author_stats = get_author_statistics(graph, sim_author['name'])
                                sim_df = sim_author_stats["df"]
                                
                                st.markdown("**Featured Books**")
                                
                                for _, book in sim_df.head(3).iterrows():
                                    col1, col2 = st.columns([1, 3])
                                    with col1:
                                        cover_path = get_book_cover(book['Title'])
                                        if cover_path:
                                            st.image(cover_path, width=100)
                                        else:
                                            st.write("📚")
                                    
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
                                                if cover_path:
                                                    st.image(cover_path, width=100)
                                                else:
                                                    st.write("📚")
                                            
                                            with col2:
                                                st.markdown(f"**{book['Title']}**")
                                                st.markdown(f"*{book['Genre']}*")
                                                st.markdown(f"RM {book['Price (RM)']:.2f}")
                                                if book['Best Recommend'] == "✅":
                                                    st.markdown("⭐ Best Recommend")
                                            st.markdown("---")
                    else:
                        st.info("No similar authors found based on shared genres.")
            else:
                st.warning(f"No books found by {author_name}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # === Similar Books ===
    with tab5:
        st.subheader("Find Similar Books")
        st.caption("Based on same author and genre (powered by OWL reasoning)")
        
        all_books = get_all_books(graph)
        if not all_books.empty:
            book_titles = all_books['Title'].tolist()
            book_titles = sorted(book_titles)
            book_title = st.selectbox("Select a book you like:", book_titles, key="similar_book_select")
            
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
        st.markdown('</div>', unsafe_allow_html=True)

# ===========================================
# Main Application 
# ===========================================
def verify_file_paths():
    """Verify that all required files exist"""
    issues = []
    
    if not os.path.exists(DATA_PATH):
        issues.append(f"Data file not found: {DATA_PATH}")
    else:
        st.sidebar.success(f"✅ Data file found: {os.path.basename(DATA_PATH)}")
    
    if not os.path.exists(ONTOLOGY_PATH):
        issues.append(f"Ontology file not found: {ONTOLOGY_PATH}")
    else:
        st.sidebar.success(f"✅ Ontology file found: {os.path.basename(ONTOLOGY_PATH)}")
    
    if not os.path.exists(IMAGE_DIR):
        st.sidebar.warning(f"Image directory not found: {IMAGE_DIR}")
    
    return issues

@st.cache_resource
def load_books_graph_only():
    """Load original RDF data only (for testing)"""
    try:
        g = rdflib.Graph()
        
        g.bind("", "http://www.example.org/bookstore#")
        g.bind("rdf", "http://www.w3.org/1999/02/22-rdf-syntax-ns#")
        g.bind("rdfs", "http://www.w3.org/2000/01/rdf-schema#")
        g.bind("owl", "http://www.w3.org/2002/07/owl#")
        g.bind("xsd", "http://www.w3.org/2001/XMLSchema#")
        
        if not os.path.exists(DATA_PATH):
            st.error(f"Data file not found at: {DATA_PATH}")
            st.info(f"Current working directory: {os.getcwd()}")
            st.info(f"Looking for: books.ttl")
            return None
        
        if not os.path.exists(ONTOLOGY_PATH):
            st.error(f"Ontology file not found at: {ONTOLOGY_PATH}")
            return None
        
        g.parse(DATA_PATH, format="turtle")
        g.parse(ONTOLOGY_PATH, format="turtle")
        
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
    st.set_page_config(
        page_title="Semantic Bookstore", 
        layout="wide", 
        page_icon="📚",
        initial_sidebar_state="expanded"
    )
    
    # ===== SIDEBAR DEBUG =====
    with st.sidebar:
        st.markdown("""
        <div class="sidebar-brand">
            <div class="icon">📖</div>
            <h3>Bookstore</h3>
            <p>Semantic Discovery</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        if st.session_state.get("reasoning_enabled", False):
            st.success("🔮 OWL Reasoning: Enabled")
            st.info("All searches use reasoning-enhanced semantic relationships")
        else:
            st.warning("⚠️ OWL Reasoning: Disabled")
        
        st.markdown("---")
        
        st.markdown("""
        <div style="padding: 0.5rem 0;">
            <p style="font-size: 0.75rem; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600;">Quick Stats</p>
        </div>
        """, unsafe_allow_html=True)
        
        graph = get_active_graph()
        if graph:
            all_books = get_all_books(graph)
            if not all_books.empty:
                st.metric("📚 Books", len(all_books))
                st.metric("✍️ Authors", all_books['Author'].nunique())
                st.metric("🏷️ Genres", all_books['Genre'].nunique())
        
        st.markdown("---")
        
        with st.expander("⚙️ System Info", expanded=False):
            st.write(f"**Data:** `{os.path.basename(DATA_PATH)}`")
            st.write(f"**Ontology:** `{os.path.basename(ONTOLOGY_PATH)}`")
            st.write(f"**Images:** `{os.path.basename(IMAGE_DIR)}`")
    
    # Verify file paths
    file_issues = verify_file_paths()
    if file_issues:
        for issue in file_issues:
            st.error(issue)
        st.stop()
    
    # Initialize session state
    if 'initialized' not in st.session_state:
        st.session_state.initialized = False
        st.session_state.load_error = None
    
    loading_placeholder = st.empty()
    
    if not st.session_state.initialized:
        with loading_placeholder.container():
            st.info("📚 Initializing book catalog and reasoning engine...")
            progress_bar = st.progress(0)
            
            progress_bar.progress(20)
            st.info("Loading book data...")
            
            g = load_data()
            
            if g is None or len(g) == 0:
                st.error("Failed to load data - graph is empty")
                st.session_state.load_error = "Empty graph"
                return
            
            progress_bar.progress(50)
            st.info("Verifying data...")
            
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
            
            progress_bar.progress(70)
            st.info("Running reasoning engine...")
            
            try:
                inferred = rdflib.Graph()
                for triple in g:
                    inferred.add(triple)
                
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
            
            import time
            time.sleep(0.5)
            loading_placeholder.empty()
            st.rerun()
            return
    
    # Normal application interface
    if st.session_state.get("reasoning_enabled", False):
        graph = st.session_state.get("inferred_graph")
    else:
        graph = st.session_state.get("original_graph")
    
    if graph is None:
        st.error("Graph is None - initialization failed")
        if st.button("Retry Loading"):
            st.session_state.initialized = False
            st.rerun()
        return
    
    # Main content
    show_homepage()
    
    # Divider and advanced search
    st.markdown("---")
    show_search_content(graph)
    
    # ===== FOOTER =====
    st.markdown("""
    <div class="store-footer">
        <div>
            <span class="brand">Semantic Web-Based <span class="accent">Book Search and Recommendation System</span></span>
            <span style="color: #d1d5db; margin: 0 0.75rem;">|</span>
            <span style="font-size: 0.9rem;">Semantic Web-Based Book Discovery</span>
        </div>
        <div class="footer-links">
            <span>Powered by RDFlib</span>
            <span>•</span>
            <span>SPARQL</span>
            <span>•</span>
            <span>OWL Inference</span>
            <span>•</span>
            <span>Streamlit</span>
        </div>
        <div style="margin-top: 0.75rem; font-size: 0.8rem; color: #9ca3af;">
            © 2026 Semantic Web-Based Book Search and Recommendation System
        </div>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()