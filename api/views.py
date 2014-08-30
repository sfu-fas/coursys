from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required

from oauth_provider.models import Token
from api.models import ConsumerInfo
from oauth_provider.forms import AuthorizeRequestTokenForm

@login_required
def oauth_authorize(request, request_token, callback, params):
    """
    The callback view or oauth_provider's OAUTH_AUTHORIZE_VIEW
    """
    consumer = request_token.consumer
    consumerinfo = ConsumerInfo.objects.get(consumer_id=request_token.consumer_id)
    form = AuthorizeRequestTokenForm(initial={'oauth_token': request_token.key})

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
    token = get_object_or_404(Token, key=oauth_token)
    context = {
        'token': token,
        'error': error,
    }
    return render(request, 'api/oauth_callback.html', context)

