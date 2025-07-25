from django.shortcuts import render, HttpResponseRedirect, get_object_or_404, HttpResponse
from django.urls import reverse
from django.contrib import messages
from .models import Asset, AssetChangeRecord, assets_from_csv
from .forms import AssetForm, AssetAttachmentForm, AssetChangeForm, InventoryUploadForm, InventoryFilterForm
from courselib.auth import requires_role
from log.models import LogEntry
from coredata.models import Unit, Person
from django.db import transaction
from django.http import StreamingHttpResponse
from django_datatables_view.base_datatable_view import BaseDatatableView
from django.middleware.csrf import get_token
import csv, datetime


@requires_role('INV')
def inventory_index(request):
    if 'tabledata' in request.GET:
        return InventoryDataJSON.as_view()(request)
    form = InventoryFilterForm(request)
    return render(request, 'inventory/index.html', {'form': form})


# Helper methods moved from template filtering since we are now using server-side code.
def add_asset_display_class(asset):
    if asset.out_of_stock():
        return 'outofstock'
    elif asset.needs_reorder():
        return 'needsreorder'
    elif asset.in_stock():
        return 'instock'
    else:
        return ""

class InventoryDataJSON(BaseDatatableView):
    model = Asset
    columns = ['name', 'quantity', 'category', 'location', 'last_modified', 'stock_status', 'actions']
    order_columns = ['name', 'quantity', 'category', 'location', 'last_modified', 'stock_status', 'actions']

    def get_initial_queryset(self):
        qs = Asset.objects.visible(self.request.units)
        return qs

    def get_filter_method(self):
        return self.FILTER_ICONTAINS

    def render_column(self, row, column):
        instockclass = add_asset_display_class(row)
        if column == 'name':
            extra_string = ''
            if row.has_attachments():
                extra_string += ' &nbsp; <i class="fa fa-paperclip" title="Attachment(s)"></i>'
            if row.has_records():
                extra_string += ' &nbsp; <i class="fa fa-book" title="Record(s)"></i>'
            return row.name + extra_string
        if column == 'quantity':
            return str("<span class=" + instockclass + ">%s</span>" % row.quantity)

        elif column == 'last_modified':
            return str("<span class='sort'>%s</span>%s" % (row.last_modified, row.last_modified.strftime("%b %d, %Y")))
        elif column == 'actions':
            return '<form class="lineform" method="POST" action=' +\
                reverse('inventory:delete_asset', kwargs={'asset_id': row.id}) + '>' +\
                '<input type="hidden" name="csrfmiddlewaretoken" value="' + get_token(self.request) + '">' +\
                    '<button type="submit" class="btn confirm-submit" title="Hide asset" data-submit-action="remove this asset">' +\
                        '<i class="fa fa-trash-o"></i>' +\
                    '</button>' +\
                '</form>' +\
                '<a class="lineform" href="' + reverse('inventory:add_change_record', kwargs={'asset_slug': row.slug}) +'">' +\
                    '<button type="submit" class="btn" title="Add change record">' +\
                        '<i class="fa fa-book"></i>' +\
                    '</button>' +\
                '</a>' +\
                '<a class="lineform" href="' + reverse('inventory:edit_asset', kwargs={'asset_slug': row.slug}) + '">' +\
                    '<button type="submit" class="btn" title="Edit asset">' +\
                        '<i class="fa fa-edit"></i>' +\
                    '</button>' +\
                '</a>' +\
                '<a class="lineform" href="' + reverse('inventory:view_asset', kwargs={'asset_slug': row.slug}) + '">' +\
                    '<button type="submit" class="btn" title="View asset">' +\
                        '<i class="fa fa-eye"></i>' +\
                    '</button>' +\
                '</a>'
        else:
            return super(InventoryDataJSON, self).render_column(row, column)

    def filter_queryset(self, qs):
        # use request parameters to filter queryset
        requestget = self.request.GET
        categories = requestget.getlist('categories[]')
        if categories:
            qs = qs.filter(category__in=categories)
        in_stock_status = requestget.getlist('in_stock_status[]')
        if in_stock_status:
            qs = qs.filter(stock_status__in=in_stock_status)
        brand = requestget.get('brand[]', None)
        if brand:
            qs = qs.filter(brand=brand)
        return super(InventoryDataJSON, self).filter_queryset(qs)


