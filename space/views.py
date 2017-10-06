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
    units = Unit.sub_units(request.units)
    locations = Location.objects.visible(units)
    room_types = RoomType.objects.visible(units)
    return render(request, 'space/index.html', {'locations': locations, 'room_types': room_types})


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
def edit_location(request, location_slug, from_index=0):
    location = get_object_or_404(Location, slug=location_slug, unit__in=Unit.sub_units(request.units))
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
            if from_index:
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
                             u'Location was deleted')
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
    roomtype = get_object_or_404(RoomType, slug=roomtype_slug, unit__in=Unit.sub_units(request.units))
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
                             u'Room type was deleted')
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
                                 u'Booking was created')
            l = LogEntry(userid=request.user.username,
                         description="Added booking %s for location %s" % (booking, location),
                         related_object=booking)
            l.save()
            if from_index:
                return view_location(request, location_slug)
            return HttpResponseRedirect(reverse('space:index'))
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
                                 u'Booking was edited')
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
                             u'Booking was deleted')
        l = LogEntry(userid=request.user.username,
                     description="Deleted booking %s" % booking,
                     related_object=booking)
        l.save()
    return view_location(request, booking.location.slug)

