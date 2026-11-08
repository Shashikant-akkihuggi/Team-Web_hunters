import asyncio
import httpx
from backend.app.main import app

async def run_tests():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        print("1. Testing Health Endpoint...")
        res = await client.get("/health")
        assert res.status_code == 200
        print("   ->", res.json())

        print("2. Testing Admin Login...")
        res = await client.post("/api/auth/login", json={
            "email": "admin@knowledgecontinuity.io",
            "password": "Password123!"
        })
        assert res.status_code == 200, res.text
        data = res.json()
        token = data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("   -> Admin logged in:", data["user"]["full_name"])

        print("3. Testing Projects List...")
        res = await client.get("/api/projects", headers=headers)
        assert res.status_code == 200
        projects = res.json()
        print(f"   -> Found {len(projects)} projects. First: {projects[0]['name']}")
        project_id = projects[0]["id"]

        print("4. Testing Findings List...")
        res = await client.get(f"/api/knowledge/{project_id}/findings", headers=headers)
        assert res.status_code == 200
        findings = res.json()
        print(f"   -> Retrieved {len(findings)} findings.")

        print("5. Testing Handover Detail...")
        res = await client.get(f"/api/handovers/{project_id}", headers=headers)
        assert res.status_code == 200
        handovers = res.json()
        handover_id = handovers[0]["id"]
        print(f"   -> Handover status: {handovers[0]['status']}")

        print("6. Testing PDF Export...")
        res = await client.get(f"/api/handovers/{project_id}/{handover_id}/export-pdf", headers=headers)
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/pdf"
        print(f"   -> PDF Export verified! Size: {len(res.content)} bytes.")

        print("\nSUCCESS: All async ASGI tests passed!")

if __name__ == "__main__":
    asyncio.run(run_tests())
