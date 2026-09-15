import datetime
from decimal import Decimal, InvalidOperation
from coredata.models import Unit
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, URLValidator, validate_email
from django.db import models


SYSTEM_VARIABLE_KEY_VALIDATOR = RegexValidator(
    regex=r'^[a-z][a-z0-9_]*$',
    message='Keys must start with a letter and contain only lowercase letters, numbers, and underscores.',
)


class SystemVariable(models.Model):
    TYPE_STRING = 'string'
    TYPE_TEXT = 'text'
    TYPE_INTEGER = 'integer'
    TYPE_DECIMAL = 'decimal'
    TYPE_EMAIL = 'email'
    TYPE_URL = 'url'
    TYPE_BOOLEAN = 'boolean'
    TYPE_DATE = 'date'

    VALUE_TYPE_CHOICES = [
        (TYPE_STRING, 'String'),
        (TYPE_TEXT, 'Text'),
        (TYPE_INTEGER, 'Integer'),
        (TYPE_DECIMAL, 'Decimal'),
        (TYPE_EMAIL, 'Email'),
        (TYPE_URL, 'URL'),
        (TYPE_BOOLEAN, 'Boolean'),
        (TYPE_DATE, 'Date'),
    ]

    DEFAULT_TYPED_VALUES = {
        TYPE_STRING: '',
        TYPE_TEXT: '',
        TYPE_INTEGER: 0,
        TYPE_DECIMAL: Decimal('0'),
        TYPE_EMAIL: '',
        TYPE_URL: '',
        TYPE_BOOLEAN: False,
        TYPE_DATE: datetime.date(2000, 1, 1),
    }

    key = models.CharField(max_length=100, db_index=True, validators=[SYSTEM_VARIABLE_KEY_VALIDATOR], help_text='e.g. "minimum_wage"')
    label = models.CharField(max_length=200, help_text='e.g. "Minimum Wage"')
    value_type = models.CharField(max_length=20, choices=VALUE_TYPE_CHOICES, default=TYPE_STRING)
    value = models.TextField(default='', blank=True)
    unit = models.ForeignKey(Unit, null=True, blank=True, on_delete=models.PROTECT, help_text='Leave blank for the global default value.')
    notes = models.TextField(default='', blank=True, help_text='Any notes about this variable?')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (('key', 'unit'))

    def _default_typed_value(self):
        return self.DEFAULT_TYPED_VALUES.get(self.value_type, '')

    def _parse_typed_value(self, raw_value):
        raw_value = (raw_value or '').strip()

        if self.value_type in {self.TYPE_STRING, self.TYPE_TEXT, self.TYPE_EMAIL, self.TYPE_URL}:
            return raw_value

        if self.value_type == self.TYPE_INTEGER:
            return int(raw_value)

        if self.value_type == self.TYPE_DECIMAL:
            return Decimal(raw_value)

        if self.value_type == self.TYPE_BOOLEAN:
            val = str(raw_value).strip().lower()
            if val in {'true'}:
                return True
            if val in {'false'}:
                return False
            return self._default_typed_value()

        if self.value_type == self.TYPE_DATE:
            return datetime.date.fromisoformat(raw_value)

        return raw_value

    def clean(self):
        super(SystemVariable, self).clean()

        if self.key:
            self.key = self.key.strip().lower()

        if self.label:
            self.label = self.label.strip()

        existing_same_scope = SystemVariable.objects.filter(key=self.key, unit=self.unit).exclude(pk=self.pk)
        if existing_same_scope.exists():
            if self.unit:
                raise ValidationError('A variable already exists for this key and unit.')
            raise ValidationError('A system-wide variable already exists for this key.')

        existing_same_key = SystemVariable.objects.filter(key=self.key).exclude(pk=self.pk).first()
        if existing_same_key and existing_same_key.value_type != self.value_type:
            raise ValidationError('All values for this key must use the same value type.')

        self._validate_typed_value()

    def _validate_typed_value(self):
        raw_value = (self.value or '').strip()

        if self.value_type in {self.TYPE_STRING, self.TYPE_TEXT}:
            if not raw_value:
                raise ValidationError('This value cannot be blank.')

        elif self.value_type == self.TYPE_INTEGER:
            try:
                int(raw_value)
            except (TypeError, ValueError):
                raise ValidationError('Enter a valid integer.')

        elif self.value_type == self.TYPE_DECIMAL:
            try:
                Decimal(raw_value)
            except (InvalidOperation, TypeError, ValueError):
                raise ValidationError('Enter a valid decimal value.')

        elif self.value_type == self.TYPE_EMAIL:
            try:
                validate_email(raw_value)
            except ValidationError:
                raise ValidationError('Enter a valid email address.')

        elif self.value_type == self.TYPE_URL:
            validator = URLValidator()
            try:
                validator(raw_value)
            except ValidationError:
                raise ValidationError('Enter a valid URL.')

        elif self.value_type == self.TYPE_BOOLEAN:
            if str(raw_value).lower() not in {'true', 'false'}:
                raise ValidationError('Enter a valid boolean value.')

        elif self.value_type == self.TYPE_DATE:
            try:
                datetime.date.fromisoformat(raw_value)
            except (TypeError, ValueError):
                raise ValidationError('Enter a valid date in YYYY-MM-DD format.')

    def typed_value(self):
        raw_value = (self.value or '').strip()

        try:
            return self._parse_typed_value(raw_value)
        except (TypeError, ValueError, InvalidOperation):
            return self._default_typed_value()

    @classmethod
    def get_value(cls, key, unit=None):
        variable = None

        if unit is not None:
            variable = cls.objects.filter(key=key, unit=unit).first()

        if variable is None:
            variable = cls.objects.filter(key=key, unit__isnull=True).first()

        if variable is None:
            variable = cls.objects.filter(key=key).first()

        if variable is not None:
            return variable.typed_value()

        return None
