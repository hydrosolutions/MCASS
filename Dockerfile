# Use an official Python runtime as a parent image
FROM python:3.11

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

# Set the working directory in the container to /app
WORKDIR /app

# Add the current directory contents into the container at /app
ADD . /app

# Add Display to the container. This is needed for the dashboard to work.
#ENV DISPLAY :0

# Install any needed packages specified in requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    apt-get update && \
    apt-get install -y gdal-bin libgdal-dev && \
    pip install --upgrade pip && \
    pip install --trusted-host pypi.python.org -r requirements.txt

# Make port 5006 available to the world outside this container
EXPOSE 5006

# Run the command to start the dashboard
CMD ["panel", "serve", "--allow-websocket-origin=snowmapper.ch", "mcass-dashboard.py", "--show", "--autoreload"]
