from django.core.checks import Error
from django.db.utils import OperationalError, ProgrammingError
from bitfield import BitField

def _add_error(errors, msg, ident):
    errors.append(
        Error(
            msg,
            hint=None,
            obj=BitField,
            id='coredata.E%03i' % (ident)
        )
    )

def bitfield_check(app_configs, **kwargs):
    """
    The BitField claims it doesn't work in mysql, but what we need has always seemed to be okay. This system check
    makes sure that the subset of behaviour we expect from BitField is there.
    """
    errors = []

    from coredata.models import CourseOffering, OFFERING_FLAG_KEYS
    assert OFFERING_FLAG_KEYS[0] == 'write'

    # find an offering that should be returned by a "flag" query
    try:
        o = CourseOffering.objects.filter(flags=1).first()
    except (OperationalError, ProgrammingError):
        # probably means no DB migration yet: let it slide.
        return []
    if o is None:
        # no data there to check
        return []

    # ... and the filter had better find it
    found = CourseOffering.objects.filter(flags=CourseOffering.flags.write, pk=o.pk)
    if not found:
        _add_error(errors, 'Bitfield set-bit query not finding what it should.', 1)
    # ... and the opposite had better not
    found = CourseOffering.objects.filter(flags=~CourseOffering.flags.write, pk=o.pk)
    if found:
        _add_error(errors, 'Bitfield negated-bit query finding what it should not.', 2)

    # find an offering that should be returned by a "not flag" query
    o = CourseOffering.objects.filter(flags=0).first()
    # *** This is the one that fails on mysql. We don't use it, so hooray.
    # ... and the filter had better find it
    #found = CourseOffering.objects.filter(flags=~CourseOffering.flags.write, pk=o.pk)
    #if not found:
    #    _add_error(errors, 'Bitfield negated-bit query not finding what it should.', 3)

    # .. and the opposite had better not
    found = CourseOffering.objects.filter(flags=CourseOffering.flags.write, pk=o.pk)
    if found:
        _add_error(errors, 'Bitfield set-bit query finding what it should not.', 4)

    return errors