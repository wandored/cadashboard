# R365 Dashboard

Flask web-app dashboard used to display Odata from R365.

- REQUIRED: Odata credentials

## Local Files

- /etc/config.json - environment data and keys
- ./lobster_items.json - dictionary of lobster sizes
- ./stone_claw_items.json - dictionary of stone crab sizes

## Local development with Docker Compose

Docker is used for local development testing. The Dockerfile and Compose file
are local files excluded from Git.

Rebuild the image after changing Python dependencies:

```bash
docker compose up --build
```

Open http://localhost:5001. Compose maps host port 5001 to container port 80.
