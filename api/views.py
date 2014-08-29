from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from api.models import ConsumerInfo, TokenInfo
from api.forms import AuthForm
from coredata.models import Person

import datetime

@login_required
def oauth_authorize(request, request_token, callback, params):
    """
    The callback view or oauth_provider's OAUTH_AUTHORIZE_VIEW
    """
    consumer = request_token.consumer
    consumerinfo = ConsumerInfo.objects.get(consumer_id=request_token.consumer_id)
    form = AuthForm(initial={'oauth_token': request_token.key})

    tokeninfo, _ = TokenInfo.objects.get_or_create(token=request_token)
    tokeninfo.permissions = consumerinfo.permissions
    tokeninfo.save()

    context = {
        'consumer': consumer,
        'consumerinfo': consumerinfo,
        'form': form,
    }
    return render(request, 'api/oauth_authorize.html', context)


def oauth_callback(request, oauth_token=None, error=None):
    """
    If the consumer doesn't provide a callback URL, this gives a user-visible result
    """
    context = {
        'oauth_token': oauth_token,
        'error': error,
    }
    return render(request, 'api/oauth_callback.html', context)
