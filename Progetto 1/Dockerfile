# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# Added pytest explicitly for container-based testing if needed
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir pytest

# Copy the current directory contents into the container at /app
COPY . .

# create the simulation_data directory to avoid permission issues if run as non-root (optional best practice)
RUN mkdir -p simulation_data

# Make port 80 available to the world outside this container
# (Not strictly needed for a CLI app, but good practice for future web expansion)
# EXPOSE 80

# Define environment variable
# ENV NAME World

# Run main.py when the container launches
CMD ["python", "main.py"]
