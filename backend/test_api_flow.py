import os
from fastapi.testclient import TestClient
from backend.app.main import app

def test_complete_flow():
    with TestClient(app) as client:
        print("1. Testing Health Endpoint...")
        res = client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"
        print("   Health OK!")

        print("2. Testing Login with Admin...")
        res = client.post("/api/auth/login", json={
            "email": "admin@knowledgecontinuity.io",
            "password": "Password123!"
        })
        assert res.status_code == 200, res.text
        admin_token = res.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        print("   Admin Login OK! Token acquired.")

        print("3. Testing Projects Listing...")
        res = client.get("/api/projects", headers=admin_headers)
        assert res.status_code == 200
        projects = res.json()
        assert len(projects) > 0
        project_id = projects[0]["id"]
        print(f"   Project found: {projects[0]['name']} (Readiness: {projects[0]['readiness_score']}%)")

        print("4. Testing Findings & Evidence Retrieval...")
        res = client.get(f"/api/knowledge/{project_id}/findings", headers=admin_headers)
        assert res.status_code == 200
        findings = res.json()
        assert len(findings) > 0
        print(f"   Total findings retrieved: {len(findings)}")
        conflicts = [f for f in findings if f["verification_status"] == "CONFLICTING"]
        print(f"   Conflicting findings detected: {len(conflicts)}")

        print("5. Testing Timeline Endpoint...")
        res = client.get(f"/api/knowledge/{project_id}/timeline", headers=admin_headers)
        assert res.status_code == 200
        timeline = res.json()
        print(f"   Timeline items: {len(timeline)}")

        print("6. Testing Risks and Dependencies Endpoint...")
        res = client.get(f"/api/knowledge/{project_id}/risks-dependencies", headers=admin_headers)
        assert res.status_code == 200
        risks_deps = res.json()
        print(f"   Risks: {len(risks_deps['risks'])}, Blockers: {len(risks_deps['blockers'])}, Dependencies: {len(risks_deps['dependencies'])}")

        print("7. Testing Handover Listing and PDF Export...")
        res = client.get(f"/api/handovers/{project_id}", headers=admin_headers)
        assert res.status_code == 200
        handovers = res.json()
        assert len(handovers) > 0
        handover_id = handovers[0]["id"]
        print(f"   Handover ID: {handover_id} (Status: {handovers[0]['status']})")

        res = client.get(f"/api/handovers/{project_id}/{handover_id}/export-pdf", headers=admin_headers)
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/pdf"
        assert len(res.content) > 1000
        print(f"   PDF generated successfully! Size: {len(res.content)} bytes.")

        print("8. Testing Incoming Member Role Enforcement...")
        res = client.post("/api/auth/login", json={
            "email": "incoming@knowledgecontinuity.io",
            "password": "Password123!"
        })
        assert res.status_code == 200
        incoming_token = res.json()["access_token"]
        incoming_headers = {"Authorization": f"Bearer {incoming_token}"}

        # Incoming member viewing approved handovers: should succeed
        res = client.get(f"/api/handovers/{project_id}/{handover_id}", headers=incoming_headers)
        assert res.status_code == 200
        print("   Incoming Member successfully viewed authorized approved handover!")

        # Incoming member attempting to review findings: should be forbidden (403)
        res = client.get(f"/api/review/{project_id}/queue", headers=incoming_headers)
        assert res.status_code == 403
        print("   Incoming Member properly blocked from Review Queue (403 Forbidden).")

        print("9. Testing Dashboard Analytics...")
        res = client.get("/api/analytics/dashboard", headers=admin_headers)
        assert res.status_code == 200
        stats = res.json()
        print(f"   Total Projects: {stats['total_projects']}, Documents: {stats['total_documents']}, Findings: {stats['total_findings']}")

        print("\nALL BACKEND API FLOW TESTS PASSED WITH 100% SUCCESS!")

if __name__ == "__main__":
    test_complete_flow()
