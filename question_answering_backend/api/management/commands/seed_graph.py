from django.core.management.base import BaseCommand
from api.neo4j_service import neo4j_service


class Command(BaseCommand):
    help = "Seed a Sachin Tendulkar-centric knowledge graph with entities, relationships and facts."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding Sachin Tendulkar knowledge graph into Neo4j..."))

        # Clear existing demo data for relevant labels
        neo4j_service.run_cypher("MATCH (n:Person) DETACH DELETE n")
        neo4j_service.run_cypher("MATCH (n:Organization) DETACH DELETE n")
        neo4j_service.run_cypher("MATCH (n:Team) DETACH DELETE n")
        neo4j_service.run_cypher("MATCH (n:Country) DETACH DELETE n")
        neo4j_service.run_cypher("MATCH (n:City) DETACH DELETE n")
        neo4j_service.run_cypher("MATCH (n:Record) DETACH DELETE n")
        neo4j_service.run_cypher("MATCH (n:Trophy) DETACH DELETE n")
        neo4j_service.run_cypher("MATCH (n:Format) DETACH DELETE n")
        neo4j_service.run_cypher("MATCH (n:Role) DETACH DELETE n")

        # Create entities and biographical details
        neo4j_service.run_cypher(
            """
            // Core person
            CREATE (sachin:Person {
                name: 'Sachin Tendulkar',
                full_name: 'Sachin Ramesh Tendulkar',
                nickname: 'Little Master',
                batting_style: 'Right-hand bat',
                bowling_style: 'Right-arm offbreak/legbreak',
                birth_year: 1973
            })

            // Places
            CREATE (mumbai:City {name: 'Mumbai'})
            CREATE (maharashtra:Country {name: 'India'})

            // Link city to country (optional hierarchy)
            MERGE (mumbai)-[:IN_COUNTRY]->(maharashtra)

            // Birth and origin
            MERGE (sachin)-[:BORN_IN]->(mumbai)
            MERGE (sachin)-[:BORN_ON {year: 1973, month: 4, day: 24}]->(:Record {type:'BirthDate', label:'24 April 1973'})

            // Teams and organizations
            CREATE (india:Team {name: 'India', level: 'International', sport: 'Cricket'})
            CREATE (mumbaiTeam:Team {name: 'Mumbai', level: 'Domestic', sport: 'Cricket'})
            CREATE (mi:Organization {name: 'Mumbai Indians', type: 'IPL Franchise', sport: 'Cricket'})
            CREATE (bcci:Organization {name: 'BCCI', type: 'Cricket Board'})
            CREATE (icc:Organization {name: 'ICC', type: 'Governing Body'})

            // Roles and formats
            CREATE (batsman:Role {name: 'Batsman'})
            CREATE (opener:Role {name: 'Opening Batsman'})
            CREATE (partTimeBowler:Role {name: 'Part-time Bowler'})
            CREATE (test:Format {name: 'Test'})
            CREATE (odi:Format {name: 'ODI'})
            CREATE (t20i:Format {name: 'T20I'})
            CREATE (ipl:Format {name: 'IPL'})

            // Career associations
            MERGE (sachin)-[:REPRESENTED {from: 1989, to: 2013}]->(india)
            MERGE (sachin)-[:PLAYED_FOR {from: 1988, to: 2013}]->(mumbaiTeam)
            MERGE (sachin)-[:PLAYED_FOR {from: 2008, to: 2013}]->(mi)
            MERGE (sachin)-[:CAPTAINED {format: 'International', from: 1996, to: 2000}]->(india)

            // Debut and Retirement records
            CREATE (testDebut:Record {type:'Debut', format:'Test', year:1989, opponent:'Pakistan', location:'Karachi'})
            CREATE (odiDebut:Record {type:'Debut', format:'ODI', year:1989, opponent:'Pakistan', location:'Gujranwala'})
            CREATE (testRetire:Record {type:'Retirement', format:'Test', year:2013, opponent:'West Indies', location:'Mumbai'})
            CREATE (odiRetire:Record {type:'Retirement', format:'ODI', year:2012, opponent:'Pakistan', location:'Mirpur'})

            MERGE (sachin)-[:DEBUTED_IN]->(testDebut)
            MERGE (sachin)-[:DEBUTED_IN]->(odiDebut)
            MERGE (sachin)-[:RETIRED_IN]->(testRetire)
            MERGE (sachin)-[:RETIRED_IN]->(odiRetire)

            // Roles over the career
            MERGE (sachin)-[:ROLE_AS]->(batsman)
            MERGE (sachin)-[:ROLE_AS]->(opener)
            MERGE (sachin)-[:ROLE_AS]->(partTimeBowler)

            // Notable trophies
            CREATE (cwc2011:Trophy {name:'ICC Cricket World Cup 2011', year:2011})
            MERGE (india)-[:WON]->(cwc2011)
            MERGE (sachin)-[:WON]->(cwc2011)

            // Records (simplified)
            CREATE (recMostODIRuns:Record {type:'CareerRecord', label:'Most ODI runs', value: 18426, unit: 'runs'})
            CREATE (recMostIntlRuns:Record {type:'CareerRecord', label:'Most international runs', value: 34357, unit: 'runs'})
            CREATE (rec100Intl100s:Record {type:'CareerRecord', label:'100 international centuries', value: 100, unit: 'centuries'})
            CREATE (recMostTestRuns:Record {type:'CareerRecord', label:'Most Test runs', value: 15921, unit: 'runs'})
            CREATE (recODIDouble:Record {type:'Milestone', label:'First ODI double century by an Indian', value: 200, unit: 'runs', year:2010, opponent:'South Africa', location:'Gwalior'})

            MERGE (sachin)-[:HOLDS_RECORD]->(recMostODIRuns)
            MERGE (sachin)-[:HOLDS_RECORD]->(recMostIntlRuns)
            MERGE (sachin)-[:HOLDS_RECORD]->(rec100Intl100s)
            MERGE (sachin)-[:HOLDS_RECORD]->(recMostTestRuns)
            MERGE (sachin)-[:HOLDS_RECORD]->(recODIDouble)

            // Format-wise stats (coarse-grained for demo)
            CREATE (testStats:Record {type:'Stats', format:'Test', matches:200, runs:15921, hundreds:51, fifties:68, average:53.78})
            CREATE (odiStats:Record {type:'Stats', format:'ODI', matches:463, runs:18426, hundreds:49, fifties:96, average:44.83})
            CREATE (t20iStats:Record {type:'Stats', format:'T20I', matches:1, runs:10, hundreds:0, fifties:0, average:10.0})
            CREATE (iplStats:Record {type:'Stats', format:'IPL', matches:78, runs:2334, hundreds:1, fifties:13, average:34.83})

            MERGE (sachin)-[:FORMAT_STATS]->(testStats)
            MERGE (sachin)-[:FORMAT_STATS]->(odiStats)
            MERGE (sachin)-[:FORMAT_STATS]->(t20iStats)
            MERGE (sachin)-[:FORMAT_STATS]->(iplStats)

            // Affiliations to governing bodies (useful for generic Q&A)
            MERGE (bcci)-[:GOVERNS]->(india)
            MERGE (icc)-[:GOVERNS]->(bcci)

            // City -> Team link (home association)
            MERGE (mumbai)-[:HOME_TEAM]->(mumbaiTeam)

            // --------------------------------------------
            // Coaching relationships for Sachin Tendulkar
            // --------------------------------------------
            // Add coach persons
            CREATE (achrekar:Person {name:'Ramakant Achrekar'})
            // Optional: Guru/mentor figures (for demo coverage)
            CREATE (gavaskar:Person {name:'Sunil Gavaskar'})

            // Connect coaches to Sachin using both directions for robustness
            MERGE (achrekar)-[:COACHED {from:1984, to:1990}]->(sachin)
            MERGE (sachin)-[:COACHED_BY {from:1984, to:1990}]->(achrekar)

            // Example: Gavaskar as an inspiration/mentor (using COACHED for demo purposes)
            MERGE (gavaskar)-[:COACHED {note:'Mentor/Inspiration'}]->(sachin)
            MERGE (sachin)-[:COACHED_BY {note:'Mentor/Inspiration'}]->(gavaskar)

            RETURN 'ok' AS status
            """
        )

        self.stdout.write(self.style.SUCCESS("Sachin Tendulkar seed complete."))
