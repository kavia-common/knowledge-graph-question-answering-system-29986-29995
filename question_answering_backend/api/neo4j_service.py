"""
Neo4j service module that manages a singleton driver and exposes a simple query interface.

Configuration:
- Reads connection settings from environment variables (do not hardcode credentials)
  NEO4J_URI          e.g. bolt://localhost:7687 or neo4j://host:7687
  NEO4J_USER         database username
  NEO4J_PASSWORD     database password
  NEO4J_DATABASE     optional; defaults to 'neo4j'

This module is intentionally lightweight and resilient:
- If configuration is missing or connection fails, queries raise ValueError with a clear message.
- Caller code (e.g., services) can catch and return nice API errors.

Notes:
- Ensure a running Neo4j instance is reachable with the above credentials.
"""

import os
from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase, basic_auth
from neo4j.exceptions import Neo4jError, ServiceUnavailable, AuthError


class _Neo4jService:
    """
    Thin wrapper around the Neo4j Python driver.
    Creates a driver on first use and reuses it across calls.
    """

    def __init__(self) -> None:
        self._driver = None  # lazy init
        self._config_err: Optional[str] = None

    def _get_env(self) -> Dict[str, Optional[str]]:
        return {
            "uri": os.getenv("NEO4J_URI"),
            "user": os.getenv("NEO4J_USER"),
            "password": os.getenv("NEO4J_PASSWORD"),
            "database": os.getenv("NEO4J_DATABASE", "neo4j"),
        }

    def _ensure_driver(self) -> None:
        """
        Initialize the driver if not present. Any configuration or connection error will be
        captured and surfaced on query attempts.
        """
        if self._driver is not None or self._config_err:
            return

        env = self._get_env()
        missing = [k for k, v in env.items() if k in ("uri", "user", "password") and (v is None or v == "")]
        if missing:
            self._config_err = (
                "Neo4j configuration missing. Please set environment variables: "
                f"{', '.join(['NEO4J_URI','NEO4J_USER','NEO4J_PASSWORD'])}."
            )
            return

        try:
            auth = basic_auth(env["user"], env["password"])
            # Create the driver (does not verify connection until used)
            self._driver = GraphDatabase.driver(env["uri"], auth=auth)
        except (AuthError, ServiceUnavailable, Neo4jError) as exc:
            self._config_err = f"Failed to initialize Neo4j driver: {exc}"
        except Exception as exc:  # broad fallback with clear message
            self._config_err = f"Unexpected error initializing Neo4j driver: {exc}"

    # PUBLIC_INTERFACE
    def run_cypher(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query and return a list of dictionaries for rows.

        Args:
            query: Cypher query string
            parameters: Optional dict of parameters

        Returns:
            List of dictionaries (each row as a key-value dict)

        Raises:
            ValueError if configuration/connection error occurs.
        """
        self._ensure_driver()
        if self._config_err:
            raise ValueError(self._config_err)

        if not query or not isinstance(query, str):
            return []

        params = parameters or {}
        env = self._get_env()
        database = env["database"] or "neo4j"

        try:
            assert self._driver is not None  # for type-checkers
            with self._driver.session(database=database) as session:
                # Defensive normalization of person/persons parameters:
                # If the Cypher uses either $person or $persons and the other is provided,
                # normalize so both are available to prevent "Expected parameter(s)" errors.
                # This is safe as unused parameters are ignored by Neo4j.
                try:
                    # Make a shallow copy to avoid mutating caller's dict
                    params = dict(params)
                    if "persons" in params and "person" not in params:
                        # Provide a single person convenience if a list is supplied
                        lst = params.get("persons") or []
                        if isinstance(lst, (list, tuple)) and lst:
                            params["person"] = lst[0]
                    if "person" in params and "persons" not in params:
                        # Provide a list convenience if single person is supplied
                        p = params.get("person")
                        if isinstance(p, str) and p != "":
                            params["persons"] = [p]
                except Exception:
                    # Do not fail normalization; proceed with original params
                    pass

                result = session.run(query, **params)
                # Safe materialization to list of dict rows
                rows: List[Dict[str, Any]] = [record.data() for record in result]  # type: ignore
                return rows
        except (AuthError, ServiceUnavailable, Neo4jError) as exc:
            raise ValueError(f"Neo4j query failed: {exc}") from exc
        except Exception as exc:
            # Any unexpected error is wrapped as ValueError for the API layer
            raise ValueError(f"Unexpected error running Cypher: {exc}") from exc

    # PUBLIC_INTERFACE
    def close(self) -> None:
        """
        Close the underlying driver (used by tests or shutdown hooks).
        """
        if self._driver is not None:
            try:
                self._driver.close()
            finally:
                self._driver = None


# Create a singleton-like service instance for easy importing
neo4j_service = _Neo4jService()
