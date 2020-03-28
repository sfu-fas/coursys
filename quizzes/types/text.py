from .base import QuestionType, BaseConfigForm


class ShortAnswer(QuestionType):
    name = 'Short Answer'

    class ConfigForm(BaseConfigForm):
        pass
