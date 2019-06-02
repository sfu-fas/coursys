from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import models
import os, re
from threading import Thread


uuid_re = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')


def move_file(model, storage, field_name, field, o):
    fld = getattr(o, field_name)

    old_loc = fld.name
    if not old_loc:
        # null in optional field: nothing to do.
        return

    new_loc = field.upload_to(o, os.path.split(old_loc)[1])
    old_loc_full = storage.path(old_loc)
    new_loc_full = storage.path(new_loc)
    old_dir = os.path.split(old_loc_full)[0]
    new_dir = os.path.split(new_loc_full)[0]

    if old_loc == new_loc or uuid_re.search(old_loc):
        # already in place or contains a UUID (i.e. is probably new format already)
        return

    # link/move/unlink ensures that this can be safely interrupted
    print(('%s > %s' % (old_loc, new_loc)))
    os.makedirs(new_dir)
    os.link(old_loc_full, new_loc_full)
    up = {field_name: new_loc}
    model.objects.filter(pk=o.pk).update(**up)  # avoid any .save() logic
    os.remove(old_loc_full)

    # clean up newly-empty directories
    while not os.listdir(old_dir):
        os.rmdir(old_dir)
        old_dir = os.path.split(old_dir)[0]


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('app', type=str, help='the app to work in')
        parser.add_argument('model', type=str, help='the model class to work on')
        parser.add_argument('field', type=str, help='the FileField in the model')

    def handle(self, *args, **options):
        app_name = options['app']
        model_name = options['model']
        field_name = options['field']

        model = apps.get_model(app_name, model_name)
        fields = model._meta.get_fields()
        matching_fields = [f for f in fields if isinstance(f, models.FileField) and f.name == field_name]
        field = matching_fields[0]
        storage = field.storage

        for o in model.objects.all():
            # threads aren't usually interrupted: https://stackoverflow.com/a/842567/6871666
            t = Thread(target=move_file, args=(model, storage, field_name, field, o))
            t.start()
            t.join()
