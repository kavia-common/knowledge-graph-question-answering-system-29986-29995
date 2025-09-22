from django.core.management.base import BaseCommand
from api.neo4j_service import neo4j_service


class Command(BaseCommand):
    help = "Seed a tiny example knowledge graph for demo and testing."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding example data into Neo4j..."))

        # Wipe demo labels/relationships (keep it simple; use labels used below)
        neo4j_service.run_cypher("MATCH (n:Person) DETACH DELETE n")
        neo4j_service.run_cypher("MATCH (n:Organization) DETACH DELETE n")
        neo4j_service.run_cypher("MATCH (n:Location) DETACH DELETE n")

        # Create sample nodes
        neo4j_service.run_cypher(
            """
            CREATE (alice:Person {name: 'Alice'})
            CREATE (bob:Person {name: 'Bob'})
            CREATE (contoso:Organization {name: 'Contoso'})
            CREATE (globex:Organization {name: 'Globex'})
            CREATE (seattle:Location {name: 'Seattle'})
            CREATE (newyork:Location {name: 'New York'})
            RETURN 1
            """
        )

        # Create relationships
        neo4j_service.run_cypher(
            """
            MATCH (alice:Person {name:'Alice'}),(contoso:Organization {name:'Contoso'})
            CREATE (alice)-[:WORKS_AT]->(contoso)
            """
        )
        neo4j_service.run_cypher(
            """
            MATCH (bob:Person {name:'Bob'}),(globex:Organization {name:'Globex'})
            CREATE (bob)-[:WORKS_AT]->(globex)
            """
        )
        neo4j_service.run_cypher(
            """
            MATCH (alice:Person {name:'Alice'}),(seattle:Location {name:'Seattle'})
            CREATE (alice)-[:LOCATED_IN]->(seattle)
            """
        )
        neo4j_service.run_cypher(
            """
            MATCH (bob:Person {name:'Bob'}),(newyork:Location {name:'New York'})
            CREATE (bob)-[:LOCATED_IN]->(newyork)
            """
        )

        self.stdout.write(self.style.SUCCESS("Seed complete."))
