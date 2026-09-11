from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='CscCenter',
            fields=[
                ('id', models.CharField(max_length=64, primary_key=True, serialize=False)),
                ('name', models.JSONField()),
                ('address', models.JSONField()),
                ('locality', models.CharField(blank=True, default='', max_length=200)),
                ('city', models.CharField(blank=True, default='', max_length=100)),
                ('taluk', models.CharField(blank=True, default='', max_length=100)),
                ('pincode', models.CharField(max_length=6)),
                ('lat', models.FloatField()),
                ('lng', models.FloatField()),
                ('phone', models.CharField(blank=True, max_length=20, null=True)),
                ('hours', models.JSONField(blank=True, null=True)),
            ],
            options={
                'ordering': ['id'],
            },
        ),
        migrations.CreateModel(
            name='PincodeCentroid',
            fields=[
                ('pincode', models.CharField(max_length=6, primary_key=True, serialize=False)),
                ('lat', models.FloatField()),
                ('lng', models.FloatField()),
            ],
            options={
                'ordering': ['pincode'],
            },
        ),
    ]
