#!/usr/bin/env python3
import os
import sys
assert sys.version_info >= (3, 5)

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "courses.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
