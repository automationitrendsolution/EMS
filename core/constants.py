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

# ---- Employee status ----
EMPLOYEE_STATUSES = ["active", "inactive", "suspended"]

# ---- Project ----
PROJECT_STATUSES = ["planning", "active", "completed", "on_hold"]
PRIORITIES = ["low", "medium", "high", "critical"]

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
