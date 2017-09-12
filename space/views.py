from django.shortcuts import render, HttpResponseRedirect, get_object_or_404
from django.core.urlresolvers import reverse
from django.contrib import messages
from .models import Location, RoomType, BookingRecord
from .forms import LocationForm, RoomTypeForm, BookingRecordForm
from courselib.auth import requires_role
from log.models import LogEntry
from coredata.models import Unit, Role, Person
from courselib.auth import ForbiddenResponse


@requires_role('SPAC')
def index(request):
    unit_ids = [unit.id for unit in request.units]
    units = Unit.objects.filter(id__in=unit_ids)
    locations = Location.objects.visible(units)
    return render(request, 'space/index.html', {'locations': locations})


@requires_role('SPAC')
def add_location(request):
    if request.method == 'POST':
        form = LocationForm(request, request.POST)
        if form.is_valid():
            location = form.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 u'Location was created')
            l = LogEntry(userid=request.user.username,
                         description="Added location %s" % location,
                         related_object=location)
            l.save()
            return HttpResponseRedirect(reverse('space:index'))
    else:
        form = LocationForm(request)
    return render(request, 'space/new_location.html', {'form': form})


@requires_role('SPAC')
def edit_location(request, location_slug):
    location = get_object_or_404(Location, slug=location_slug, unit__in=request.units)
    if request.method == 'POST':
        form = LocationForm(request, request.POST, instance=location)
        if form.is_valid():
            location = form.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 u'Location was edited')
            l = LogEntry(userid=request.user.username,
                         description="Edited location %s" % location,
                         related_object=location)
            l.save()
            return HttpResponseRedirect(reverse('space:index'))
    else:
        form = LocationForm(request, instance=location)
    return render(request, 'space/edit_location.html', {'form': form})


@requires_role('SPAC')
def view_location(request, location_slug):
    location = get_object_or_404(Location, slug=location_slug, unit__in=request.units)
    return render(request, 'space/view_location.html', {'location': location})


@requires_role('SPAC')
def delete_location(request, location_id):
    location = get_object_or_404(Location, pk=location_id, unit__in=request.units)
    if request.method == 'POST':
        location.hidden = True
        location.save()
        messages.add_message(request,
                             messages.SUCCESS,
                             u'Location was deleted')
        l = LogEntry(userid=request.user.username,
                     description="Deleted location %s" % location,
                     related_object=location)
        l.save()
    return HttpResponseRedirect(reverse('space:index'))


@requires_role('SPAC')
def list_roomtypes(request):
    unit_ids = [unit.id for unit in request.units]
    units = Unit.objects.filter(id__in=unit_ids)
    roomtypes = RoomType.objects.visible(units)
    return render(request, 'space/list_roomtypes.html', {'roomtypes': roomtypes})


@requires_role('SPAC')
def add_roomtype(request):
    if request.method == 'POST':
        form = RoomTypeForm(request, request.POST)
        if form.is_valid():
            roomtype = form.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 u'Room type was created')
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
    roomtype = get_object_or_404(RoomType, slug=roomtype_slug, unit__in=request.units)
    if request.method == 'POST':
        form = RoomTypeForm(request, request.POST, instance=roomtype)
        if form.is_valid():
            roomtype = form.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 u'Room type was edited')
            l = LogEntry(userid=request.user.username,
                         description="Edited roomtype %s" % roomtype,
                         related_object=roomtype)
            l.save()
            return HttpResponseRedirect(reverse('space:list_roomtypes'))
    else:
        form = RoomTypeForm(request, instance=roomtype)
    return render(request, 'space/edit_roomtype.html', {'form': form})


@requires_role('SPAC')
def view_roomtype(request, roomtype_slug):
    location = get_object_or_404(RoomTypeForm, slug=roomtype_slug, unit__in=request.units)
    return render(request, 'space/view_roomtype.html', {'roomtype': roomtype})


@requires_role('SPAC')
def delete_roomtype(request, roomtype_id):
    roomtype = get_object_or_404(RoomType, pk=roomtype_id, unit__in=request.units)
    if request.method == 'POST':
        roomtype.hidden = True
        roomtype.save()
        messages.add_message(request,
                             messages.SUCCESS,
                             u'Room type was deleted')
        l = LogEntry(userid=request.user.username,
                     description="Deleted roomtype %s" % roomtype,
                     related_object=roomtype)
        l.save()
    return HttpResponseRedirect(reverse('space:list_roomtypes'))

@requires_role('SPAC')
def add_booking(request, location_slug):
    location = get_object_or_404(Location, slug=location_slug, unit__in=request.units)
    if request.method == 'POST':
        form = BookingRecordForm(request, request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.location = location
            booking.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 u'Booking was created')
            l = LogEntry(userid=request.user.username,
                         description="Added booking" % booking,
                         related_object=booking)
            l.save()
            return HttpResponseRedirect(reverse('space:index'))
    else:
        form = BookingRecordForm(request)
    return render(request, 'space/new_booking.html', {'form': form})


@requires_role('SPAC')
def edit_booking(request, booking_slug):
    booking = get_object_or_404(booking, slug=booking_slug, unit__in=request.units)
    if request.method == 'POST':
        form = bookingForm(request, request.POST, instance=booking)
        if form.is_valid():
            booking = form.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 u'Room type was edited')
            l = LogEntry(userid=request.user.username,
                         description="Edited booking %s" % booking,
                         related_object=booking)
            l.save()
            return HttpResponseRedirect(reverse('space:list_bookings'))
    else:
        form = bookingForm(request, instance=booking)
    return render(request, 'space/edit_booking.html', {'form': form})


@requires_role('SPAC')
def view_booking(request, booking_slug):
    booking = get_object_or_404(BookingRecord, slug=booking_slug, unit__in=request.units)
    return render(request, 'space/view_booking.html', {'booking': booking})


@requires_role('SPAC')
def delete_booking(request, booking_id):
    booking = get_object_or_404(BookingRecord, pk=booking_id, unit__in=request.units)
    if request.method == 'POST':
        booking.hidden = True
        booking.save()
        messages.add_message(request,
                             messages.SUCCESS,
                             u'Room type was deleted')
        l = LogEntry(userid=request.user.username,
                     description="Deleted booking %s" % booking,
                     related_object=booking)
        l.save()
    return HttpResponseRedirect(reverse('space:list_bookings'))

