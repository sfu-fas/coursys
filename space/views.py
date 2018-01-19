from django.shortcuts import render, HttpResponseRedirect, get_object_or_404, HttpResponse
from django.urls import reverse
from django.contrib import messages
from django.http import StreamingHttpResponse
from .models import Location, RoomType, BookingRecord, BookingMemo, BookingRecordAttachment
from .forms import LocationForm, RoomTypeForm, BookingRecordForm, BookingRecordAttachmentForm
from courselib.auth import requires_role
from log.models import LogEntry
from coredata.models import Unit, Person
from grad.models import Supervisor
import datetime
import csv


@requires_role('SPAC')
def index(request):
    units = Unit.sub_units(request.units)
    locations = Location.objects.visible(units)
    room_types = RoomType.objects.visible(units)
    return render(request, 'space/index.html', {'locations': locations, 'room_types': room_types})


@requires_role('SPAC')
def download_locations(request):
    units = Unit.sub_units(request.units)
    locations = Location.objects.visible(units)
    response = HttpResponse(content_type='text/csv')

    response['Content-Disposition'] = 'inline; filename="locations-%s.csv"' % \
                                      (datetime.datetime.now().strftime('%Y%m%d'))
    writer = csv.writer(response)
    writer.writerow(['Unit', 'Campus', 'Building', 'Floor', 'Room Number', 'Square Meters', 'Room Type Description',
                     'Room Type Code', 'COU Code Description', 'Space Factor', 'COU Code Value', 'Infrastructure',
                     'Room Capacity', 'Category', 'Occupancy', 'Own/Leased', 'Comments', 'Current Booking',
                     'Active Grad Student(s)'])
    for l in locations:
        booking = l.get_current_booking()
        grad_count = None
        if booking:
            booker = booking.person
            grad_count = Supervisor.objects.filter(supervisor=booker, removed=False, student__current_status='ACTI').count()

        writer.writerow([l.unit.name, l.get_campus_display(), l.get_building_display(), l.floor, l.room_number,
                         l.square_meters, l.room_type.long_description, l.room_type.code,
                         l.room_type.COU_code_description, l.room_type.space_factor, l.room_type.COU_code_value,
                         l.get_infrastructure_display(), l.room_capacity, l.get_category_display(), l.occupancy_count,
                         l.get_own_or_lease_display(), l.comments, booking, grad_count])
    return response


@requires_role('SPAC')
def add_location(request):
    if request.method == 'POST':
        form = LocationForm(request, request.POST)
        if form.is_valid():
            location = form.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 'Location was created')
            l = LogEntry(userid=request.user.username,
                         description="Added location %s" % location,
                         related_object=location)
            l.save()
            return HttpResponseRedirect(reverse('space:index'))
    else:
        form = LocationForm(request)
    return render(request, 'space/new_location.html', {'form': form})


@requires_role('SPAC')
def edit_location(request, location_slug, from_index=0):
    location = get_object_or_404(Location, slug=location_slug, unit__in=Unit.sub_units(request.units))
    if request.method == 'POST':
        form = LocationForm(request, request.POST, instance=location)
        if form.is_valid():
            location = form.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 'Location was edited')
            l = LogEntry(userid=request.user.username,
                         description="Edited location %s" % location,
                         related_object=location)
            l.save()
            if from_index == '1':
                return HttpResponseRedirect(reverse('space:index'))
            return view_location(request, location.slug)
    else:
        form = LocationForm(request, instance=location)
    return render(request, 'space/edit_location.html', {'form': form, 'location': location, 'from_index': from_index})


@requires_role('SPAC')
def view_location(request, location_slug):
    location = get_object_or_404(Location, slug=location_slug, unit__in=Unit.sub_units(request.units))
    return render(request, 'space/view_location.html', {'location': location})


@requires_role('SPAC')
def delete_location(request, location_id):
    location = get_object_or_404(Location, pk=location_id, unit__in=Unit.sub_units(request.units))
    if request.method == 'POST':
        location.hidden = True
        location.save()
        messages.add_message(request,
                             messages.SUCCESS,
                             'Location was deleted')
        l = LogEntry(userid=request.user.username,
                     description="Deleted location %s" % location,
                     related_object=location)
        l.save()
    return HttpResponseRedirect(reverse('space:index'))


@requires_role('SPAC')
def list_roomtypes(request):
    roomtypes = RoomType.objects.visible(Unit.sub_units(request.units))
    return render(request, 'space/list_roomtypes.html', {'roomtypes': roomtypes})


