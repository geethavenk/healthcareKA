"""
Streamlit frontend for the healthcare knowledge and appointment assistant.
"""

import os
import requests
import steamlit as st
import padas as pd

# Config 
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
API_KEY = os.getenv("FRONTEND_API_KEY", "")

HEADERS = {"x-api-key": API_KEY}

st.set_page_config(page_title="Healthcare Knowledge Assistant", layout="wide")

# API helpers 
def api_get(path:str, params: dict | None = None):
    try:
        resp = requests.get(f"{BACKEND_URL}{path}", headers=HEADERS, params=params, timeout=30)
    except requests.exceptions.ConnectionError:
        st.error(f"Could not reach the backend at {BACKEND_URL}. Is it running?")
        return None
    return _handle_response(resp)

def api_post(path:str, json:dict | None = None, files = None, data = None):
    try:
        resp = requests.post(f"{BACKEND_URL}{path}", headers=HEADERS, json=json, files=files, data=data, timeout=60)
    except requests.exceptions.ConnectionError:
        st.error(f"Could not reach the backend at {BACKEND_URL}. Is it running?")
        return None
    return _handle_response(resp)

def _handle_response(resp: requests.Response):
    if resp.status_code == 429:
        st.warning("Rate limit exceeded. Please try again later.")
        return None
    if resp.status_code == 401:
        st.error("Invalid or missing API key. Check FRONTEND_API_KEY in .env.")
        return None
    if not resp.ok:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        st.error(f"Error {resp.status_code}: {detail}")
        return None
    return resp.json()

# Header
st.title("🏥 Healthcare Knowledge and Appointment Assistant")
st.caption(f"Connected to backend: {BACKEND_URL}")

tabs = st.tabs(["Departments & Doctors", "Patients", "Appointments", "Documents", "Search", "Ask"])

# Tab 1: Departments and Doctors

 with tabs[0]:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Add a Department")
        with st.form("add_department"):
            dept_name = st.text_input("Department name", placeholder="Cardiology")
            dept_desc = st.text_area("Description (optional)")
            if st.form_submit_button("Add Department"):
                result = api_post("/departments", json={"name": dept_name, "description": dept_desc or None})
                if result:
                    st.success(f"Department '{result['name']}' created (id={result['id']}).")

        st.subheader("Existing Departments")
        departments = api_get("/departments")
        if departments:
            st.dataframe(pd.DataFrame(departments), use_container_width=True)

    with col2:
        st.subheader("Add a Doctor")
        departments_for_select = api_get("/departments") or []
        dept_options = {d["name"]: d["id"] for d in departments_for_select}

        with st.form("add_doctor"):
            doc_name = st.text_input("Doctor name", placeholder="Dr. Asha Rao")
            doc_specialty = st.text_input("Specialty", placeholder="Cardiology")
            doc_dept = st.selectbox("Department", options=list(dept_options.keys()) or ["(add a department first)"])
            doc_email = st.text_input("Email (optional)")
            doc_phone = st.text_input("Phone (optional)")
            doc_available = st.checkbox("Available for consultation", value=True)
            if st.form_submit_button("Add Doctor"):
                if not dept_options:
                    st.error("Add a department first.")
                else:
                    result = api_post("/doctors", json={
                        "name": doc_name,
                        "specialty": doc_specialty,
                        "department_id": dept_options[doc_dept],
                        "email": doc_email or None,
                        "phone": doc_phone or None,
                        "available": doc_available,
                    })
                    if result:
                        st.success(f"Doctor '{result['name']}' added (id={result['id']}).")

        st.subheader("Search Doctors by Specialty")
        specialty_query = st.text_input("Specialty contains...", key="specialty_search")
        doctors = api_get("/doctors", params={"specialty": specialty_query} if specialty_query else None)
        if doctors:
            st.dataframe(pd.DataFrame(doctors), use_container_width=True)

# Tab 2: Patients

with tabs[1]:
    st.subheader("Add a Patient")
    with st.form("add_patient"):
        p_name = st.text_input("Patient name")
        p_age = st.number_input("Age", min_value=0, max_value=120, value=30)
        p_gender = st.selectbox("Gender", ["Prefer not to say", "Male", "Female", "Other"])
        p_contact = st.text_input("Contact (phone/email)")
        if st.form_submit_button("Add Patient"):
            result = api_post("/patients", json={
                "name": p_name,
                "age": int(p_age),
                "gender": None if p_gender == "Prefer not to say" else p_gender,
                "contact": p_contact or None,
            })
            if result:
                st.success(f"Patient '{result['name']}' added (id={result['id']}).")

    st.subheader("Existing Patients")
    patients = api_get("/patients")
    if patients:
        st.dataframe(pd.DataFrame(patients), use_container_width=True)

