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
    g.parse("data/products.ttl", format="turtle")
    g.parse("ontology/ecommerce_ontology.owl", format="turtle")
    return g

# ---------------------------
# 2. REASONING WITH OWLREADY2
# ---------------------------
@st.cache_resource
def load_ontology_and_reason():
    """Load ontology and run reasoner to infer new relationships"""
    onto = get_ontology("ontology/ecommerce_ontology.owl").load()
    # Load individuals from RDF data
    # (This would typically be done by converting RDF to Owlready2 format)
    
    # Run HermiT reasoner to infer classifications
    # Example: A GamingLaptop will be inferred as a Laptop and Electronics
    sync_reasoner()  # Runs HermiT by default
    
    return onto

# ---------------------------
# 3. SPARQL QUERY FUNCTIONS
# ---------------------------
def search_by_keyword(graph, keyword):
    """Search products by name or brand using SPARQL"""
    query = f"""
    PREFIX : <http://www.example.org/ecommerce#>
    SELECT ?product ?name ?brand ?price WHERE {{
        ?product rdf:type :Product ;
                 :name ?name ;
                 :brand ?brand ;
                 :price ?price .
        FILTER(CONTAINS(LCASE(?name), LCASE("{keyword}")) || 
               CONTAINS(LCASE(?brand), LCASE("{keyword}")))
    }}
    """
    results = []
    for row in graph.query(query):
        results.append({
            "Product": str(row.product).split("#")[-1],
            "Name": str(row.name),
            "Brand": str(row.brand),
            "Price": float(row.price)
        })
    return pd.DataFrame(results)

def filter_by_price(graph, min_price, max_price):
    """Filter products within price range [citation:5]"""
    query = f"""
    PREFIX : <http://www.example.org/ecommerce#>
    SELECT ?product ?name ?price WHERE {{
        ?product :name ?name ;
                 :price ?price .
        FILTER(?price >= {min_price} && ?price <= {max_price})
    }}
    ORDER BY ?price
    """
    results = []
    for row in graph.query(query):
        results.append({
            "Product": str(row.product).split("#")[-1],
            "Name": str(row.name),
            "Price": float(row.price)
        })
    return pd.DataFrame(results)

def get_compatible_products(graph, product_name):
    """Find products compatible with a given product using OWL property"""
    query = f"""
    PREFIX : <http://www.example.org/ecommerce#>
    SELECT ?product ?compatible_name WHERE {{
        ?product :name "{product_name}" ;
                 :compatibleWith ?compatible .
        ?compatible :name ?compatible_name .
    }}
    """
    results = []
    for row in graph.query(query):
        results.append(str(row.compatible_name))
    return results

def get_products_by_category(graph, category):
    """Get all products in a category (with OWL inference)"""
    # Note: With reasoning, this will also return subcategory products
    query = f"""
    PREFIX : <http://www.example.org/ecommerce#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    SELECT ?product ?name ?price WHERE {{
        ?product rdf:type/rdfs:subClassOf* :{category} ;
                 :name ?name ;
                 :price ?price .
    }}
    """
    results = []
    for row in graph.query(query):
        results.append({
            "Product": str(row.product).split("#")[-1],
            "Name": str(row.name),
            "Price": float(row.price)
        })
    return pd.DataFrame(results)

# ---------------------------
# 4. STREAMLIT UI
# ---------------------------
def main():
    st.set_page_config(page_title="Semantic Product Search", layout="wide")
    
    st.title("🛍️ Semantic Product Search Engine")
    st.markdown("Using **RDF + SPARQL + OWL Inference**")
    
    # Load data
    with st.spinner("Loading product catalog..."):
        graph = load_data()
    
    # Sidebar navigation
    st.sidebar.header("Search Options")
    search_type = st.sidebar.radio(
        "Choose search method:",
        ["🔍 Keyword Search", "💰 Price Range", "📂 Category Browse", "🔗 Compatibility"]
    )
    
    # 1. KEYWORD SEARCH
    if search_type == "🔍 Keyword Search":
        st.subheader("Search Products by Name or Brand")
        keyword = st.text_input("Enter product name or brand:", "iPhone")
        if keyword:
            df = search_by_keyword(graph, keyword)
            if not df.empty:
                st.dataframe(df, use_container_width=True)
                st.success(f"Found {len(df)} products")
            else:
                st.warning("No products found")
    
    # 2. PRICE FILTER
    elif search_type == "💰 Price Range":
        st.subheader("Filter Products by Price")
        col1, col2 = st.columns(2)
        with col1:
            min_price = st.number_input("Min Price (RM)", min_value=0, value=0)
        with col2:
            max_price = st.number_input("Max Price (RM)", min_value=0, value=2000)
        
        if st.button("Search"):
            df = filter_by_price(graph, min_price, max_price)
            if not df.empty:
                st.dataframe(df, use_container_width=True)
                # Show summary statistics
                st.metric("Average Price", f"RM{df['Price'].mean():.2f}")
                st.metric("Total Products", len(df))
            else:
                st.warning("No products in this price range")
    
    # 3. CATEGORY BROWSE (Demonstrates OWL Inference)
    elif search_type == "📂 Category Browse":
        st.subheader("Browse by Category")
        st.info("💡 **Semantic Intelligence**: Searching 'Electronics' also returns Laptops, Smartphones, and Accessories due to OWL subclass inference!")
        
        categories = ["Electronics", "Laptop", "Smartphone", "Accessory", "GamingLaptop"]
        category = st.selectbox("Select category:", categories)
        
        if category:
            df = get_products_by_category(graph, category)
            if not df.empty:
                st.dataframe(df, use_container_width=True)
                st.caption(f"Showing {len(df)} products in '{category}' and its subcategories")
            else:
                st.warning("No products in this category")
    
    # 4. COMPATIBILITY RECOMMENDATIONS
    elif search_type == "🔗 Compatibility":
        st.subheader("Find Compatible Accessories")
        products = ["iPhone 14 Pro", "Samsung Galaxy S23", "ASUS ROG Zephyrus", "Dell XPS 13", "USB-C Fast Charger"]
        selected = st.selectbox("Select a product:", products)
        
        if selected:
            compatible = get_compatible_products(graph, selected)
            if compatible:
                st.success(f"✅ Products compatible with {selected}:")
                for item in compatible:
                    st.write(f"• {item}")
            else:
                st.info("No compatibility information available for this product")
    
    # Footer with project info
    st.markdown("---")
    st.caption("Powered by RDFlib, Owlready2, and Streamlit")

if __name__ == "__main__":
    main()