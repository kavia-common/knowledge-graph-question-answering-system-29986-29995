# knowledge-graph-question-answering-system-29986-29995

A simple knowledge graph-based question answering system using Django + DRF and Neo4j.

Quick start:
1) Create and configure environment variables
   - Copy question_answering_backend/.env.example to your environment or export them.
   - Ensure a Neo4j instance is running and credentials are correct.

2) Install dependencies
   - pip install -r question_answering_backend/requirements.txt

3) Run migrations and start server
   - cd question_answering_backend
   - python manage.py migrate
   - python manage.py runserver 0.0.0.0:8000

4) Seed sample graph (optional)
   - python manage.py seed_graph

5) Try the API
   - Health: http://localhost:8000/api/health/
   - Neo4j connectivity health: http://localhost:8000/api/health/neo4j/
     Returns {"ok": true} if backend can connect to Neo4j. If you see errors like
     "Cannot resolve address <host>:7687", verify your NEO4J_URI and network/DNS.
     For Neo4j Aura, prefer neo4j://<host>:7687 and ensure outbound DNS is allowed.
   - POST http://localhost:8000/api/ask/
     Body: { "question": "Who works at Contoso?" }
   - Docs: http://localhost:8000/docs

Notes:
- Copy question_answering_backend/.env.example to question_answering_backend/.env and provide values.
- For local Neo4j: NEO4J_URI=bolt://localhost:7687
- For Neo4j Aura: NEO4J_URI=neo4j://<host>:7687 and consider NEO4J_ENCRYPTED=true

Ocean Professional theme: blue (#2563EB) and amber (#F59E0B) accents reflected in API descriptions and metadata.