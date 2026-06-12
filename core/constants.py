"""Shared enumerations used across modules."""

# ---- Roles (RBAC) ----
ROLE_SUPER_ADMIN = "super_admin"
ROLE_ADMIN = "admin"
ROLE_PROJECT_MANAGER = "project_manager"
ROLE_TEAM_LEADER = "team_leader"
ROLE_EMPLOYEE = "employee"

ROLES = [
    ROLE_SUPER_ADMIN,
    ROLE_ADMIN,
    ROLE_PROJECT_MANAGER,
    ROLE_TEAM_LEADER,
    ROLE_EMPLOYEE,
]

ROLE_LABELS = {
    ROLE_SUPER_ADMIN: "Super Admin",
    ROLE_ADMIN: "Admin",
    ROLE_PROJECT_MANAGER: "Project Manager",
    ROLE_TEAM_LEADER: "Team Leader",
    ROLE_EMPLOYEE: "Employee",
}

# Privilege ranking — higher number = more power.
ROLE_RANK = {
    ROLE_EMPLOYEE: 1,
    ROLE_TEAM_LEADER: 2,
    ROLE_PROJECT_MANAGER: 3,
    ROLE_ADMIN: 4,
    ROLE_SUPER_ADMIN: 5,
}

MANAGEMENT_ROLES = [ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_PROJECT_MANAGER]

# Roles that can see *every* project and task. Everyone else — including
# admins and project managers — is scoped to the projects/tasks they own,
# manage, are assigned to, or are a team member of. Intentionally narrower
# than MANAGEMENT_ROLES (which still governs who may create/edit/delete).
FULL_VISIBILITY_ROLES = [ROLE_SUPER_ADMIN]

# Roles allowed to manually override a task's actual (logged) hours.
ACTUAL_HOURS_EDIT_ROLES = [ROLE_SUPER_ADMIN, ROLE_PROJECT_MANAGER]

# ---- Employee status ----
EMPLOYEE_STATUSES = ["active", "inactive", "suspended"]

# ---- Project ----
PROJECT_STATUSES = ["planning", "active", "completed", "on_hold"]
PROJECT_STATUS_LABELS = {
    "planning": "Planning",
    "active": "Active",
    "completed": "Completed",
    "on_hold": "On Hold",
}
PRIORITIES = ["low", "medium", "high", "critical"]
PRIORITY_LABELS = {
    "low": "Low",
    "medium": "Medium",
    "high": "High",
    "critical": "Critical",
}

# ---- Task ----
TASK_STATUSES = ["todo", "in_progress", "review", "testing", "completed", "rejected"]
KANBAN_COLUMNS = ["todo", "in_progress", "review", "testing", "completed"]

STATUS_LABELS = {
    "todo": "Todo",
    "in_progress": "In Progress",
    "review": "Review",
    "testing": "Testing",
    "completed": "Completed",
    "rejected": "Rejected",
}

# ---- Performance: KRA (Key Result Area) / KPI (Key Performance Indicator) ----
PERF_KIND_KRA = "kra"
PERF_KIND_KPI = "kpi"
PERF_KINDS = [PERF_KIND_KRA, PERF_KIND_KPI]
PERF_KIND_LABELS = {
    PERF_KIND_KRA: "KRA",
    PERF_KIND_KPI: "KPI",
}
PERF_KIND_FULL_LABELS = {
    PERF_KIND_KRA: "Key Result Area",
    PERF_KIND_KPI: "Key Performance Indicator",
}
PERF_STATUSES = ["not_started", "in_progress", "achieved", "not_achieved"]
PERF_STATUS_LABELS = {
    "not_started": "Not Started",
    "in_progress": "In Progress",
    "achieved": "Achieved",
    "not_achieved": "Not Achieved",
}

# ---- Employee Error tracking (super-admin only) ----
ERROR_SEVERITIES = ["low", "medium", "high", "critical"]
ERROR_SEVERITY_LABELS = {
    "low": "Low",
    "medium": "Medium",
    "high": "High",
    "critical": "Critical",
}
ERROR_STATUSES = ["open", "resolved"]
ERROR_STATUS_LABELS = {
    "open": "Open",
    "resolved": "Resolved",
}

# ---- Activity log verbs ----
ACTIVITY_TASK_CREATED = "task_created"
ACTIVITY_TASK_ASSIGNED = "task_assigned"
ACTIVITY_TASK_UPDATED = "task_updated"
ACTIVITY_STATUS_CHANGED = "status_changed"
ACTIVITY_COMMENT_ADDED = "comment_added"
ACTIVITY_FILE_UPLOADED = "file_uploaded"

# ---- Notification types ----
NOTIF_TASK_ASSIGNED = "task_assigned"
NOTIF_TASK_UPDATED = "task_updated"
NOTIF_TASK_COMPLETED = "task_completed"
NOTIF_COMMENT_MENTION = "comment_mention"
NOTIF_DUE_DATE = "due_date_reminder"
