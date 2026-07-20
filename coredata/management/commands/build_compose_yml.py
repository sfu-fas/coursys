from django.core.management.base import BaseCommand

from docker.build_compose import DEPLOYMENT_CONTEXTS, build_from_template


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("deploy_mode", type=str)
    
    def build_and_write(self, deploy_mode: str):
        content = build_from_template(deploy_mode)
        print(f"Writing compose-{deploy_mode}.yml.")
        with open(f"compose-{deploy_mode}.yml", "wt", encoding="utf-8") as fh:
            fh.write(content)

    def handle(self, *args, **options):
        deploy_mode = options["deploy_mode"]
        if deploy_mode == "ALL":
            for dm in DEPLOYMENT_CONTEXTS.keys():
                self.build_and_write(dm)
        else:
            self.build_and_write(deploy_mode)
