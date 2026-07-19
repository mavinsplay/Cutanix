from django.db import migrations, models
import django.db.models.deletion


def clear_tier_text(apps, schema_editor):
    TelegramUser = apps.get_model("users", "TelegramUser")
    TelegramUser.objects.update(subscription_tier=None)


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0004_payment_months"),
        ("users", "0003_alter_telegramuser_subscription_tier"),
    ]

    operations = [
        migrations.RunPython(clear_tier_text, migrations.RunPython.noop),
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
    ]
