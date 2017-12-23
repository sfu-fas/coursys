from models import DiscussionTopic
from django.db.models.aggregates import Max
import datetime
import time


def recent_activity(member):
    """
    Returns whether there has been any discussion activity since last visited for a member
    """
    latest_activity = DiscussionTopic.objects.filter(offering=member.offering).aggregate(Max('last_activity_at'))['last_activity_at__max']
    if latest_activity is None:
        latest_activity = datetime.datetime.fromtimestamp(0)
    return datetime.datetime.fromtimestamp(member.last_discuss()) < latest_activity


def update_last_viewed(member):
    """
    Updates the last discussion view attribute for a member
    """
    member.set_last_discuss(time.time())
    member.save()