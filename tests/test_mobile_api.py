import os
import unittest

from app import create_app, db
from app.models import User


class MobileApiTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.getenv("DATABASE_URL"):
            raise unittest.SkipTest("DATABASE_URL não configurada para testes de integração.")

        cls.app = create_app()
        cls.client = cls.app.test_client()

        with cls.app.app_context():
            user = User.query.filter_by(email="mobile.test@prp.local").first()
            if not user:
                user = User(
                    nome="Mobile Test",
                    email="mobile.test@prp.local",
                    is_admin=True,
                    deve_alterar_senha=False,
                )
                user.set_password("123456")
                db.session.add(user)
                db.session.commit()

    def _login(self):
        res = self.client.post(
            "/api/mobile/auth/login",
            json={"email": "mobile.test@prp.local", "password": "123456"},
        )
        self.assertEqual(res.status_code, 200)
        payload = res.get_json()
        return payload["data"]["access_token"]

    def test_login_mobile(self):
        res = self.client.post(
            "/api/mobile/auth/login",
            json={"email": "mobile.test@prp.local", "password": "123456"},
        )
        payload = res.get_json()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(payload["status"], "success")
        self.assertIn("access_token", payload["data"])

    def test_dashboard_requires_token(self):
        res = self.client.get("/api/mobile/dashboard")
        payload = res.get_json()
        self.assertEqual(res.status_code, 401)
        self.assertEqual(payload["status"], "error")

    def test_lancamento_rejects_unexpected_fields(self):
        token = self._login()
        res = self.client.post(
            "/api/mobile/lancamentos",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "meio": "cartao",
                "data": "2026-01-01",
                "valor": "10,00",
                "descricao": "Teste",
                "cartao_id": "x",
                "categoria_id": "y",
                "hack_field": "unexpected",
            },
        )
        payload = res.get_json()
        self.assertEqual(res.status_code, 400)
        self.assertEqual(payload["status"], "error")
        self.assertIn("invalid_fields", payload["data"])


if __name__ == "__main__":
    unittest.main()
