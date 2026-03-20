# Backend

The backend is a Python AWS Lambda application that exposes:

- `GET /health`
- `GET /v1/integrations`
- `POST /v1/chat/plan`
- `POST /v1/chat/execute`

The code is written against the Python standard library so it can be tested without installing extra packages.