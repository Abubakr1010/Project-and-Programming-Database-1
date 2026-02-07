# Use a more modern Python base for better compatibility with Gemini SDK
FROM python:3.9-slim

# Set environment variables to prevent Python from writing .pyc files 
# and to ensure output is sent straight to terminal (unbuffered)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
# - graphviz: Required for rendering the ER diagrams
# - libpq-dev & gcc: Required for psycopg2 (PostgreSQL adapter)
# - curl: For healthchecks or debugging
RUN apt-get update && apt-get install -y \
    graphviz \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . /app

# Streamlit uses port 8501 by default
EXPOSE 8501

# Run the application
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.enableCORS=false"]