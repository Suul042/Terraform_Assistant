# Gemini Project Overview

This file provides a central guide to understanding and contributing to this project.

## Project Structure

- **`/app`**: Contains the backend Python application logic.
- **`/frontend`**: Holds the Next.js frontend application.
- **`/docs`**: Project documentation.
- **`/tests`**: Automated tests for the application.
- **`.github/workflows`**: CI/CD pipelines.

## Key Files

- **`docker-compose.yml`**: Defines the services, networks, and volumes for local development.
- **`Dockerfile`**: Instructions for building the application's Docker image.
- **`requirements.txt`**: Python dependencies for the backend.
- **`package.json`**: Node.js dependencies for the frontend.

## Getting Started

1.  **Backend**: Navigate to the `/app` directory and install dependencies using `pip install -r requirements.txt`.
2.  **Frontend**: Navigate to the `/frontend` directory and install dependencies using `npm install`.
3.  **Run the application**: Use `docker-compose up` from the root directory.