@requires_role('INV')
def inventory_download(request):
    unit_ids = [unit.id for unit in request.units]
    units = Unit.objects.filter(id__in=unit_ids)
    assets = Asset.objects.visible(units)
    response = HttpResponse(content_type='text/csv')

    response['Content-Disposition'] = 'inline; filename="inventory-%s.csv"' % datetime.datetime.now().strftime('%Y%m%d')
    writer = csv.writer(response)
    if assets:
        writer.writerow(['Name', 'Unit', 'Brand', 'Description', 'Serial', 'Service/Asset Tag', 'Express Service Code',
                         'Quantity', 'Minimum Re-Order Quantity', 'Quantity Ordered', 'Minimum Vendor Quantity',
                         'Price', 'Category', 'Location', 'PR/PO No.', 'Account No.', 'Supplier/Vendor',
                         'Calibration/Service Date', 'End of Life Date', 'Notes', 'Service Records',
                         'Attachments', 'Change Records', 'User', 'Date Shipped/Received', 'Currently in Use', 'URL'])
        for a in assets:
            url = request.build_absolute_uri(reverse('inventory:view_asset', kwargs={'asset_slug': a.slug}))
            writer.writerow([a.name, a.unit, a.brand, a.description, a.serial, a.tag, a.express_service_code,
                             a.quantity, a.min_qty, a.qty_ordered, a.min_vendor_qty, a.price, a.get_category_display(),
                             a.location, a.po, a.account, a.vendor, a.calibration_date, a.eol_date, a.notes,
                             a.service_records, a.has_attachments(), a.has_records(), a.user, a.date_shipped, a.in_use,
                             url])
    return response


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
def upload_assets_csv(request):
    if request.method == 'POST':
        form = InventoryUploadForm(request, data=request.POST, files=request.FILES)
        if form.is_valid():
            rows = assets_from_csv(request, form.cleaned_data['file'], save=True)
            messages.add_message(request, messages.SUCCESS, "Added %i assets from file upload." % rows)
            # We don't have a related_object to create a log, but each individually created object will set a log in
            # the assets_from_csv method if save=True.
            return HttpResponseRedirect(reverse('inventory:inventory_index'))
    else:
        form = InventoryUploadForm(request)
    return render(request, 'inventory/upload_assets.html', {'form': form})


@requires_role('INV')
def edit_asset(request, asset_slug):
    asset = get_object_or_404(Asset, slug=asset_slug, unit__in=request.units, hidden=False)
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
        if asset.user:
            user = asset.user.emplid
        else:
            user = None
        form = AssetForm(request, instance=asset, initial={'user': user})
    return render(request, 'inventory/edit_asset.html', {'form': form, 'asset_slug': asset_slug})


@requires_role('INV')
def view_asset(request, asset_slug):
    asset = get_object_or_404(Asset, slug=asset_slug, unit__in=request.units, hidden=False)
    asset_url = request.build_absolute_uri(reverse('inventory:view_asset', kwargs={'asset_slug': asset_slug}))
    return render(request, 'inventory/view_asset.html', {'asset': asset, 'asset_url': asset_url})


@requires_role('INV')
def delete_asset(request, asset_id):
    asset = get_object_or_404(Asset, pk=asset_id, unit__in=request.units, hidden=False)
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
    asset = get_object_or_404(Asset, pk=asset_id, unit__in=request.units, hidden=False)
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
    asset = get_object_or_404(Asset, pk=asset_id, unit__in=request.units, hidden=False)
    attachment = get_object_or_404(asset.attachments.all(), slug=attach_slug)
    filename = attachment.contents.name.rsplit('/')[-1]
    resp = StreamingHttpResponse(attachment.contents.chunks(), content_type=attachment.mediatype)
    resp['Content-Disposition'] = 'inline; filename="' + filename + '"'
    resp['Content-Length'] = attachment.contents.size
    return resp


@requires_role('INV')
def download_attachment(request, asset_id, attach_slug):
    asset = get_object_or_404(Asset, pk=asset_id, unit__in=request.units, hidden=False)
    attachment = get_object_or_404(asset.attachments.all(), slug=attach_slug)
    filename = attachment.contents.name.rsplit('/')[-1]
    resp = StreamingHttpResponse(attachment.contents.chunks(), content_type=attachment.mediatype)
    resp['Content-Disposition'] = 'attachment; filename="' + filename + '"'
    resp['Content-Length'] = attachment.contents.size
    return resp


@requires_role('INV')
def delete_attachment(request, asset_id, attach_slug):
    asset = get_object_or_404(Asset, pk=asset_id, unit__in=request.units, hidden=False)
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
    asset = get_object_or_404(Asset, slug=asset_slug, unit__in=request.units, hidden=False)
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
    record = get_object_or_404(AssetChangeRecord, pk=record_id, asset__unit__in=request.units, hidden=False)
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