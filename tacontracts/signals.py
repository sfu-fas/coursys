# Django
from django.db.models.signals import post_save
from django.dispatch import receiver

# App
from .models import TACategory, TAContract, TACourse

def log(sender, **kwargs):
    instance = kwargs['instance']
    created = kwargs['created']
    saved = "saved"
    if created:
        saved = "created"

    print sender
    print "%s %s at %s" % (str(instance), saved, str(datetime.datetime.now())) 


@receiver(post_save, sender=TACategory)
def log_category(sender, **kwargs):
    log(sender, **kwargs)

@receiver(post_save, sender=TAContract)
def log_contract(sender, **kwargs):
    log(sender, **kwargs)

@receiver(post_save, sender=TACourse)
def log_course(sender, **kwargs):
    log(sender, **kwargs)

