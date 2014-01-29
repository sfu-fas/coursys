class CareerEventHookBase(object):

    # Form Stuff

    def modify_entry_form(self, form):
        pass

    # Saving Stuff

    def pre_save(self, event):
        pass

    def post_save(self, event):
        pass


class InstantCareerEvent(CareerEventHookBase):
    '''
    Should make start_date automatically equal end_date.
    '''

    def modify_entry_form(self, form):
        del form.fields['end_date']

    def pre_save(self, event):
        event.start_date = event.end_date


class ExclusiveCareerEvent(CareerEventHookBase):
    '''
    Should close the current CareerEvent of the same type if it has not ended yet.
    '''
    pass


class SemesterCareerEvent(CareerEventHookBase):
    '''
    Should change the widget used for dates to a semester choice list.
    '''
    pass
