from django.contrib.admin import widgets

from .models import BookingRecord, Location, RoomType, BookingRecordAttachment
from django import forms
from coredata.models import Unit
from coredata.forms import PersonField


class LocationForm(forms.ModelForm):
    def __init__(self, request, *args, **kwargs):
        super(LocationForm, self).__init__(*args, **kwargs)
        unit_ids = [unit.id for unit in Unit.sub_units(request.units)]
        units = Unit.objects.filter(id__in=unit_ids)
        roomtypes = RoomType.objects.visible(units)
        self.fields['unit'].queryset = units
        self.fields['unit'].empty_label = None
        self.fields['room_type'].queryset = roomtypes
        self.fields['room_type'].empty_label = None

    class Meta:
        exclude = []
        model = Location
        widgets = {
            'comments': forms.Textarea
        }


class BookingRecordForm(forms.ModelForm):
    person = PersonField()

    class Meta:
        exclude = ['location']
        model = BookingRecord
        field_classes = {
            'start_time': forms.SplitDateTimeField,
            'end_time': forms.SplitDateTimeField,
        }
        widgets = {
            'start_time': forms.SplitDateTimeWidget,
            'end_time': forms.SplitDateTimeWidget,
            'notes': forms.Textarea,
        }

    def clean(self):
        cleaned_data = super(BookingRecordForm, self).clean()
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")
        if end_time is not None and end_time < start_time:
            raise forms.ValidationError({'end_time': "End date/time cannot be before start date.",
                                         'start_time': "End date/time cannot be before start date."})

    def is_valid(self, *args, **kwargs):
        PersonField.person_data_prep(self)
        return super(BookingRecordForm, self).is_valid(*args, **kwargs)


class RoomTypeForm(forms.ModelForm):
    def __init__(self, request, *args, **kwargs):
        super(RoomTypeForm, self).__init__(*args, **kwargs)
        unit_ids = [unit.id for unit in Unit.sub_units(request.units)]
        units = Unit.objects.filter(id__in=unit_ids)
        self.fields['unit'].queryset = units
        self.fields['unit'].empty_label = None

    class Meta:
        exclude = []
        model = RoomType


class BookingRecordAttachmentForm(forms.ModelForm):
    class Meta:
        exclude = ['booking_record', 'created_by']
        model = BookingRecordAttachment
