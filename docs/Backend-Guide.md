# Backend Guide

This guide explains how to set up and run the Python backend.

## Prerequisites

- Python 3.9 or later
- pip
- Docker (optional)

## Setup

1.  **Clone the repository**:

    ```bash
    git clone <repository-url>
    cd <project-directory>/app
    ```

2.  **Install dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure the environment**:

    Copy the `.env.example` file to `.env` and update the environment variables as needed.

## Running the Application

- **With Docker**:

  ```bash
  docker-compose up --build
  ```

- **Without Docker**:

  ```bash
  uvicorn app.main:app --reload
  ```
