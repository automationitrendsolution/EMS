"""Generic helpers: serialization, file validation, mentions."""
import os
import re
import uuid

from django.conf import settings
from django.core.files.storage import default_storage

MENTION_RE = re.compile(r"@([A-Za-z0-9_.-]+)")


def oid(value):
    """Stringify an ObjectId / document, tolerant of None."""
    return str(value) if value is not None else None


def doc_brief(user):
    """Compact public representation of a user document."""
    if not user:
        return None
    return {
        "id": str(user.id),
        "employee_id": user.employee_id,
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
        "profile_image": user.profile_image_url,
    }


def extract_mentions(text):
    """Return the set of @usernames referenced in text."""
    return set(MENTION_RE.findall(text or ""))


def validate_upload(uploaded_file):
    """Raise ValueError if the file violates extension / size policy."""
    name = uploaded_file.name
    ext = os.path.splitext(name)[1].lower().lstrip(".")
    if ext not in settings.ALLOWED_UPLOAD_EXTENSIONS:
        raise ValueError(
            f"File type '.{ext}' not allowed. "
            f"Allowed: {', '.join(settings.ALLOWED_UPLOAD_EXTENSIONS)}"
        )
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if uploaded_file.size > max_bytes:
        raise ValueError(f"File exceeds {settings.MAX_UPLOAD_SIZE_MB} MB limit.")
    return ext


def save_upload(uploaded_file, subdir="attachments"):
    """Persist an uploaded file under MEDIA_ROOT with a randomized name.

    Returns ``(relative_path, original_name, size, content_type)``.
    """
    ext = validate_upload(uploaded_file)
    safe_name = f"{uuid.uuid4().hex}.{ext}"
    rel_path = os.path.join(subdir, safe_name)
    saved = default_storage.save(rel_path, uploaded_file)
    return saved, uploaded_file.name, uploaded_file.size, uploaded_file.content_type


def media_url(rel_path):
    if not rel_path:
        return None
    return settings.MEDIA_URL + rel_path
