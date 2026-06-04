from accounts.auth import decode_token, make_token_pair
from accounts.models import User
from accounts.services import create_user, next_employee_id
from core.testutils import MongoTestCase


class UserModelTests(MongoTestCase):
    def test_password_hash_and_check(self):
        u = create_user(full_name="Test", email="t@example.com", password="secret123")
        self.assertNotEqual(u.password_hash, "secret123")
        self.assertTrue(u.check_password("secret123"))
        self.assertFalse(u.check_password("wrong"))

    def test_employee_id_increments(self):
        create_user(full_name="A", email="a@x.com", password="pw123456")
        second = next_employee_id()
        self.assertEqual(second, "EMP0002")

    def test_jwt_round_trip(self):
        u = create_user(full_name="J", email="j@x.com", password="pw123456")
        tokens = make_token_pair(u)
        payload = decode_token(tokens["access"])
        self.assertEqual(payload["sub"], str(u.id))
        self.assertEqual(payload["type"], "access")


class AuthAPITests(MongoTestCase):
    def setUp(self):
        super().setUp()
        self.user = create_user(
            full_name="Admin", email="admin@x.com", password="admin12345",
            role="super_admin",
        )

    def test_login_success(self):
        res = self.client.post(
            "/api/v1/auth/login/",
            data={"email": "admin@x.com", "password": "admin12345"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("access", res.json())

    def test_login_bad_password(self):
        res = self.client.post(
            "/api/v1/auth/login/",
            data={"email": "admin@x.com", "password": "nope"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 401)

    def test_me_requires_auth(self):
        res = self.client.get("/api/v1/auth/me/")
        self.assertIn(res.status_code, (401, 403))

    def test_me_with_token(self):
        tokens = make_token_pair(self.user)
        res = self.client.get(
            "/api/v1/auth/me/", HTTP_AUTHORIZATION=f"Bearer {tokens['access']}"
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["email"], "admin@x.com")
