# Generated by Django 2.2.1 on 2019-07-21 15:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trade', '0009_auto_20190721_1926'),
    ]

    operations = [
        migrations.RenameField(
            model_name='order',
            old_name='quality_testing_price',
            new_name='quality_testing_fee',
        ),
        migrations.AlterField(
            model_name='refundapply',
            name='add_time',
            field=models.BigIntegerField(default=1563722722.9748812),
        ),
    ]
