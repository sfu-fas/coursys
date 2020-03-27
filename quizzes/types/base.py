class QuestionType(object):
    def __init__(self):
        pass

    def make_config_form(self):
        """
        Returns a Django Form instance that can be used to edit this question's details.

        The Form's 'cleaned_data' should match this code's 'config' object.
        """
        raise NotImplementedError()

    def make_entry_field(self, questionanswer=None):
        """
        Returns a Django Field for this question, to be filled in by the student. If questionanswer is given, it is
        a QuestionAnswer instance that must be used to populate initial data in the field.
        """
        raise NotImplementedError()

    def serialize_field(self, field):
        """
        Convert filled field (as returned by .make_entry_field) to a JSON-friendly format that can be stored in
        QuestionAnswer.answer
        """
        raise NotImplementedError()

    def to_html(self, questionanswer=None):
        """
        Convert QuestionAnswer to HTML for display to the user.
        """
        raise NotImplementedError