@requires_role('SPAC')
def add_roomtype(request):
    if request.method == 'POST':
        form = RoomTypeForm(request, request.POST)
        if form.is_valid():
            roomtype = form.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 'Room type was created')
            l = LogEntry(userid=request.user.username,
                         description="Added roomtype %s" % roomtype,
                         related_object=roomtype)
            l.save()
            return HttpResponseRedirect(reverse('space:list_roomtypes'))
    else:
        form = RoomTypeForm(request)
    return render(request, 'space/new_roomtype.html', {'form': form})


@requires_role('SPAC')
def edit_roomtype(request, roomtype_slug):
    roomtype = get_object_or_404(RoomType, slug=roomtype_slug, unit__in=Unit.sub_units(request.units))
    if request.method == 'POST':
        form = RoomTypeForm(request, request.POST, instance=roomtype)
        if form.is_valid():
            roomtype = form.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 'Room type was edited')
            l = LogEntry(userid=request.user.username,
                         description="Edited roomtype %s" % roomtype,
                         related_object=roomtype)
            l.save()
            return HttpResponseRedirect(reverse('space:list_roomtypes'))
    else:
        form = RoomTypeForm(request, instance=roomtype)
    return render(request, 'space/edit_roomtype.html', {'form': form, 'roomtype': roomtype})


@requires_role('SPAC')
def view_roomtype(request, roomtype_slug):
    roomtype = get_object_or_404(RoomType, slug=roomtype_slug, unit__in=Unit.sub_units(request.units))
    return render(request, 'space/view_roomtype.html', {'roomtype': roomtype})


@requires_role('SPAC')
def delete_roomtype(request, roomtype_id):
    roomtype = get_object_or_404(RoomType, pk=roomtype_id, unit__in=Unit.sub_units(request.units))
    if request.method == 'POST':
        roomtype.hidden = True
        roomtype.save()
        messages.add_message(request,
                             messages.SUCCESS,
                             'Room type was deleted')
        l = LogEntry(userid=request.user.username,
                     description="Deleted roomtype %s" % roomtype,
                     related_object=roomtype)
        l.save()
    return HttpResponseRedirect(reverse('space:list_roomtypes'))


@requires_role('SPAC')
def add_booking(request, location_slug, from_index=0):
    location = get_object_or_404(Location, slug=location_slug, unit__in=Unit.sub_units(request.units))
    editor = get_object_or_404(Person, userid=request.user.username)
    if request.method == 'POST':
        form = BookingRecordForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.location = location
            booking.save(editor=editor)
            location.mark_conflicts()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 'Booking was created')
            l = LogEntry(userid=request.user.username,
                         description="Added booking %s for location %s" % (booking, location),
                         related_object=booking)
            l.save()
            if from_index == '1':
                return HttpResponseRedirect(reverse('space:index'))
            return view_location(request, location_slug)

        else:
            form.fields['start_time'].help_text = "Any previous bookings without an end time will also get its " \
                                                  "end time set to this."
    else:
        form = BookingRecordForm()
        form.fields['start_time'].help_text = "Any previous bookings without an end time will also get its " \
                                              "end time set to this."

    return render(request, 'space/new_booking.html', {'form': form, 'location': location, 'from_index': from_index})


@requires_role('SPAC')
def edit_booking(request, booking_slug):
    booking = get_object_or_404(BookingRecord, slug=booking_slug, location__unit__in=Unit.sub_units(request.units))
    editor = get_object_or_404(Person, userid=request.user.username)
    if request.method == 'POST':
        form = BookingRecordForm(request.POST, instance=booking)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.save(editor=editor)
            booking.location.mark_conflicts()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 'Booking was edited')
            l = LogEntry(userid=request.user.username,
                         description="Edited booking %s" % booking,
                         related_object=booking)
            l.save()
            return view_location(request, booking.location.slug)
    else:
        form = BookingRecordForm(instance=booking, initial={'person': booking.person.emplid})
    return render(request, 'space/edit_booking.html', {'form': form, 'booking_slug': booking_slug,
                                                       'location': booking.location })


@requires_role('SPAC')
def view_booking(request, booking_slug):
    booking = get_object_or_404(BookingRecord, slug=booking_slug, location__unit__in=Unit.sub_units(request.units))
    return render(request, 'space/view_booking.html', {'booking': booking})


