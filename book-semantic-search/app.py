import streamlit as st
import rdflib
from rdflib.namespace import XSD
from owlready2 import *
import pandas as pd
import random
import os
from PIL import Image

# ---------------------------
# 1. LOAD RDF DATA
# ---------------------------
@st.cache_resource
def load_data():
    """Load RDF data and ontology"""
    g = rdflib.Graph()
    g.parse("data/books.ttl", format="turtle")
    g.parse("ontology/book_ontology.owl", format="turtle")
    return g

# ---------------------------
# 2. REASONING WITH OWLREADY2
# ---------------------------
@st.cache_resource
def load_ontology_and_reason():
    """Load ontology and run reasoner to infer new relationships"""
    onto = get_ontology("ontology/book_ontology.owl").load()
    sync_reasoner()
    return onto

# ---------------------------
# 3. SPARQL QUERY FUNCTIONS
# ---------------------------
def search_by_keyword(graph, keyword):
    """Search books by title, author, or genre using SPARQL"""
    query = f"""
    PREFIX : <http://www.example.org/bookstore#>
    SELECT ?book ?title ?author ?genre ?price WHERE {{
        ?book rdf:type :Book ;
                 :title ?title ;
                 :author ?author ;
                 :genre ?genre ;
                 :price ?price .
        FILTER(CONTAINS(LCASE(?title), LCASE("{keyword}")) || 
               CONTAINS(LCASE(?author), LCASE("{keyword}")) ||
               CONTAINS(LCASE(?genre), LCASE("{keyword}")))
    }}
    """
    results = []
    for row in graph.query(query):
        results.append({
            "Book": str(row.book).split("#")[-1],
            "Title": str(row.title),
            "Author": str(row.author),
            "Genre": str(row.genre),
            "Price (RM)": float(row.price)
        })
    return pd.DataFrame(results)

def filter_by_price(graph, min_price, max_price):
    """Filter books within price range"""
    query = f"""
    PREFIX : <http://www.example.org/bookstore#>
    SELECT ?book ?title ?author ?price WHERE {{
        ?book :title ?title ;
                 :author ?author ;
                 :price ?price .
        FILTER(?price >= {min_price} && ?price <= {max_price})
    }}
    ORDER BY ?price
    """
    results = []
    for row in graph.query(query):
        results.append({
            "Book": str(row.book).split("#")[-1],
            "Title": str(row.title),
            "Author": str(row.author),
            "Price (RM)": float(row.price)
        })
    return pd.DataFrame(results)

def get_similar_books(graph, book_title):
    """Find books similar to a given book using OWL property (same author or genre)"""
    query = f"""
    PREFIX : <http://www.example.org/bookstore#>
    SELECT ?book ?similar_title ?author ?genre WHERE {{
        ?book :title "{book_title}" ;
                 :author ?author ;
                 :genre ?genre .
        ?similar_book :title ?similar_title ;
                      :author ?author ;
                      :genre ?genre .
        FILTER(?similar_title != "{book_title}")
    }}
    LIMIT 10
    """
    results = []
    for row in graph.query(query):
        results.append({
            "Title": str(row.similar_title),
            "Author": str(row.author),
            "Genre": str(row.genre)
        })
    return pd.DataFrame(results)

def get_books_by_genre(graph, genre):
    """Get all books in a genre (with OWL inference)"""
    query = f"""
    PREFIX : <http://www.example.org/bookstore#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?book ?title ?author ?price WHERE {{
        ?book rdf:type/rdfs:subClassOf* :{genre} ;
                 :title ?title ;
                 :author ?author ;
                 :price ?price .
    }}
    """
    results = []
    for row in graph.query(query):
        results.append({
            "Book": str(row.book).split("#")[-1],
            "Title": str(row.title),
            "Author": str(row.author),
            "Price (RM)": float(row.price)
        })
    return pd.DataFrame(results)

def get_books_by_author(graph, author_name):
    """Get all books by a specific author"""
    query = f"""
    PREFIX : <http://www.example.org/bookstore#>
    SELECT ?book ?title ?genre ?price WHERE {{
        ?book :title ?title ;
                 :author "{author_name}" ;
                 :genre ?genre ;
                 :price ?price .
    }}
    """
    results = []
    for row in graph.query(query):
        results.append({
            "Title": str(row.title),
            "Genre": str(row.genre),
            "Price (RM)": float(row.price)
        })
    return pd.DataFrame(results)

