# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0002_asset_location'),
    ]

    operations = [
        migrations.AddField(
            model_name='asset',
            name='category',
            field=models.CharField(default='GEN', max_length=4, null=True, blank=True, choices=[('BANN', 'Banners'), ('DISP', 'Display'), ('BROC', 'Brochures'), ('SWAG', 'Swag'), ('GEN', 'General'), ('EVEN', 'Events')]),
        ),
        migrations.AddField(
            model_name='asset',
            name='min_qty',
            field=models.PositiveIntegerField(help_text='The minimum quantity that should be in stock before having to re-order', null=True, verbose_name='Minimum re-order quantity', blank=True),
        ),
        migrations.AddField(
            model_name='asset',
            name='price',
            field=models.DecimalField(null=True, max_digits=8, decimal_places=2, blank=True),
        ),
        migrations.AddField(
            model_name='asset',
            name='qty_ordered',
            field=models.PositiveIntegerField(null=True, verbose_name='Quantity on order', blank=True),
        ),
        migrations.AddField(
            model_name='asset',
            name='quantity',
            field=models.PositiveIntegerField(null=True, blank=True),
        ),
    ]
