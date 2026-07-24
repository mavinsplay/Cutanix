from django.test import TestCase, Client
from django.urls import reverse
from users.models import TelegramUser
from payments.models import PricingPlan, Payment
from payments.platega import Platega, PlategaCallback


class PlategaPaymentTests(TestCase):
    def setUp(self):
        self.user = TelegramUser.objects.create(
            telegram_id=123456789,
            username="testuser",
            first_name="Test",
        )
        self.plan = PricingPlan.objects.create(
            name="Ultra",
            price_rub=499,
            period_days=30,
            requests_limit=100,
            features=["Unlimited scan"],
            is_featured=True,
            is_active=True,
        )
        self.client = Client()

    def test_payment_creation(self):
        # Create payment via API
        response = self.client.post(
            "/api/payment/create/",
            data={
                "plan_id": self.plan.id,
                "months": 1,
                "payment_method": Platega.METHOD_CARD_RU,
            },
            content_type="application/json",
            HTTP_X_TELEGRAM_INIT_DATA=f"user=%7B%22id%22%3A123456789%7D",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("redirect", data)
        self.assertIn("payment_id", data)

        # Check Payment object in DB
        payment = Payment.objects.get(id=data["payment_id"])
        self.assertEqual(payment.user, self.user)
        self.assertEqual(payment.plan, self.plan)
        self.assertEqual(payment.status, "pending")
        self.assertEqual(payment.payment_method, Platega.METHOD_CARD_RU)

    def test_payment_status_check_and_demo_activation(self):
        payment = Payment.objects.create(
            user=self.user,
            plan=self.plan,
            amount_kopeks=49900,
            months=1,
            payment_method=Platega.METHOD_SBP_QR,
            status="pending",
        )
        response = self.client.get(f"/api/payment/status/{payment.id}/?demo=1")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "succeeded")
        self.assertEqual(data["plan_name"], "Ultra")

        # Verify user subscription activated
        self.user.refresh_from_db()
        self.assertEqual(self.user.subscription_tier, self.plan)
        self.assertEqual(self.user.requests_limit, 100)

    def test_payment_callback_webhook(self):
        payment = Payment.objects.create(
            user=self.user,
            plan=self.plan,
            amount_kopeks=49900,
            months=1,
            payment_method=Platega.METHOD_CRYPTO,
            status="pending",
        )
        callback_payload = {
            "id": "tx-uuid-12345",
            "amount": 499,
            "currency": "RUB",
            "status": Platega.STATUS_CONFIRMED,
            "paymentMethod": Platega.METHOD_CRYPTO,
            "payload": str(payment.id),
        }
        response = self.client.post(
            "/api/payment/callback/",
            data=callback_payload,
            content_type="application/json",
            HTTP_X_MERCHANTID="your-merchant-id",
            HTTP_X_SECRET="your-secret-key",
        )
        self.assertEqual(response.status_code, 200)

        payment.refresh_from_db()
        self.assertEqual(payment.status, "succeeded")
        self.user.refresh_from_db()
        self.assertEqual(self.user.subscription_tier, self.plan)
