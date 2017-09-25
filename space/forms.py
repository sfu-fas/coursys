from .models import BookingRecord, Location, RoomType
from django import forms
from coredata.models import Unit
from coredata.forms import PersonField


class LocationForm(forms.ModelForm):
    def __init__(self, request, *args, **kwargs):
        super(LocationForm, self).__init__(*args, **kwargs)
        unit_ids = [unit.id for unit in request.units]
        units = Unit.objects.filter(id__in=unit_ids)
        roomtypes = RoomType.objects.visible(units)
        self.fields['unit'].queryset = units
        self.fields['unit'].empty_label = None
        self.fields['room_type'].queryset = roomtypes
        self.fields['room_type'].empty_label = None

    class Meta:
        exclude = []
        model = Location


class BookingRecordForm(forms.ModelForm):
    person = PersonField()

    class Meta:
        exclude = ['location']
        model = BookingRecord

    def is_valid(self, *args, **kwargs):
        PersonField.person_data_prep(self)
        return super(BookingRecordForm, self).is_valid(*args, **kwargs)


class RoomTypeForm(forms.ModelForm):
    def __init__(self, request, *args, **kwargs):
        super(RoomTypeForm, self).__init__(*args, **kwargs)
        unit_ids = [unit.id for unit in request.units]
        units = Unit.objects.filter(id__in=unit_ids)
        self.fields['unit'].queryset = units
        self.fields['unit'].empty_label = None

    class Meta:
        exclude = []
        model = RoomType
