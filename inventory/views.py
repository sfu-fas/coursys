from django.shortcuts import render, HttpResponseRedirect, get_object_or_404
from django.core.urlresolvers import reverse
from django.contrib import messages
from .models import Asset
from .forms import AssetForm
from courselib.auth import requires_role
from log.models import LogEntry
from coredata.models import Unit, Role
from courselib.auth import ForbiddenResponse
import unicodecsv as csv
from datetime import datetime


def _has_unit_role(user, asset):
    """
    A quick method to check that the person has the Inventory Admin role for the given asset's unit.
    """
    return Role.objects.filter(person__userid=user.username, role='INV', unit=asset.unit).count() > 0

@requires_role('INV')
def index(request):
    unit_ids = [unit.id for unit in request.units]
    units = Unit.objects.filter(id__in=unit_ids)
    assets = Asset.objects.visible(units)
    return render(request, 'inventory/index.html', {'assets': assets})


@requires_role('INV')
def new_asset(request):
    if request.method == 'POST':
        form = AssetForm(request, request.POST)
        if form.is_valid():
            asset = form.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 u'Asset was created')
            l = LogEntry(userid=request.user.username,
                         description="Added asset %s" % asset.name,
                         related_object=asset)
            l.save()
            return HttpResponseRedirect(reverse('index'))
    else:
        form = AssetForm(request)
    return render(request, 'inventory/new_asset.html', {'form': form})


@requires_role('INV')
def edit_asset(request, asset_slug):
    asset = get_object_or_404(Asset, slug=asset_slug)
    if not _has_unit_role(request.user, asset):
        return ForbiddenResponse(request)
    if request.method == 'POST':
        form = AssetForm(request, request.POST, instance=asset)
        if form.is_valid():
            asset = form.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 u'Asset was modified')
            l = LogEntry(userid=request.user.username,
                         description="Modified asset %s" % asset.name,
                         related_object=asset)
            l.save()
            return HttpResponseRedirect(reverse(index))
    else:
        form = AssetForm(request, instance=asset)
    return render(request, 'inventory/edit_asset.html', {'form': form, 'asset_slug': asset_slug})


@requires_role('INV')
def view_asset(request, asset_slug):
    asset = get_object_or_404(Asset, slug=asset_slug)
    if not _has_unit_role(request.user, asset):
        return ForbiddenResponse(request)
    return render(request, 'inventory/view_asset.html', {'asset': asset})


@requires_role('INV')
def delete_asset(request, asset_id):
    asset = get_object_or_404(Asset, pk=asset_id)
    if not _has_unit_role(request.user, asset):
        return ForbiddenResponse(request)
    if request.method == 'POST':
        asset.delete()
        messages.success(request, 'Hid asset %s' % asset)
        l = LogEntry(userid=request.user.username,
                     description="Deleted asset: %s" % asset,
                     related_object=asset)
        l.save()
    return HttpResponseRedirect(reverse(index))



