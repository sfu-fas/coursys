from django.shortcuts import render, HttpResponseRedirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from .models import Asset, AssetChangeRecord
from .forms import AssetForm, AssetAttachmentForm, AssetChangeForm
from courselib.auth import requires_role
from log.models import LogEntry
from coredata.models import Unit, Role, Person
from courselib.auth import ForbiddenResponse
from django.db import transaction
from django.http import StreamingHttpResponse


@requires_role('INV')
def inventory_index(request):
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
                                 'Asset was created')
            l = LogEntry(userid=request.user.username,
                         description="Added asset %s" % asset.name,
                         related_object=asset)
            l.save()
            return HttpResponseRedirect(reverse('inventory:inventory_index'))
    else:
        form = AssetForm(request)
    return render(request, 'inventory/new_asset.html', {'form': form})


@requires_role('INV')
def edit_asset(request, asset_slug):
    asset = get_object_or_404(Asset, slug=asset_slug, unit__in=request.units)
    if request.method == 'POST':
        form = AssetForm(request, request.POST, instance=asset)
        if form.is_valid():
            asset = form.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 'Asset was modified')
            l = LogEntry(userid=request.user.username,
                         description="Modified asset %s" % asset.name,
                         related_object=asset)
            l.save()
            return HttpResponseRedirect(reverse('inventory:inventory_index'))
    else:
        form = AssetForm(request, instance=asset)
    return render(request, 'inventory/edit_asset.html', {'form': form, 'asset_slug': asset_slug})


@requires_role('INV')
def view_asset(request, asset_slug):
    asset = get_object_or_404(Asset, slug=asset_slug, unit__in=request.units)
    return render(request, 'inventory/view_asset.html', {'asset': asset})


@requires_role('INV')
def delete_asset(request, asset_id):
    asset = get_object_or_404(Asset, pk=asset_id, unit__in=request.units)
    if request.method == 'POST':
        asset.delete()
        messages.success(request, 'Hid asset %s' % asset)
        l = LogEntry(userid=request.user.username,
                     description="Deleted asset: %s" % asset,
                     related_object=asset)
        l.save()
    return HttpResponseRedirect(reverse('inventory:inventory_index'))


@requires_role('INV')
@transaction.atomic
def new_attachment(request, asset_id):
    asset = get_object_or_404(Asset, pk=asset_id, unit__in=request.units)
    editor = get_object_or_404(Person, userid=request.user.username)

    form = AssetAttachmentForm()
    context = {"asset": asset,
               "attachment_form": form}

    if request.method == "POST":
        form = AssetAttachmentForm(request.POST, request.FILES)
        if form.is_valid():
            attachment = form.save(commit=False)
            attachment.asset = asset
            attachment.created_by = editor
            upfile = request.FILES['contents']
            filetype = upfile.content_type
            if upfile.charset:
                filetype += "; charset=" + upfile.charset
            attachment.mediatype = filetype
            attachment.save()
            return HttpResponseRedirect(reverse('inventory:view_asset', kwargs={'asset_slug': asset.slug}))
        else:
            context.update({"attachment_form": form})

    return render(request, 'inventory/asset_document_attachment_form.html', context)


@requires_role('INV')
def view_attachment(request, asset_id, attach_slug):
    asset = get_object_or_404(Asset, pk=asset_id, unit__in=request.units)
    attachment = get_object_or_404(asset.attachments.all(), slug=attach_slug)
    filename = attachment.contents.name.rsplit('/')[-1]
    resp = StreamingHttpResponse(attachment.contents.chunks(), content_type=attachment.mediatype)
    resp['Content-Disposition'] = 'inline; filename="' + filename + '"'
    resp['Content-Length'] = attachment.contents.size
    return resp


@requires_role('INV')
def download_attachment(request, asset_id, attach_slug):
    asset = get_object_or_404(Asset, pk=asset_id, unit__in=request.units)
    attachment = get_object_or_404(asset.attachments.all(), slug=attach_slug)
    filename = attachment.contents.name.rsplit('/')[-1]
    resp = StreamingHttpResponse(attachment.contents.chunks(), content_type=attachment.mediatype)
    resp['Content-Disposition'] = 'attachment; filename="' + filename + '"'
    resp['Content-Length'] = attachment.contents.size
    return resp


@requires_role('INV')
def delete_attachment(request, asset_id, attach_slug):
    asset = get_object_or_404(Asset, pk=asset_id, unit__in=request.units)
    attachment = get_object_or_404(asset.attachments.all(), slug=attach_slug)
    attachment.hide()
    messages.add_message(request,
                         messages.SUCCESS,
                         'Attachment deleted.'
                         )
    l = LogEntry(userid=request.user.username, description="Hid attachment %s" % attachment, related_object=attachment)
    l.save()
    return HttpResponseRedirect(reverse('inventory:view_asset', kwargs={'asset_slug': asset.slug}))


@requires_role('INV')
def add_change_record(request, asset_slug):
    asset = get_object_or_404(Asset, slug=asset_slug, unit__in=request.units)
    if request.method == 'POST':
        form = AssetChangeForm(request, request.POST)
        if form.is_valid():
            change = form.save(commit=False)
            change.asset = asset
            qty = int(form.cleaned_data['qty'])
            #  If no one has ever put in a quantity for the asset, make it 0 to avoid adding int to Nonetype
            if not asset.quantity:
                asset.quantity = 0
            if qty + asset.quantity < 0:
                messages.add_message(request, messages.WARNING, 'You tried to remove more of this asset than you '
                                                                'originally had.  Asset quantity set to zero.')
                asset.quantity = 0
            else:
                asset.quantity += qty
            asset.save()
            change.save(request.user.username)
            messages.add_message(request, messages.SUCCESS, 'Asset change record added')
            l = LogEntry(userid=request.user.username, description="Added change record %s for asset %s" %
                                                                   (change, asset), related_object=change)
            l.save()
            return HttpResponseRedirect(reverse('inventory:view_asset', kwargs={'asset_slug': asset.slug}))
    else:
        form = AssetChangeForm(request)

    return render(request, 'inventory/add_change_record.html', {'form': form, 'asset': asset})


@requires_role('INV')
def delete_change_record(request, record_id):
    record = get_object_or_404(AssetChangeRecord, pk=record_id, asset__unit__in=request.units)
    asset = record.asset
    record.delete(request.user.username)
    messages.success(request, 'Successfully hid record')
    l = LogEntry(userid=request.user.username,
                 description="Deleted record: %s" % record,
                 related_object=record)
    l.save()
    messages.warning(request, 'WARNING:  Quantity for this asset has not been changed.  If deleting this '
                              'record implies quantity changes, please adjust the asset quantity now.')
    return HttpResponseRedirect(reverse('inventory:view_asset', kwargs={'asset_slug': asset.slug}))