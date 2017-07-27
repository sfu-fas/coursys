from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import models
import os


def filename(path):
    return os.path.split(path)[1]


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('app', type=str, help='the app to work in')
        parser.add_argument('model', type=str, help='the model class to work on')
        parser.add_argument('field', type=str, help='the FileField in the model')

    def handle(self, *args, **options):
        raise NotImplementedError("This isn't even close to done.")
        app_name = options['app']
        model_name = options['model']
        field_name = options['field']

        model = apps.get_model(app_name, model_name)
        fields = model._meta.get_fields()
        matching_fields = [f for f in fields if isinstance(f, models.FileField) and f.name == field_name]
        field = matching_fields[0]

        for o in model.objects.all():
            fld = getattr(o, field_name)
            old_loc = fld.file.name
            new_loc = field.upload_to(o, filename(old_loc))
            if old_loc == new_loc:
                continue

            print(new_loc)
            print(os.path.split(new_loc))

