# Use the official lightweight Python image as a base
FROM python:3.11-slim as app

# Install necessary packages and clean up to reduce image size
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy only requirements first for better cache utilization
COPY /application/requirements.txt /app/
COPY /application/requirements_full.txt /app/
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r requirements_full.txt

# Copy the application code after installing dependencies
COPY /application/ /app/

# Set permissions for the chroma directory (if necessary)
RUN chown -R root:root /app/docs/chroma && \
    chmod -R 755 /app/docs/chroma

# Expose the application's port
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