# Tab 3: Appointments
with tabs[2]:
    st.subheader("Book an Appointment")

    patients_for_select = api_get("/patients") or []
    doctors_for_select = api_get("/doctors") or []
    patient_options = {p["name"]: p["id"] for p in patients_for_select}
    doctor_options = {d["name"]: d["id"] for d in doctors_for_select}

    with st.form("book_appointment"):
        sel_patient = st.selectbox("Patient", options=list(patient_options.keys()) or ["(add a patient first)"])
        sel_doctor = st.selectbox("Doctor", options=list(doctor_options.keys()) or ["(add a doctor first)"])
        appt_date = st.date_input("Date")
        appt_time = st.time_input("Time")
        reason = st.text_area("Reason (optional)", placeholder="Follow-up consultation")
        if st.form_submit_button("Book Appointment"):
            if not patient_options or not doctor_options:
                st.error("Add at least one patient and one doctor first.")
            else:
                from datetime import datetime
                appointment_datetime = datetime.combine(appt_date, appt_time).isoformat()
                result = api_post("/appointments", json={
                    "patient_id": patient_options[sel_patient],
                    "doctor_id": doctor_options[sel_doctor],
                    "appointment_date": appointment_datetime,
                    "reason": reason or None,
                })
                if result:
                    st.success(f"Appointment booked for {sel_patient} with {sel_doctor} on {appointment_datetime}.")

    st.subheader("All Appointments")
    appointments = api_get("/appointments")
    if appointments:
        st.dataframe(pd.DataFrame(appointments), use_container_width=True)

 # Tab 4: Documents
with tabs[3]:
    st.subheader("Upload a General Health Information Document")
    st.caption("Supported formats: .pdf, .txt, .md")

    uploaded_file = st.file_uploader("Choose a file", type=["pdf", "txt", "md"])
    custom_title = st.text_input("Custom title (optional)")

    if st.button("Upload Document", disabled=uploaded_file is None):
        files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
        data = {"title": custom_title} if custom_title else {}
        result = api_post("/documents", files=files, data=data)
        if result:
            st.success(f"'{result['title']}' uploaded and split into {result['chunks_created']} chunks.")

    st.subheader("Uploaded Documents")
    documents = api_get("/documents")
    if documents:
        st.dataframe(pd.DataFrame(documents), use_container_width=True)


# Tab 5: Search
with tabs[4]:
    st.subheader("Search Health Information Documents")
    search_query = st.text_input("Search query", placeholder="diabetes symptoms")
    top_k = st.slider("Number of results", min_value=1, max_value=20, value=5)

    if st.button("Search", disabled=not search_query):
        result = api_post("/search", json={"query": search_query, "top_k": top_k})
        if result:
            st.write(f"Results for: **{result['query']}**")
            for item in result["results"]:
                with st.container(border=True):
                    st.markdown(f"**{item['document_title']}**  (similarity: {item['similarity_score']})")
                    st.write(item["chunk_text"])

# Tab 6: Ask (Graph RAG)                    
with tabs[5]:
    st.subheader("Ask a General Health Information Question")
    st.info(
        "This assistant provides general health information only and does not "
        "provide medical diagnosis. Please consult a qualified healthcare "
        "professional for medical advice."
    )

    question = st.text_area("Your question", placeholder="Which department generally handles skin-related problems?")
    ask_top_k = st.slider("Context depth", min_value=1, max_value=20, value=5, key="ask_top_k")

    if st.button("Ask", disabled=not question):
        with st.spinner("Thinking..."):
            result = api_post("/ask", json={"question": question, "top_k": ask_top_k})

        if result:
            st.markdown("### Answer")
            st.write(result["answer"])
            st.caption(result["disclaimer"])

            if result["sources"]:
                st.markdown("### Source Documents Used")
                for item in result["sources"]:
                    with st.container(border=True):
                        st.markdown(f"**{item['document_title']}**  (similarity: {item['similarity_score']})")
                        st.write(item["chunk_text"])

            if result["related_entities"]:
                st.markdown("### Related Graph Entities")
                for entity in result["related_entities"]:
                    if entity.get("relationship") and entity.get("related_to"):
                        st.write(f"- **{entity['type']}** \"{entity['name']}\" --{entity['relationship']}--> \"{entity['related_to']}\"")
                    else:
                        st.write(f"- **{entity['type']}** \"{entity['name']}\"")
                        