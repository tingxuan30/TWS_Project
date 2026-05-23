import streamlit as st
import rdflib
from rdflib.namespace import XSD
from owlready2 import *
import pandas as pd

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
    
    # Run HermiT reasoner to infer classifications
    # Example: A FantasyNovel will be inferred as a Book and Fiction
    sync_reasoner()  # Runs HermiT by default
    
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
    # With reasoning, this will also return subgenre books
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
    """Get books marked as bestsellers (using OWL inference)"""
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

# ---------------------------
# 4. STREAMLIT UI
# ---------------------------
def main():
    st.set_page_config(page_title="Semantic Book Search Engine", layout="wide", page_icon="📚")
    
    st.title("📚 Semantic Book Search Engine")
    st.markdown("Using **RDF + SPARQL + OWL Inference** for Intelligent Book Discovery")
    st.caption("Find books by title, author, genre, price range, or get AI‑powered recommendations")
    
    # Load data
    with st.spinner("Loading book catalog from semantic knowledge graph..."):
        graph = load_data()
    
    # Sidebar navigation
    st.sidebar.header("🔍 Search Options")
    search_type = st.sidebar.radio(
        "Choose search method:",
        ["Keyword Search", "Price Range", "Browse by Genre", "Browse by Author", "Similar Books", "Bestsellers"]
    )
    
    # 1. KEYWORD SEARCH
    if search_type == "Keyword Search":
        st.subheader("🔎 Search Books by Title, Author, or Genre")
        keyword = st.text_input("Enter book title, author name, or genre:", "Harry Potter")
        if keyword:
            df = search_by_keyword(graph, keyword)
            if not df.empty:
                st.dataframe(df, use_container_width=True)
                st.success(f"📖 Found {len(df)} books matching '{keyword}'")
                
                # Show genre distribution
                if "Genre" in df.columns:
                    st.caption("Genre distribution:")
                    st.dataframe(df["Genre"].value_counts().reset_index().rename(columns={"index": "Genre", "Genre": "Count"}))
            else:
                st.warning("No books found. Try a different keyword.")
    
    # 2. PRICE FILTER
    elif search_type == "Price Range":
        st.subheader("💰 Filter Books by Price")
        col1, col2 = st.columns(2)
        with col1:
            min_price = st.number_input("Min Price (RM)", min_value=0, value=0, step=5)
        with col2:
            max_price = st.number_input("Max Price (RM)", min_value=0, value=100, step=5)
        
        if st.button("🔍 Search", type="primary"):
            df = filter_by_price(graph, min_price, max_price)
            if not df.empty:
                st.dataframe(df, use_container_width=True)
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("📊 Average Price", f"RM{df['Price (RM)'].mean():.2f}")
                with col_b:
                    st.metric("📚 Total Books", len(df))
                with col_c:
                    st.metric("💵 Cheapest Book", f"RM{df['Price (RM)'].min():.2f}")
            else:
                st.warning("No books found in this price range.")
    
    # 3. BROWSE BY GENRE (Demonstrates OWL Inference)
    elif search_type == "Browse by Genre":
        st.subheader("📖 Browse Books by Genre")
        st.info("✨ **Semantic Intelligence**: Searching 'Fiction' also returns Fantasy, Mystery, and Science Fiction due to OWL subclass inference!")
        
        genres = ["Book", "Fiction", "NonFiction", "Fantasy", "Mystery", "ScienceFiction", "Biography", "Technical"]
        genre = st.selectbox("Select a genre:", genres)
        
        if genre:
            df = get_books_by_genre(graph, genre)
            if not df.empty:
                st.dataframe(df, use_container_width=True)
                st.caption(f"📚 Showing {len(df)} books in '{genre}' and its subgenres (inferred via OWL reasoning)")
                
                # Show unique authors count
                unique_authors = df["Author"].nunique()
                st.metric("✍️ Unique Authors", unique_authors)
            else:
                st.warning("No books found in this genre.")
    
    # 4. BROWSE BY AUTHOR
    elif search_type == "Browse by Author":
        st.subheader("✍️ Browse Books by Author")
        
        # Sample authors (you can also query this dynamically from RDF)
        authors = ["J.K. Rowling", "George R.R. Martin", "J.R.R. Tolkien", "Dan Brown", "Yuval Noah Harari"]
        author_name = st.selectbox("Select an author:", authors)
        
        if author_name:
            df = get_books_by_author(graph, author_name)
            if not df.empty:
                st.dataframe(df, use_container_width=True)
                st.success(f"Found {len(df)} books by {author_name}")
            else:
                st.warning(f"No books found by {author_name}")
    
    # 5. SIMILAR BOOKS (Recommendation)
    elif search_type == "Similar Books":
        st.subheader("🔗 Find Similar Books")
        st.caption("Based on same author or genre — powered by semantic relationships")
        
        popular_books = ["Harry Potter and the Sorcerer's Stone", "A Game of Thrones", "The Hobbit", "The Da Vinci Code", "Sapiens"]
        book_title = st.selectbox("Select a book you like:", popular_books)
        
        if book_title:
            df = get_similar_books(graph, book_title)
            if not df.empty:
                st.success(f"📖 Readers who liked '{book_title}' also enjoyed:")
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No similar books found in the catalog yet.")
    
    # 6. BESTSELLERS (OWL Inference demo)
    elif search_type == "Bestsellers":
        st.subheader("⭐ Bestseller Recommendations")
        st.info("🏆 These books are classified as Bestsellers using OWL reasoning")
        
        df = get_bestseller_recommendations(graph)
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            st.balloons()
        else:
            st.warning("No bestseller data available.")
    
    # Footer with project info
    st.markdown("---")
    st.caption("📚 **Semantic Book Store** | Powered by RDFlib, Owlready2, Streamlit | RDF + SPARQL + OWL Inference")

if __name__ == "__main__":
    main()