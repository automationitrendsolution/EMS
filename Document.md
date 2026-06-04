# PROJECT NAME

iTrendTASKS

# PROJECT OVERVIEW

Build a production-ready Employee Task Management Software using:

Backend:
- Django 5+
- Django REST Framework

Database:
- MongoDB (MongoEngine)

Frontend:
- Django Templates
- Bootstrap 5
- JavaScript
- AJAX

Containerization:
- Docker
- Docker Compose

Web Server:
- Nginx

Realtime:
- Django Channels
- WebSocket

The system should focus ONLY on task and project management.

Do not implement Payroll, Attendance, Leave Management, Recruitment, Accounting, CRM, or HRMS features.

---

# USER ROLES

1. Super Admin
2. Admin
3. Project Manager
4. Team Leader
5. Employee

Implement Role Based Access Control (RBAC).

---

# MODULE 1: EMPLOYEE MANAGEMENT

Features:

- Employee Registration
- Employee Profile
- Department
- Designation
- Team Assignment
- Employee Status

Fields:

- Employee ID
- Full Name
- Email
- Phone
- Department
- Designation
- Profile Image
- Status

---

# MODULE 2: PROJECT MANAGEMENT

Features:

- Create Project
- Edit Project
- Archive Project
- Delete Project

Fields:

- Project Name
- Description
- Start Date
- End Date
- Status
- Priority
- Manager
- Team Members

Status:

- Planning
- Active
- Completed
- On Hold

---

# MODULE 3: TASK MANAGEMENT

Features:

- Create Task
- Assign Task
- Reassign Task
- Clone Task
- Delete Task
- Bulk Assign Tasks
- Bulk Status Update

Fields:

- Task ID
- Task Title
- Description
- Project
- Assigned Employee
- Reporter
- Priority
- Status
- Due Date
- Estimated Hours
- Actual Hours
- Tags

Task Status:

- Todo
- In Progress
- Review
- Testing
- Completed
- Rejected

Priority:

- Low
- Medium
- High
- Critical

---

# MODULE 4: SUBTASK MANAGEMENT

Each task can have unlimited subtasks.

Features:

- Add Subtask
- Complete Subtask
- Delete Subtask

Automatically calculate task completion percentage.

Progress Formula:

Progress =
Completed Subtasks / Total Subtasks × 100

---

# MODULE 5: KANBAN BOARD

Build Trello-like board.

Columns:

- Todo
- In Progress
- Review
- Testing
- Completed

Requirements:

- Drag and Drop
- Realtime Update
- Filter
- Search

Use Bootstrap + JavaScript + WebSockets.

---

# MODULE 6: TASK COMMENTS

Features:

- Add Comment
- Edit Comment
- Delete Comment
- Mention Employees

Example:

@rajesh Please update API status.

---

# MODULE 7: FILE ATTACHMENTS

Allow:

- PDF
- DOCX
- XLSX
- ZIP
- PNG
- JPG

Attach files to:

- Projects
- Tasks
- Comments

Store files in Docker volume.

---

# MODULE 8: TASK TIME TRACKING

Features:

- Start Timer
- Stop Timer
- Pause Timer
- Resume Timer

Store:

- Start Time
- End Time
- Total Duration

Generate:

- Employee Time Report
- Project Time Report

---

# MODULE 9: TASK ACTIVITY LOG

Track:

- Task Created
- Task Assigned
- Task Updated
- Task Status Changed
- Comment Added
- File Uploaded

Display activity timeline.

Example:

09:15 AM
Rajesh changed status from Todo → In Progress

09:30 AM
Rajesh uploaded API_Document.pdf

---

# MODULE 10: DASHBOARD

Admin Dashboard:

Show:

- Total Projects
- Active Projects
- Total Tasks
- Pending Tasks
- Completed Tasks
- Overdue Tasks
- Employee Workload

Charts:

- Task Status
- Project Progress
- Employee Performance

---

# MODULE 11: NOTIFICATIONS

Realtime Notifications

Events:

- Task Assigned
- Task Updated
- Task Completed
- Comment Mention
- Due Date Reminder

Use Django Channels.

---

# MODULE 12: REPORTS

Generate:

- Task Report
- Project Report
- Employee Report
- Productivity Report

Export:

- PDF
- Excel
- CSV

---

# MODULE 13: AI TASK ASSISTANT

Use OpenAI API.

Features:

### AI Task Breakdown

Input:

Build E-Commerce Website

Output:

- Requirement Analysis
- UI Design
- Product Module
- Cart Module
- Payment Integration
- Testing
- Deployment

---

### AI Task Summary

Summarize:

- Task Description
- Comments
- Progress

Generate short status reports.

---

### AI Project Health Analysis

Analyze:

- Pending Tasks
- Delayed Tasks
- Deadlines

Output:

Project Status:
At Risk

Reason:
15 tasks overdue.

Suggestion:
Allocate additional resources.

---

# API REQUIREMENTS

Create REST APIs for:

- Authentication
- Projects
- Tasks
- Subtasks
- Comments
- Attachments
- Notifications
- Reports

Features:

- Search
- Filter
- Pagination
- Sorting

Generate Swagger Documentation.

---

# FRONTEND REQUIREMENTS

Use:

- Bootstrap 5 Admin Dashboard
- Responsive Design
- Dark Mode
- Mobile Friendly UI

Pages:

- Login
- Dashboard
- Projects
- Project Details
- Task Board
- My Tasks
- Team Tasks
- Reports
- Settings

---

# DOCKER REQUIREMENTS

Create:

docker-compose.yml

Services:

- django
- mongodb
- redis
- celery
- celery-beat
- nginx

Volumes:

- mongodb_data
- media_data
- static_data

Production Ready Setup Required.

---

# SECURITY

Implement:

- JWT Authentication
- CSRF Protection
- XSS Protection
- Rate Limiting
- Secure File Upload
- Audit Logging

---

# OUTPUT REQUIREMENTS

Generate:

1. Complete Folder Structure
2. MongoDB Schema Design
3. Django Models
4. API Endpoints
5. Views
6. Forms
7. Bootstrap Templates
8. JavaScript Files
9. WebSocket Implementation
10. Docker Setup
11. Unit Tests
12. Production Deployment Guide

Build it like a modern SaaS application similar to Jira, Trello, ClickUp, and Asana.