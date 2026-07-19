from django.db import migrations, models
import django.db.models.deletion


def create_free_plan(apps, schema_editor):
    PricingPlan = apps.get_model("payments", "PricingPlan")
    PricingPlan.objects.get_or_create(
        name="Free",
        defaults={
            "price_rub": 0,
            "period_days": 30,
            "requests_limit": 3,
            "features": [],
            "is_featured": False,
            "is_active": False,
        },
    )


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0004_payment_months"),
        ("users", "0003_alter_telegramuser_subscription_tier"),
    ]

    operations = [
        migrations.RunPython(create_free_plan, migrations.RunPython.noop),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name="telegramuser",
                    name="subscription_tier",
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="payments.pricingplan",
                        verbose_name="Тариф",
                    ),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql=[
                        "ALTER TABLE users_telegramuser DROP COLUMN subscription_tier;",
                        "ALTER TABLE users_telegramuser ADD COLUMN subscription_tier_id integer NULL REFERENCES payments_pricingplan(id) ON DELETE SET NULL;",
                    ],
                    reverse_sql=[
                        "ALTER TABLE users_telegramuser DROP COLUMN subscription_tier_id;",
                        "ALTER TABLE users_telegramuser ADD COLUMN subscription_tier varchar(50) NOT NULL DEFAULT '';",
                    ],
                ),
            ],
        ),
    ]
