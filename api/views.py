from django.http import HttpResponseRedirect
from django.urls import reverse
from django.core.mail import send_mail
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.conf import settings

from oauth_provider.models import Token
from oauth_provider.forms import AuthorizeRequestTokenForm
from api.models import ConsumerInfo
from coredata.models import Person
from courselib.branding import product_name

EMAIL_INFORM_TEMPLATE = """
The application "{consumername}" has requested access to %s on your
behalf. You can approve this request using the interface the application
provided (and may have already done so).

You can review permissions given to third-party applications (removing access
if you wish) at this URL:
{url}""" % (product_name(hint='course'),)


@login_required
def oauth_authorize(request, request_token, callback, params):
    """
    The callback view for oauth_provider's OAUTH_AUTHORIZE_VIEW.
    """
    consumer = request_token.consumer
    consumerinfo = ConsumerInfo.objects.filter(consumer_id=request_token.consumer_id).order_by('-timestamp').first()
    form = AuthorizeRequestTokenForm(initial={'oauth_token': request_token.key})

    # email the user so we're super-sure they know this is happening
    person = get_object_or_404(Person, userid=request.user.username)
    manage_url = request.build_absolute_uri(reverse('config:manage_tokens'))
    message = EMAIL_INFORM_TEMPLATE.format(consumername=consumer.name, url=manage_url)
    send_mail('CourSys access requested', message, settings.DEFAULT_FROM_EMAIL, [person.email()], fail_silently=False)

    context = {
        'consumer': consumer,
        'consumerinfo': consumerinfo,
        'form': form,
    }
    return render(request, 'api/oauth_authorize.html', context)


def oauth_callback(request, oauth_token=None, error=None):
    """
    If the consumer doesn't provide a callback URL, this gives a user-visible result displaying the verifier.
    """
    token = get_object_or_404(Token, key=oauth_token)
    context = {
        'token': token,
        'error': error,
    }
    return render(request, 'api/oauth_callback.html', context)


@login_required
def manage_tokens(request):
    if request.method == 'POST':
        # token deletion requested
        key = request.POST.get('key', None)
        token = get_object_or_404(Token, user__username=request.user.username, token_type=Token.ACCESS, key=key)
        token.delete()
        return HttpResponseRedirect(reverse('config:manage_tokens'))

    else:
        tokens = Token.objects.filter(user__username=request.user.username, token_type=Token.ACCESS) \
            .select_related('consumer')
        for t in tokens:
            t.consumer_info = ConsumerInfo.get_for_token(t)

        context = {
            'tokens': tokens,
        }
        return render(request, 'api/manage_tokens.html', context)
