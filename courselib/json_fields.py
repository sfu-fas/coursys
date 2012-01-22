import copy

# tool to create convenient getters and setters for .config fields
def getter_setter(field):
    def getter(self):
        return self.config[field] if field in self.config else copy.copy(self.defaults[field])
    def setter(self, val):
        self.config[field] = val
    return getter, setter

# for nested config fields
def getter_setter_2(field, subfield):
    def getter(self):
        return (self.config[field][subfield] 
                if field in self.config 
                else copy.copy(self.defaults[field][subfield]))
    def setter(self, val):
        self.config[field][subfield] = val
    return getter, setter
