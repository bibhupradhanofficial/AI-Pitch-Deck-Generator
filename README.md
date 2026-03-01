# AI Pitch Deck Generator

## Project Overview

AI Pitch Deck Generator is a powerful tool that leverages Google's Generative AI to automatically create and assemble pitch decks. It handles everything from drafting content to generating visual assets and charts, providing a seamless generation experience with real-time streaming feedback to the user.

### Architecture

```text
+------+      +----------+      +-----------------------+      +--------------+      +-----------------------+
|      |      |          |      |                       |      |              |      |                       |
| User | ---> | Frontend | ---> | FastAPI / Cloud Run   | ---> | Gemini Agent | ---> | [Imagen, Veo, Charts] |
|      |      |          |      |                       |      |              |      |                       |
+------+      +----------+      +-----------------------+      +--------------+      +-----------------------+
   ^                                                                                             |
   |                                                                                             |
   |                                                                                             v
   |                                                                                         +-------+
   +--------------------------------------- Response stream -------------------------------- |  GCS  |
                                                                                             +-------+
```

## Prerequisites

Before you begin, ensure you have the following requirements met:

- **Python:** 3.11 or higher
- **GCP Account:** A Google Cloud project with an active billing account
- **Google Cloud APIs:** The following APIs must be enabled on your GCP project:
  - Vertex AI API
  - Cloud Storage API
  - Cloud Run API
  - Cloud Build API

## Local Setup Instructions

Follow these steps to set up and run the application locally:

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Copy the example environment file to create your local environment configuration:
   ```bash
   cp ../.env.example .env
   ```
   *Note: Open the newly created `.env` file and fill in all the necessary values.*

4. Start the FastAPI development server:
   ```bash
   uvicorn main:app --reload --port 8080
   ```

## GCP Setup Commands

To configure your local environment with your Google Cloud project and enable the necessary services, run the following commands:

```bash
# Login with application default credentials
gcloud auth application-default login

# Set your current GCP project
gcloud config set project YOUR_PROJECT_ID

# Enable the required APIs for the project
gcloud services enable aiplatform.googleapis.com storage.googleapis.com run.googleapis.com cloudbuild.googleapis.com
```

## Deployment

To deploy the application, run the deployment shell script provided in the project root:

```bash
bash deploy.sh
```

## Environment Variables

The following environment variables are used to configure the application. Ensure these are set correctly in your `.env` file or deployment environment.

| Variable | Description |
| :--- | :--- |
| `GCP_PROJECT_ID` | Your Google Cloud project ID. |
| `GCP_REGION` | The default region where your Vertex AI and Cloud Run services will reside. |
| `GCS_BUCKET_NAME` | The name of the Google Cloud Storage bucket used to store generated media. |
| `FRONTEND_URL` | The URL of your deployed frontend (used for configuring CORS in FastAPI). |
| `ENVIRONMENT` | Specifies the runtime environment (e.g., `development`, `production`). |
