from dirtyfields import DirtyFieldsMixin


class ConditionalSaveMixin(DirtyFieldsMixin):
    def save_if_dirty(self, *args, **kwargs):
        if self.is_dirty():
            self.save(*args, **kwargs)