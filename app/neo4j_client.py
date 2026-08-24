"""
Neo4j graph client 

Stores entities (Doctor, Department, Patient, Appointment, Symptom) as nodes and
their relationships:
    (Doctor)-[:WORKS_IN]->(Department)
    (Patient)-[:BOOKED]->(Appointment)
    (Appointment)-[:ASSIGNED_TO]->(Doctor)
    (Symptom)-[:RELATED_TO]->(Department)

Postgres holds structures attributes and Neo4j holds the relationship graph.
"""

from neo4j import GraphDatabase
from config import settings

# Driver - one shared connection pool for the whole app lifetime
# created on the first use and closed on app shutdown

_driver = None

def get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
    return _driver

def close_driver() -> None:
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


def verify_connectivity() -> bool:
    """Used by GET /health to report whether Neo4j is reachable."""

    try:
        get_driver().verify_connectivity()
        return True
    except Exception:
        return False

# WRITE functions - mirrows SQL writes into the graph

def create_department_node(department_id:int, name:str) -> None:
    query = """
    MERGE (d:Department {id: $id})
    SET d.name = $name
    """
    with get_driver().session() as session:
        session.run(query, id=department_id, name=name)


def create_doctor_node(doctor_id:int, name:str, specialty:str, department_id:int) -> None:
    query = """
    MERGE (doc:Doctor {id: $doctor_id})
    SET doc.name = $name, doc.specialty = $specialty
    WITH doc
    MATCH (dep:Department {id: $department_id})
    MERGE (doc)-[:WORKS_IN]->(dep)
    """
    with get_driver().session() as session:
        session.run(
            query, 
            doctor_id=doctor_id,
            name=name,
            specialty=specialty,
            department_id=department_id
        )


def create_patient_node(patient_id:int, name:str) -> None:
    query = """
    MERGE (p:Patient {id:$id})
    SET p.name = $name
    """
    with get_driver().session() as session:
        session.run(query, id=patient_id, name=name)


def create_appointment_node(
        appointment_id: int,
        patient_id: int,
        doctor_id: int,
        appointment_date: str,
) -> None:
    query = """
    MERGE (a:Appointment {id:$appointment_id})
    SET a.date = $appointment_date
    WITH a
    MATCH (p:Patient {id:$patient_id})
    MATCH (doc:Doctor {id:$doctor_id})
    MERGE (p)-[:BOOKED]->(a)
    MERGE (a)-[:ASSIGNED_TO]->(doc)
    """
    with get_driver().session() as session:
        session.run(
            query, 
            appointment_id=appointment_id,
            patient_id=patient_id,
            doctor_id=doctor_id,
            appointment_date=appointment_date
        )


def link_symptom_to_department(symptom_name:str, department_name:str) -> None:
    """
    Seeds general knowledge like (Symptom {name: 'skin rash'})-[:RELATED_TO]->(Department {name: 'Dermatology'}).
    Used so /ask can anser "which department handles X probelems" style questions.

    The department must already exist as a node. We MATCH rather than MERGE it, because
    create_department_node() keys Department on id - merging on name here would create a
    second, name-only Department node instead of finding the existing one.
    """
    query="""
    MATCH (dep:Department {name: $department_name})
    MERGE (s:Symptom {name: $symptom_name})
    MERGE (s)-[:RELATED_TO]->(dep)
    """
    with get_driver().session() as session:
        session.run(query, symptom_name=symptom_name, department_name=department_name)


# READ FUNCTIONS 

def get_doctors_by_specialty(specialty:str) -> list[dict]:
    query="""
    MATCH (doc:Doctor)-[:WORKS_IN]->(dep:Department)
    WHERE toLower(doc.specialty) CONTAINS toLower($specialty)
    RETURN doc.id AS id, doc.name AS name, doc.specialty AS specialty, dep.name AS department
    """
    with get_driver().session() as session:
        result = session.run(query, specialty=specialty)
        return [dict(record) for record in result]

def get_symptom_links() -> list[dict]:
    """Every seeded (Symptom)-[:RELATED_TO]->(Department) pair, for GET /symptoms."""
    query="""
    MATCH (s:Symptom)-[:RELATED_TO]->(dep:Department)
    RETURN s.name AS symptom, dep.name AS department
    ORDER BY symptom
    """
    with get_driver().session() as session:
        result = session.run(query)
        return [dict(record) for record in result]


def get_related_entities(keywords: list[str], limit:int = 10) -> list[dict]:
    """
    Given keywords that are pulled from a user's question, traverse the graph to find relevant
    entities and how they connect. Matches keywords againt Symptom, Department, and Doctor
    node names/specialties, then returns each match plus one hop of its relationships i.e., 
    matching node plus whats directly connected to it.

    Returns a flat list of dicts shaped like schemas.RelatedEntity:
        {"type": ..., "name": ..., "relationship": ..., "related_to": ...}
    """
    if not keywords:
        return []

    query = """
    UNWIND $keywords AS kw
    MATCH (n)
    WHERE (n:Symptom OR n:Department OR n:Doctor)
        AND (toLower(n.name) CONTAINS toLower(kw) OR toLower(coalesce(n.specialty, '')) CONTAINS toLower (kw))
    OPTIONAL MATCH (n)-[r]-(m)
    RETURN DISTINCT labels(n)[0] AS type, n.name AS name,
        type(r) AS relationship, m.name AS related_to
    LIMIT $limit        
    """
    with get_driver().session() as session:
        result = session.run(query, keywords=keywords, limit=limit)
        return [dict(record) for record in result]