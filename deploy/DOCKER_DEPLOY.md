# Docker Deployment Guide

## 1) Build and run

From project root:

```powershell
cd E:\CongNgheTriThuc\Knowledge_technology
docker compose up -d --build
```

## 2) Verify services

- Frontend UI: http://localhost/
- Backend health (quick check via API):

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost/api/ask -ContentType "application/json" -Body '{"question":"Xin chao"}'
```

- Fuseki raw dataset: http://localhost:3030/legalqa/query
- Fuseki inference dataset: http://localhost:3030/legalqa-inf/sparql

## 3) Common commands

- Logs:

```powershell
docker compose logs -f
```

- Restart stack:

```powershell
docker compose restart
```

- Stop stack:

```powershell
docker compose down
```

- Stop and remove data volume (rebuild dataset from RDF/TTL on next start):

```powershell
docker compose down -v
```

## 4) Notes

- Fuseki data is persisted in Docker volume `fuseki-data`.
- First boot may take longer because TDB2 is initialized automatically.
- Backend endpoints are configurable via env vars:
  - `APP_FUSEKI_BASE_ENDPOINT`
  - `APP_FUSEKI_INFERENCE_ENDPOINT`
