# tool to create convenient getters and setters for .config fields
def getter_setter(field):
    def getter(self):
        return self.config[field] if field in self.config else self.defaults[field]
    def setter(self, val):
        self.config[field] = val
    return getter, setter


