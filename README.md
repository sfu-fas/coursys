
CourSys
=======

[![Build Status](https://travis-ci.org/sfu-fas/coursys.svg?branch=master)](https://travis-ci.org/sfu-fas/coursys)

## Getting Started

See [SETUP.md](instructions/SETUP.md) for instructions to get a development environment set up.


## Notable Test Data

* An instructor: ggbaker
* A system administrator: sumo
* An advisor: dzhao
* Some Grad students: 0aaagrad, 0bbbgrad, 0cccgrad...
* Some Undergrad students: 0aaa0... 0aaa19, 0bbb0...0bbb19... 

## Best Practices

Here's some stuff that we almost always tell our students about in the first week of Coursys work. 

### Status Fields

Often, a model can be in one of several states. 

A form from our forms system, for example, can be Active, Inactive, Waiting, 
Stalled, Happy, Sad, Grumpy, or Sleepy.

Generally, statuses start as a list of tuples, like so: 

    NOTE_CATEGORIES = (
        ("EXC", "Exceptions"),
        ("WAI", "Waivers"),
        ("REQ", "Requirements"),
        ("TRA", "Transfers"),
        ("MIS", "Miscellaneous")
    )

This list can be fed directly to a CharField in a Model, like so: 

    category = models.CharField(max_length=3, choices=NOTE_CATEGORIES)

When accessing the model's 'category' field, it will return the three-letter-code, 
but you can - for example, in a template - return the 'pretty wording' using the 
`.get_foo_display` property. 

    note.get_category_display

### Persons and Roles

For every person in the system, there is a `coredata.models` Person object. 

The Role object has a foreign key to the Person object. The Role object 
describes "one job" that is held by that Person. A Person can have many roles - 
in the live system, for example, I am one of just about everything, for the 
purposes of debugging and also occasional larceny. 

It is possible to restrict access to a view to _just people who have a specific role_, 
using the `@requires_role` decorator. 

*Most of the views you write should have one of these decorators.*

    @requires_role("ADVS")
    def view_student_notes(...):
        ...

Anybody who attempts to trigger this view without having a Role object of the 
type "ADVS" foreign-keyed to their account will just get an Access Denied message.

### Unit

Many things have a `coredata.models` "Unit" associated with them. This is a way 
of subdividing parts of the system by school in the university - Units include 
groups like "CMPT", "ENGI", "MSE", corresponding to different logical groups within SFU. 

Roles must be created with a Unit. You can't just be an "Advisor", you have to 
be an "Advisor in CMPT" or an "Advisor in MSE". 

The `requires_role` decorator automatically appends to the request object a 
list of units that the current user has _this role_ for, in `request.units`.

So, for example, if I'm a CMPT Advisor and MSE Advisor, and I'm logged in: 

    @requires_role("ADVS")
    def view_student_notes(self, request):
        print request.units

This request.units should contain the "CMPT" and "MSE" Unit model objects. 

Only show users the data that they are allowed to see, considering their unit, 
as follows:

    @requires_role("ADVS")
    def view_student_notes(self, request):
        notes = Notes.objects.filter(unit__in=request.units)
        ...

### Autoslugs and URLs

We want to keep our URLs as tidy and human-readable as possible. 

Bad:

    coursys.cs.sfu.ca/forms/923

Good:

    coursys.cs.sfu.ca/forms/course_appeal_form

The [django-autoslug](https://pypi.python.org/pypi/django-autoslug)
package has got us covered - when creating a model, we can create an 'autoslug' 
field, point it at another field in the model, and from that point on the model 
has a 'slug' field that we can search on.

For more complicated slug logic, we can create an 'autoslug' function. 
See `/advisornotes/models.py` for an example: 

    class Artifact(models.Model):
        name = models.CharField(max_length=140, help_text='The name of the artifact', null=False, blank=False)
        category = models.CharField(max_length=3, choices=ARTIFACT_CATEGORIES, null=False, blank=False)
        
        def autoslug(self):
            return make_slug(self.unit.label + '-' + self.name)
        
        slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, unique=True)
        unit = models.ForeignKey(Unit, help_text='The academic unit that owns this artifact', null=False, blank=False, on_delete=models.PROTECT)
        config = JSONField(null=False, blank=False, default=dict)  # additional configuration stuff:

Here we're automatically making a slug out of the Artifact's unit (CMPT) 
and name - "cmpt-thingamajigger".

### Hardcoding URLs.

Never hardcode URLs. Use Django's built in `reverse` or the `url` template-tag,
instead. 

### Config Fields

When building models that may change in the future (pro-tip: this is most models)
we often include an empty JSON field in the model. 
 
    config = JSONField(null=False, blank=False, default=dict)

When working with the config field, it's considered polite to include any fields
that we might be storing in the config field as a comment. 

    # phonenumber - the user's phone number
    # words - words words words

The config field can be treated as an object:

    model_object.config["data"] = "harblar"

But before accessing config data, always protect against a KeyError or check 
if the data exists:

    if "data" in model_object.config:
        data = model_object.config["data"]
    else:
        data = "STEVE"

### Hidden Fields

We try our very best to never delete anything. Instead, we set a 'hidden' flag,
and filter out all 'hidden' variables every time that we pull data 
from the database. 

Here's an example from the Grad subsystem: 

    hidden = models.BooleanField(null=False, default=False)

    req = GradRequirement.objects.filter(program=grad.program, hidden=False)

### Logging

All actions that modify the database should be logged with a log.models.LogEntry
object.

### ModelForms, as_dl, and Widgetry

Let's imagine that we have a Model:

    CAMPUS_CHOICES = (
        "BNBY", "Burnaby",
        "SRRY", "Surrey",
        "HRBR", "Harbour Centre"
    )

    class CampusRestaurant(models.Model):
        location = models.CharField(max_length=100)
        opened = models.DateField()
        campus = models.CharField(max_length=4, choices=CAMPUS_CHOICES)
        config = JSONField(null=False, blank=False, default=dict)

Now, if we want to take full advantage of Django's forms functionality, we'll
have to create a Form:

    class CampusRestaurantForm(forms.ModelForm):
        location = forms.CharField(max_length=100)
        opened = forms.DateField()
        campus = ...

okay, I'm going to stop us right there and point out the obvious: we could just
be pulling this information out of the Model, right? Right. See:

    class CampusRestaurantForm(forms.ModelForm):
        class Meta:
            model = CampusRestaurant

Here, the [ModelForm](http://pydanny.com/core-concepts-django-modelforms.html) is
converting the CampusRestaurantModel into a CampusRestaurantForm, with all
of the validation and POST-processing logic that comes with a Form object. 
Hooray!

There's a pretty standard view for dealing with a form like this:

    @login_required
    def new_restaurant(request):
        if request.method == 'POST':
            form = CampusRestaurantForm(request.POST)
            if form.is_valid():
                restaurant = form.save(commit=False)
                restaurant.save()
                messages.add_message(request, 
                                     messages.SUCCESS, 
                                     u'Restaurant %s created.' % unicode(restaurant))
                return HttpResponseRedirect(reverse('campus_eating.views.home'))
        else:
            form = CampusRestaurantForm()

        return render(request, 'campus_eating/new_restaurant.html', {
                      'form':form})

And with that in place, we can render the form into HTML, inside `new_restaurant.html`, 
using:

    {% load form_display %}
    {{ form|as_dl }}

Which is good, but when we visit that page, it contains the config field, which
we don't want to show to users. And we'd like to handle our DateTimeField with
a Calendar, rather than just a standard text field. 

We can solve that first problem by adding `editable=False` as one of the arguments
to config in the Model: 
        
    config = JSONField(null=False, blank=False, editable=False, default=dict)

With that in place, config won't show up in any ModelFields. 

As for the calendar, there's a Widget for that:

    from coredata.widgets import CalendarWidget

    class CampusRestaurantForm(forms.ModelForm):
        class Meta:
            model = CampusRestaurant
            widgets = {'opened':CalendarWidget}

There are more useful widgets and fields in coredata.widgets - the OfferingField
and PersonField can be used to easily build an Foreign Key to a CourseOffering
or Person. 

There are a lot of good examples of this in `tacontracts/forms.py`.

### Fat Models, Thin Views, Skinny Templates

Logic belongs in models before views, and views before templates.

In a quote from Two Scoops of Django - 
http://twoscoopspress.com/products/two-scoops-of-django-1-6 :

> When deciding where to put a piece of code, we like to follow the 'Fat Models,
> Helper Modules, Thin Views, Stupid Templates' approach.

> We recommend that you err on the side of putting more logic into anything but
> views and templates.

> The results are pleasing. The code becomes clearer, more self-documenting, 
> less duplicated, and a lot more reusable. 

> As for template tags and filters, they should contain the minimum logic 
> possible to function.

### Testing

Wherever possible, test your application in *yourapp*/tests.py

### Code Standards

These are expected of all code in the system:

* All actions that modify the database should be logged with a new `log.models.LogEntry` object.
* All views should have an appropriate permissions decorator (like `@requires_course_staff_by_slug`). If not, then be very careful when checking permission in the code.
* Where possible, create unit tests in `app/tests.py`. Check that the unit tests pass before committing changes.
* Have a look at the [Style Guide for Python](https://www.python.org/dev/peps/pep-0008/) and try to follow it as much as possible.
    * If you like to use an IDE, [PyCharm](https://www.jetbrains.com/pycharm/), which has free licenses for students/educational staff, it will check for PEP 0008 compliance for you

### Coursys vs Courses
**CourSys** (the system) is located at courses.cs.sfu.ca

The codebase is located in a folder called 'courses'. Moving it will cause things to break.

It's confusing, I know.

As an attempt to clarify the nomenclature:

**"Coursys"** is the Brand Name of the system. Use it when describing the system. This is the displayed name of the system.

**"courses"** is the name of the codebase and core libraries.

So, you check out and build **courses**, which gives you a running instance of **CourSys**.

Table of Contents
-----------------

Here is a quick description of what is in the project:

### APPS
* coredata: data on course offerings and enrolment; imported from goSFU or set by admins
  * coredata/importer.py: program to do the import from goSFU
* dashboard: responsible for display of front page, main course pages, news items
* discipline: handling academic dishonesty cases
* grades: management of course activities and grades
* groups: handling groups so assignments can be group-based
* log: finer-grained logging for the system
* marking: finer-grained marking with a rubric
* submission: submission of work (for later grading)
* ta: management of TA applications and assignment
* tacontracts: management of TA contracts 
* grad: grade student database
* ra: research assistant database and appointments
* advisornotes: advisor notepads for student advising
* discuss: discussion forum for course offerings
* pages: wiki-like course web pages
* onlineforms: configurable and fillable online forms
* visas: Visa management for grads and whoever else we want to manually manage
* oldcode:  Dead/unused/unfinished code, including:
    * alerts: automated student problem alerts (zombie code.  Not used at all anymore)
    * planning: planning of courses, assigning instructors, etc. (incomplete and disabled).  This one will possibly get finished.
    * techreq: collection of technical requirements for courses (incomplete and disabled)
    * booking: booking system for advisors (incomplete and disabled)
    * gpaconvert: GPA conversion code for grades from other places (incomplete and disabled)

### OTHER TOP-LEVEL FILES/DIRECTORIES
* courselib: various library code for the system
* external: external code used by the system
* machines: Vagrant and Chef files to set up development, testing, and production environments
* media: static web files (CSS, JS, images, etc.)
* server-setup: description of how the production server is configured.
* tools: various scripts that have been used to manage the data as necessary

Other files are the standard Django setup.

