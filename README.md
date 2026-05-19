# TWS_Project

# Step 1: Create and Setup Project
# ---------------------------------
mkdir ecommerce-semantic-search
cd ecommerce-semantic-search
python -m venv venv

# Step 2: Activate Virtual Environment
# -----------------------------------------------
venv\Scripts\activate

# Step 3: Upgrade pip and Install Packages
# -----------------------------------------
python -m pip install --upgrade pip
python -m pip install streamlit rdflib owlready2 pandas

# Step 4: Verify Installation
# --------------------------------------
pip list | findstr "streamlit rdflib owlready pandas"

# Step 5: Run the Application (terminal)
# ---------------------------
python -m streamlit run app.py

# Step 6: Clear Cache (terminal)
# -------------------------------
python -m streamlit cache clear