def get_bestseller_recommendations(graph):
    """Get books marked as bestsellers"""
    query = f"""
    PREFIX : <http://www.example.org/bookstore#>
    SELECT ?book ?title ?author ?price WHERE {{
        ?book rdf:type :Bestseller ;
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
            "Price (RM)": float(row.price)
        })
    return pd.DataFrame(results)

def get_all_books(graph):
    """Get all books in the catalog"""
    query = f"""
    PREFIX : <http://www.example.org/bookstore#>
    SELECT ?title ?author ?genre ?price WHERE {{
        ?book rdf:type :Book ;
              :title ?title ;
              :author ?author ;
              :genre ?genre ;
              :price ?price .
    }}
    """
    results = []
    for row in graph.query(query):
        results.append({
            "Title": str(row.title),
            "Author": str(row.author),
            "Genre": str(row.genre),
            "Price (RM)": float(row.price)
        })
    return pd.DataFrame(results)

def get_recommendations_by_description(description, category, graph):
    """Get book recommendations based on user description and category"""
    all_books = get_all_books(graph)
    
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
    """
    Get the cover image path for a given book title.
    Returns the image path if exists, otherwise returns None.
    """
    # Map book titles to your image filenames
    cover_mapping = {
        "Harry Potter and the Sorcerer's Stone": "HP1.jpg",
        "Harry Potter and the Chamber of Secrets": "HP2.jpg",
        "Harry Potter and the Prisoner of Azkaban": "HP3.jpg",
    }
    
    # Get the filename for this book
    filename = cover_mapping.get(book_title)
    
    if filename:
        cover_path = f"image/{filename}"
        if os.path.exists(cover_path):
            return cover_path
    
    # Return None if no cover found
    return None

def display_book_card(book_title, author, genre, price, show_cover=True):
    """Display a book card with optional cover image"""
    
    cover_path = get_book_cover(book_title) if show_cover else None
    col1, col2 = st.columns([1, 3])
    
    with col1:
        if cover_path and os.path.exists(cover_path):
            try:
                cover = Image.open(cover_path)
                st.image(cover, width=100)
            except Exception as e:
                print(f"Error loading image: {e}")
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
    
    # Load data
    with st.spinner("Loading book catalog..."):
        graph = load_data()
    
    # Create two columns for input (removed tone column)
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Please enter a description of a book you like**")
        description = st.text_area("", placeholder="e.g., A tale of friendship, magic, and adventure...", height=100)
    
    with col2:
        st.markdown("**Select a category**")
        categories = ["All", "NonFiction", "Fantasy", "Mystery", "Biography", "Technical"]
        category = st.selectbox("", categories, label_visibility="collapsed")
    
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
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); padding: 1rem; border-radius: 10px; text-align: center;">
                    <h4>{book['Title'][:25]}...</h4>
                    <p>{book['Author']}<br>RM {book['Price (RM)']}</p>
                </div>
                """, unsafe_allow_html=True)
    
    # Quick Stats
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    
    all_books = get_all_books(graph)
    unique_authors = all_books['Author'].nunique()
    unique_genres = all_books['Genre'].nunique()
    
    with col1:
        st.metric("Total Books", len(all_books))
    with col2:
        st.metric("Authors", unique_authors)
    with col3:
        st.metric("Genres", unique_genres)
    with col4:
        st.metric("Bestsellers", len(bestsellers))

# ---------------------------
# 5. SEARCH PAGE UI
# ---------------------------
def show_search_page():
    """Display the advanced search page"""
    
    st.title("Advanced Book Search")
    st.markdown("Use the sidebar to search for books by keyword, price, genre, author, or browse bestsellers!")
    
    # Load data
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
                    st.dataframe(df, use_container_width=True)

                st.success(f"Found {len(df)} books matching '{keyword}'")
                
                if "Genre" in df.columns:
                    st.caption("Genre distribution:")
                    st.dataframe(df["Genre"].value_counts().reset_index().rename(columns={"index": "Genre", "Genre": "Count"}))
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
                    st.dataframe(df, use_container_width=True)

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
        st.info("**Semantic Intelligence**: Searching 'Fiction' also returns Fantasy, Mystery, and Science Fiction due to OWL subclass inference!")
        
        genres = ["All", "NonFiction", "Fantasy", "Mystery", "Biography", "Technical"]
        genre = st.selectbox("Select a genre:", genres)
        
        if genre:
            df = get_books_by_genre(graph, genre)
            if not df.empty:
                for _, book in df.iterrows():
                    display_book_card(
                        book_title=book['Title'],
                        author=book['Author'],
                        genre=genre,
                        price=book['Price (RM)'],
                        show_cover=True
                    )

                with st.expander("View as table"):
                    st.dataframe(df, use_container_width=True)

                st.caption(f"Showing {len(df)} books in '{genre}' and its subgenres (inferred via OWL reasoning)")
                unique_authors = df["Author"].nunique()
                st.metric("Unique Authors", unique_authors)
            else:
                st.warning("No books found in this genre.")
    
    # 4. BROWSE BY AUTHOR
    elif search_type == "Browse by Author":
        st.subheader("Browse Books by Author")
        
        authors = ["J.K. Rowling", "George R.R. Martin", "J.R.R. Tolkien", "Dan Brown", "Yuval Noah Harari", "Gillian Flynn", "Michelle Obama", "Robert C. Martin"]
        author_name = st.selectbox("Select an author:", authors)
        
        if author_name:
            df = get_books_by_author(graph, author_name)
            if not df.empty:
                for _, book in df.iterrows():
                    display_book_card(
                        book_title=book['Title'],
                        author=author_name,
                        genre=book['Genre'],
                        price=book['Price (RM)'],
                        show_cover=True
                    )

                with st.expander("View as table"):
                    st.dataframe(df, use_container_width=True)
                    
                st.success(f"Found {len(df)} books by {author_name}")
            else:
                st.warning(f"No books found by {author_name}")
    
    # 5. SIMILAR BOOKS
    elif search_type == "Similar Books":
        st.subheader("Find Similar Books")
        st.caption("Based on same author or genre — powered by semantic relationships")
        
        all_books = get_all_books(graph)
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
                    price="N/A",
                    show_cover=True
                )

            else:
                st.info("No similar books found in the catalog yet.")
    
    # 6. BESTSELLERS
    elif search_type == "Bestsellers":
        st.subheader("Bestseller Recommendations")
        st.info("These books are classified as Bestsellers using OWL reasoning")
        
        df = get_bestseller_recommendations(graph)
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            st.balloons()
        else:
            st.warning("No bestseller data available.")

# ---------------------------
# 6. MAIN APP
# ---------------------------
def main():
    st.set_page_config(page_title="Semantic Book Recommender", layout="wide", page_icon="📚")
    
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
        "<div style='text-align: center; color: #666;'><strong>Semantic Book Store</strong> | Powered by RDFlib, Owlready2, Streamlit | RDF + SPARQL + OWL Inference</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()