import os
import sys
from datetime import datetime

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import HTTPException
from backend.app.database import SessionLocal, Base, engine
from backend.app.models import User, Project, ProjectMember, Document, ExtractedFinding, AuditLog, UserRole, ProjectStatus
from backend.app.schemas import (
    UserRegister, UserLogin, UserUpdate, UserChangePassword,
    ProjectCreate, ProjectUpdate, ProjectMemberAdd, ProjectMemberUpdate
)
from backend.app.routers.auth import register, login, get_me, logout
from backend.app.routers.users import (
    get_current_user_profile, update_current_user_profile, change_password, search_users
)
from backend.app.routers.projects import (
    create_project, list_projects, get_project, update_project,
    archive_project, delete_project, list_project_members,
    add_project_member, update_project_member_role, remove_project_member
)
from backend.app.routers.dashboard import get_dashboard_summary, get_recent_activity

def run_tests():
    db = SessionLocal()
    print("=================================================================")
    print("STARTING PHASE 2 AUTHENTICATION & PROJECT MANAGEMENT TEST SUITE")
    print("=================================================================")

    # Ensure clean state for test accounts
    test_emails = [
        "lead_tester@webhunter.org",
        "second_member@webhunter.org",
        "third_observer@webhunter.org",
        "unauthorized_user@webhunter.org"
    ]
    for email in test_emails:
        u = db.query(User).filter(User.email == email).first()
        if u:
            # Delete memberships, audit logs, and user
            db.query(ProjectMember).filter(ProjectMember.user_id == u.id).delete()
            db.query(AuditLog).filter(AuditLog.user_id == u.id).delete()
            # Delete projects created by this user
            projects = db.query(Project).filter(Project.created_by == u.id).all()
            for p in projects:
                db.query(ProjectMember).filter(ProjectMember.project_id == p.id).delete()
                db.query(Document).filter(Document.project_id == p.id).delete()
                db.query(ExtractedFinding).filter(ExtractedFinding.project_id == p.id).delete()
                db.query(AuditLog).filter(AuditLog.project_id == p.id).delete()
                db.delete(p)
            db.delete(u)
    db.commit()

    # -------------------------------------------------------------
    # 1. USER REGISTRATION
    # -------------------------------------------------------------
    print("\n--- 1. Testing User Registration ---")
    reg_data = UserRegister(
        full_name="Lead Tester",
        email="lead_tester@webhunter.org",
        password="securePassword123",
        confirm_password="securePassword123",
        role="INCOMING_MEMBER"
    )
    token_resp = register(reg_data, db=db)
    assert token_resp.access_token is not None, "Failed: access token missing on register"
    assert token_resp.user.email == "lead_tester@webhunter.org", "Failed: email mismatch"
    print("  [PASS] User registered successfully with JWT access token.")

    # Test duplicate registration rejection
    try:
        register(reg_data, db=db)
        assert False, "Failed: duplicate registration should raise HTTPException"
    except HTTPException as e:
        assert e.status_code == 400, f"Expected 400, got {e.status_code}"
        print(f"  [PASS] Duplicate registration rejected with 400: '{e.detail}'")

    # Test password mismatch rejection
    try:
        mismatch_data = UserRegister(
            full_name="Mismatch User",
            email="mismatch@webhunter.org",
            password="passwordA1",
            confirm_password="passwordB2"
        )
        register(mismatch_data, db=db)
        assert False, "Failed: mismatched password should raise error"
    except (HTTPException, ValueError) as e:
        print("  [PASS] Password mismatch validation rejected properly.")

    # Register second and unauthorized users for later tests
    user2_resp = register(
        UserRegister(
            full_name="Second Member",
            email="second_member@webhunter.org",
            password="securePassword123",
            confirm_password="securePassword123"
        ),
        db=db
    )
    user2 = db.query(User).filter(User.id == user2_resp.user.id).first()

    unauth_resp = register(
        UserRegister(
            full_name="Unauthorized Outsider",
            email="unauthorized_user@webhunter.org",
            password="securePassword123",
            confirm_password="securePassword123"
        ),
        db=db
    )
    unauth_user = db.query(User).filter(User.id == unauth_resp.user.id).first()

    user1 = db.query(User).filter(User.email == "lead_tester@webhunter.org").first()

    # -------------------------------------------------------------
    # 2. USER LOGIN
    # -------------------------------------------------------------
    print("\n--- 2. Testing User Login ---")
    login_resp = login(UserLogin(email="lead_tester@webhunter.org", password="securePassword123"), db=db)
    assert login_resp.access_token is not None, "Failed: access token missing on login"
    assert login_resp.user.email == "lead_tester@webhunter.org"
    print("  [PASS] Login successful with valid credentials.")

    try:
        login(UserLogin(email="lead_tester@webhunter.org", password="wrongPassword"), db=db)
        assert False, "Failed: incorrect password should fail"
    except HTTPException as e:
        assert e.status_code == 401
        print(f"  [PASS] Invalid password rejected with 401: '{e.detail}'")

    # -------------------------------------------------------------
    # 3. CURRENT USER & PROFILE MANAGEMENT
    # -------------------------------------------------------------
    print("\n--- 3. Testing Current User & Profile Management ---")
    me_resp = get_me(current_user=user1)
    assert me_resp.id == user1.id
    assert me_resp.full_name == "Lead Tester"
    assert not hasattr(me_resp, "hashed_password"), "Failed: password hash exposed"
    print("  [PASS] GET /auth/me returns profile without exposing password hash.")

    update_resp = update_current_user_profile(UserUpdate(full_name="Lead Engineer Updated"), db=db, current_user=user1)
    assert update_resp.full_name == "Lead Engineer Updated"
    print("  [PASS] PATCH /users/me updated user full name.")

    # Change password
    pwd_change_resp = change_password(
        UserChangePassword(
            current_password="securePassword123",
            new_password="newSecurePassword456",
            confirm_password="newSecurePassword456"
        ),
        db=db,
        current_user=user1
    )
    assert "updated successfully" in pwd_change_resp["message"]
    print("  [PASS] POST /users/change-password updated password successfully.")

    # Verify new password works
    login_new_resp = login(UserLogin(email="lead_tester@webhunter.org", password="newSecurePassword456"), db=db)
    assert login_new_resp.access_token is not None
    print("  [PASS] Login with new password succeeded.")

    # Search users
    search_results = search_users(q="second_member", db=db, current_user=user1)
    assert len(search_results) >= 1
    assert search_results[0].email == "second_member@webhunter.org"
    print("  [PASS] GET /users/search returned matching user by email query.")

    # -------------------------------------------------------------
    # 4. PROJECT CREATION & AUTOMATIC OWNERSHIP ASSIGNMENT
    # -------------------------------------------------------------
    print("\n--- 4. Testing Project CRUD & Ownership ---")
    p_create = ProjectCreate(
        name="Project Alpha Continuity",
        description="Core knowledge handover for Team Web_hunter",
        category="Engineering",
        status="ACTIVE",
        start_date=datetime.utcnow()
    )
    p_resp = create_project(p_create, db=db, current_user=user1)
    assert p_resp.name == "Project Alpha Continuity"
    assert p_resp.current_user_role == "ADMIN", f"Expected ADMIN, got {p_resp.current_user_role}"
    print(f"  [PASS] Project created successfully. Creator automatically assigned as: {p_resp.current_user_role}")

    # Verify membership table directly
    membership = db.query(ProjectMember).filter(
        ProjectMember.project_id == p_resp.id,
        ProjectMember.user_id == user1.id
    ).first()
    assert membership is not None
    assert membership.role == "ADMIN"
    print("  [PASS] Database ProjectMember verified: Creator has ADMIN role.")

    # List projects for user1
    user1_projects = list_projects(db=db, current_user=user1)
    assert any(p.id == p_resp.id for p in user1_projects), "Created project not in user1 list"
    print(f"  [PASS] User1 lists {len(user1_projects)} accessible project(s).")

    # List projects for unauth_user - must NOT see Project Alpha Continuity
    unauth_projects = list_projects(db=db, current_user=unauth_user)
    assert not any(p.id == p_resp.id for p in unauth_projects), "Data leak: unauth user saw private project!"
    print("  [PASS] Data isolation verified: Unrelated user cannot see private project in list.")

    # Direct access test for unauth_user
    try:
        get_project(project_id=p_resp.id, db=db, current_user=unauth_user)
        assert False, "Failed: unauth user should get 403 Forbidden"
    except HTTPException as e:
        assert e.status_code == 403
        print(f"  [PASS] Direct access denied to non-member with 403: '{e.detail}'")

    # Update project
    p_update = ProjectUpdate(
        name="Project Alpha Continuity (Updated)",
        category="DevOps & Cloud",
        status="ACTIVE"
    )
    p_updated = update_project(project_id=p_resp.id, project_in=p_update, db=db, current_user=user1)
    assert p_updated.name == "Project Alpha Continuity (Updated)"
    assert p_updated.category == "DevOps & Cloud"
    print("  [PASS] Project details updated successfully by project ADMIN.")

    # -------------------------------------------------------------
    # 5. TEAM MANAGEMENT
    # -------------------------------------------------------------
    print("\n--- 5. Testing Team Management ---")
    # Add second user as INCOMING_MEMBER
    member_add = ProjectMemberAdd(
        email="second_member@webhunter.org",
        role="INCOMING_MEMBER"
    )
    added_member = add_project_member(project_id=p_resp.id, member_in=member_add, db=db, current_user=user1)
    assert added_member.user_id == user2.id
    assert added_member.role == "INCOMING_MEMBER"
    print("  [PASS] Added second user by email with role INCOMING_MEMBER.")

    # Verify duplicate member rejection
    try:
        add_project_member(project_id=p_resp.id, member_in=member_add, db=db, current_user=user1)
        assert False, "Failed: adding duplicate member should raise 400"
    except HTTPException as e:
        assert e.status_code == 400
        print(f"  [PASS] Duplicate member rejected with 400: '{e.detail}'")

    # Verify adding unregistered email rejection
    try:
        add_project_member(
            project_id=p_resp.id,
            member_in=ProjectMemberAdd(email="nonexistent_xyz@webhunter.org", role="INCOMING_MEMBER"),
            db=db,
            current_user=user1
        )
        assert False, "Failed: adding nonexistent email should raise 404"
    except HTTPException as e:
        assert e.status_code == 404
        print(f"  [PASS] Non-existent email addition rejected with 404: '{e.detail}'")

    # List members
    members_list = list_project_members(project_id=p_resp.id, db=db, current_user=user1)
    assert len(members_list) == 2, f"Expected 2 members, got {len(members_list)}"
    print(f"  [PASS] Listed {len(members_list)} project members successfully.")

    # Update role: promote second user to PROJECT_MANAGER
    role_update = ProjectMemberUpdate(role="PROJECT_MANAGER")
    updated_role = update_project_member_role(
        project_id=p_resp.id,
        user_id=user2.id,
        role_in=role_update,
        db=db,
        current_user=user1
    )
    assert updated_role.role == "PROJECT_MANAGER"
    print("  [PASS] Updated member role to PROJECT_MANAGER.")

    # Safeguard test: Try to demote sole ADMIN
    try:
        update_project_member_role(
            project_id=p_resp.id,
            user_id=user1.id,
            role_in=ProjectMemberUpdate(role="INCOMING_MEMBER"),
            db=db,
            current_user=user1
        )
        assert False, "Failed: demoting sole ADMIN should fail"
    except HTTPException as e:
        assert e.status_code == 400
        print(f"  [PASS] Safeguard enforced: Cannot demote sole ADMIN: '{e.detail}'")

    # Unauthorized role change: second user (PROJECT_MANAGER) tries to change roles (only ADMIN allowed)
    try:
        update_project_member_role(
            project_id=p_resp.id,
            user_id=user1.id,
            role_in=ProjectMemberUpdate(role="PROJECT_MANAGER"),
            db=db,
            current_user=user2
        )
        assert False, "Failed: non-ADMIN should not be permitted to update roles"
    except HTTPException as e:
        assert e.status_code == 403
        print(f"  [PASS] Unauthorized role change blocked with 403: '{e.detail}'")

    # Remove member
    remove_resp = remove_project_member(project_id=p_resp.id, user_id=user2.id, db=db, current_user=user1)
    assert "successfully" in remove_resp["message"]
    remaining_members = list_project_members(project_id=p_resp.id, db=db, current_user=user1)
    assert len(remaining_members) == 1
    print("  [PASS] Member removed successfully by ADMIN.")

    # -------------------------------------------------------------
    # 6. DASHBOARD SUMMARY & REAL DATABASE METRICS
    # -------------------------------------------------------------
    print("\n--- 6. Testing Real Dashboard Summary & Activity ---")
    dash_summary = get_dashboard_summary(db=db, current_user=user1)
    assert dash_summary.total_projects >= 1
    assert dash_summary.active_projects >= 1
    assert len(dash_summary.recent_projects) >= 1
    assert dash_summary.recent_projects[0].current_user_role == "ADMIN"
    print(f"  [PASS] Dashboard Summary: {dash_summary.total_projects} total project(s), {dash_summary.active_projects} active project(s).")
    print(f"  [PASS] Recent project: '{dash_summary.recent_projects[0].name}' with role '{dash_summary.recent_projects[0].current_user_role}'.")

    # Activity log
    activity_logs = get_recent_activity(db=db, current_user=user1)
    assert len(activity_logs) > 0
    actions = [a.action for a in activity_logs]
    assert "PROJECT_CREATED" in actions
    print(f"  [PASS] Dashboard recent activity contains {len(activity_logs)} real audit log entries (Actions: {list(set(actions))[:4]}).")

    # -------------------------------------------------------------
    # 7. ARCHIVE & DELETE PROJECT
    # -------------------------------------------------------------
    print("\n--- 7. Testing Project Archive & Delete ---")
    archived = archive_project(project_id=p_resp.id, db=db, current_user=user1)
    assert archived.status == "ARCHIVED"
    print("  [PASS] Project archived successfully.")

    # Delete project
    del_resp = delete_project(project_id=p_resp.id, db=db, current_user=user1)
    assert "deleted successfully" in del_resp["message"]
    print(f"  [PASS] {del_resp['message']}")

    # Verify project is gone
    deleted_p = db.query(Project).filter(Project.id == p_resp.id).first()
    assert deleted_p is None
    print("  [PASS] Verified project completely removed from database.")

    # -------------------------------------------------------------
    # 8. LOGOUT
    # -------------------------------------------------------------
    print("\n--- 8. Testing Logout ---")
    logout_resp = logout(current_user=user1, db=db)
    assert "Successfully logged out" in logout_resp["message"]
    print(f"  [PASS] {logout_resp['message']}")

    print("\n=================================================================")
    print("ALL PHASE 2 BACKEND TESTS PASSED WITH 100% SUCCESS!")
    print("=================================================================")
    db.close()

if __name__ == "__main__":
    run_tests()
