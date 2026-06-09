# Azure Infrastructure & Teams Setup Guide

This guide details how to provision the necessary Azure resources and configure the Microsoft Teams side panel for the Smart Interviewer module.

---

## 1. Azure Cosmos DB Setup

Azure Cosmos DB is used to store interview sessions, question configurations, candidate answers, transcripts, and evaluation scores.

1. Navigate to the **Azure Portal**.
2. Search for and select **Azure Cosmos DB** -> click **Create** -> choose **Azure Cosmos DB for NoSQL**.
3. Configure settings:
   - **Resource Group**: Use your existing group.
   - **Account Name**: e.g., `smart-interviewer-db`.
   - **Capacity mode**: Provisioned throughput or Serverless (Serverless recommended for dev/test).
4. Review and click **Create**.
5. Once deployed, go to **Keys** in the left menu and copy:
   - **URI** -> Set in `.env` as `COSMOS_ENDPOINT`.
   - **Primary Key** -> Set in `.env` as `COSMOS_KEY`.
6. Run the database provisioning script from the repository root:
   ```bash
   python infrastructure/cosmos_setup.py
   ```
   This creates the `smart_interviewer` database and the `interview_sessions` container partitioned by `/candidate_id`.

---

## 2. Azure Speech Service Setup

Azure Speech Service is used to transcribe candidate spoken answers in real-time within the Teams meeting panel.

1. Search for and select **Speech services** in the Azure Portal -> click **Create**.
2. Configure settings:
   - **Resource Group**: Same group as above.
   - **Name**: e.g., `smart-interviewer-speech`.
   - **Pricing Tier**: Free (F0) or Standard (S0).
3. Review and click **Create**.
4. Once deployed, go to **Keys and Endpoint** in the left menu and copy:
   - **Key 1** -> Set in `.env` as `AZURE_SPEECH_KEY`.
   - **Location/Region** -> Set in `.env` as `AZURE_SPEECH_REGION` (e.g., `eastus`).

---

## 3. Azure Communication Services (Email) Setup

Used to send invitation emails to candidates containing the scheduled meeting link and preparatory instructions.

1. Search for and select **Communication Services** in the Azure Portal -> click **Create**.
2. Once created, search for **Email Communication Services** -> click **Create**.
3. Create a **1-click free Azure subdomain** or connect your custom verified domain.
4. Go to **Setup** -> **Provision Domains** -> copy the sender address (e.g., `DoNotReply@xxxxxxxx.azurecomm.net`). Set this as `ACS_SENDER_EMAIL` in `.env`.
5. Connect your Email Communication Service resource to your primary Communication Service resource in the portal.
6. Go back to your primary Communication Service resource -> **Keys** -> copy the **Connection string** -> Set in `.env` as `ACS_CONNECTION_STRING`.

---

## 4. Azure Blob Storage Setup

Used to store candidate screen + microphone video recordings.

1. Go to your existing Storage Account in the Azure Portal.
2. Select **Containers** under Data Storage -> click **+ Container**.
3. Set name to `interview-recordings` (Set `AZURE_BLOB_RECORDINGS_CONTAINER` in `.env`).
4. Set access level to **Private**.
5. The backend uses the existing `AZURE_STORAGE_CONNECTION_STRING` to generate time-limited read/write SAS tokens for this container.

---

## 5. Teams App Registration & Manifest

The side panel runs as an in-meeting app inside Microsoft Teams. To install it, you need to create a zip file with the manifest.

### Prerequisites

You need `ngrok` or another tunneling software to expose your local Vite dev server (`http://localhost:3001`) to the internet during development:
```bash
ngrok http 3001
```
Copy the generated HTTPS URL (e.g. `https://xxxx.ngrok-free.app`).

### Manifest Modification

1. Open `teams-panel/public/manifest/manifest.json`.
2. Replace all instances of `https://<your_ngrok_url>` with your active ngrok HTTPS forwarding URL.
3. Replace `your-static-meeting-url` in `.env` with a real Teams meeting link.

### Uploading to Teams

1. Zip the files inside `teams-panel/public/manifest/` (`manifest.json`, `color.png`, `outline.png`) into a file named `manifest.zip`.
2. Go to **Microsoft Teams** -> **Apps** (left sidebar) -> **Manage your apps** (at the bottom) -> **Upload an app** -> **Upload a custom app**.
3. Select `manifest.zip`.
4. Add the app to a calendar meeting: Schedule a Teams meeting -> Edit meeting -> click **+ (Add app)** -> Search for **Smart Interviewer** -> click **Add**.
5. When you join the meeting, the **Smart Interviewer** icon will appear on the top meeting toolbar. Click it to open the side panel!
