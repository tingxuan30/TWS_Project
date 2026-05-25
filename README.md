# TWS_Project

Update all into the ternimal

### Step 1: Create and Setup Project

1）mkdir book-semantic-search

2) cd book-semantic-search
   
3）python -m venv venv

### -----------------------------------------------
### Step 2: Activate Virtual Environment

1）venv\Scripts\activate

### -----------------------------------------------
### Step 3: Upgrade pip and Install Packages

1）python -m pip install --upgrade pip

2) python -m pip install streamlit rdflib owlready2 pandas

### -----------------------------------------------
### Step 4: Verify Installation

1）pip list | findstr "streamlit rdflib owlready pandas"

### -----------------------------------------------
### Step 5: Run the Application

Don't forget to put it in the "book-semantic-search" folder (cd book-semantic-search)

After running the code, please enter your email address in the terminal, and then it will be forwarded to the website

1）python -m streamlit run app.py

### -----------------------------------------------
### Step 6: Clear Cache (terminal)

1）python -m streamlit cache clear