@requires_role('SPAC')
def delete_booking(request, booking_id):
    booking = get_object_or_404(BookingRecord, pk=booking_id, location__unit__in=Unit.sub_units(request.units))
    editor = get_object_or_404(Person, userid=request.user.username)
    if request.method == 'POST':
        booking.hidden = True
        booking.save(editor=editor)
        booking.location.mark_conflicts()
        messages.add_message(request,
                             messages.SUCCESS,
                             'Booking was deleted')
        l = LogEntry(userid=request.user.username,
                     description="Deleted booking %s" % booking,
                     related_object=booking)
        l.save()
    return view_location(request, booking.location.slug)


@requires_role('SPAC')
def add_booking_attachment(request, booking_slug):
    booking = get_object_or_404(BookingRecord, slug=booking_slug, location__unit__in=Unit.sub_units(request.units))
    editor = get_object_or_404(Person, userid=request.user.username)
    form = BookingRecordAttachmentForm()
    context = {"booking": booking,
               "attachment_form": form}

    if request.method == "POST":
        form = BookingRecordAttachmentForm(request.POST, request.FILES)
        if form.is_valid():
            attachment = form.save(commit=False)
            attachment.booking_record = booking
            attachment.created_by = editor
            upfile = request.FILES['contents']
            filetype = upfile.content_type
            if upfile.charset:
                filetype += "; charset=" + upfile.charset
            attachment.mediatype = filetype
            attachment.save()
            return HttpResponseRedirect(reverse('space:view_booking', kwargs={'booking_slug': booking.slug}))
        else:
            context.update({"attachment_form": form})

    return render(request, 'space/add_booking_record_attachment.html', context)


@requires_role('SPAC')
def view_booking_attachment(request, booking_slug, attachment_id):
    booking = get_object_or_404(BookingRecord, slug=booking_slug, location__unit__in=Unit.sub_units(request.units))
    attachment = get_object_or_404(BookingRecordAttachment, booking_record=booking, pk=attachment_id)
    filename = attachment.contents.name.rsplit('/')[-1]
    resp = StreamingHttpResponse(attachment.contents.chunks(), content_type=attachment.mediatype)
    resp['Content-Disposition'] = 'inline; filename="' + filename + '"'
    resp['Content-Length'] = attachment.contents.size
    return resp


@requires_role('SPAC')
def download_booking_attachment(request, booking_slug, attachment_id):
    booking = get_object_or_404(BookingRecord, slug=booking_slug, location__unit__in=Unit.sub_units(request.units))
    attachment = get_object_or_404(BookingRecordAttachment, booking_record=booking, pk=attachment_id)
    filename = attachment.contents.name.rsplit('/')[-1]
    resp = StreamingHttpResponse(attachment.contents.chunks(), content_type=attachment.mediatype)
    resp['Content-Disposition'] = 'attachment; filename="' + filename + '"'
    resp['Content-Length'] = attachment.contents.size
    return resp


@requires_role('SPAC')
def delete_booking_attachment(request, booking_slug, attachment_id):
    booking = get_object_or_404(BookingRecord, slug=booking_slug, location__unit__in=Unit.sub_units(request.units))
    attachment = get_object_or_404(BookingRecordAttachment, booking_record=booking, pk=attachment_id)
    attachment.hide()
    messages.add_message(request,
                         messages.SUCCESS,
                         'Attachment was deleted')
    l = LogEntry(userid=request.user.username,
                 description="Deleted attachment in booking %s" % booking,
                 related_object=attachment)
    l.save()
    return HttpResponseRedirect(reverse('space:view_booking', kwargs={'booking_slug': booking.slug}))


@requires_role('SPAC')
def send_memo(request, booking_slug, from_index=0):
    booking = get_object_or_404(BookingRecord, slug=booking_slug, location__unit__in=Unit.sub_units(request.units))
    editor = get_object_or_404(Person, userid=request.user.username)
    booking_memo = BookingMemo(booking_record=booking, created_by=editor)
    booking_memo.email_memo()
    booking_memo.save()
    messages.add_message(request,
                         messages.SUCCESS,
                         'Memo was sent')
    l = LogEntry(userid=request.user.username,
                 description="Send memo to %s" % booking.person,
                 related_object=booking_memo)
    l.save()
    if from_index == '1':
        return HttpResponseRedirect(reverse('space:view_location', kwargs={'location_slug': booking.location.slug}))
    return HttpResponseRedirect(reverse('space:view_booking', kwargs={'booking_slug': booking.slug}))

