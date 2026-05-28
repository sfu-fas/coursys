# Testing

## Django Tests

The various `*/tests.py` should have decent coverage of the system. (The actual coverage varies.)

In general, tests should be runnable in the standard way:
```shell
python ./manage.py test
```

You *may* have to remove or clean your `courses/localsettings.py` to run the tests: they expect a fairly dev-like environment.


## Test Data

Fixtures available for testing (`fixtures/*.json`) are generated as described in `BUILD_TEST_DATA.md`, with most of the logic to create them in `coredata/devtest_data_generator.py`.


## Page Tests

We have a common pattern of using `courselib.testsing.test_views` to check the rendering of most/many/all views for a module. It checks that the page successfully renders, returns a 200 Okay, and produces valid HTML.

This isn't the best test in the world, but it's at least something vaguely end-to-end, ensuring that things can be instantiated, run, and produce sane output. It has also previously caught regressions on Django version updates, where our code assumes something about the internal workings of an object that has been changed.

e.g. to test views with two different collections of variables in their URL patterns, the `tests.py` would be something like:
```py
from django.test import TestCase
from courselib.testing import Client, test_views

class PagesTest(TestCase):
    fixtures = ['basedata', 'coredata']
    def test_pages(self):
        offering = ...
        activity = ...

        c = Client()
        c.login_user('whoever')
        test_views(self, c, 'viewprefix:', ['index', 'foo'], {'course_slug': offering.slug})
        test_views(self, c, 'viewprefix:', ['info'], {'course_slug': offering.slug, 'activity_slug': activity.slug})
```


## Python Version Checks

There can be differences between Python version, and specifically the version running in production. These issues have been rare, but we should at least have a method to test compatibility.

Pyenv seems to provide a reasonably-convenient way to do this. First, [install pyenv and set up your environment](https://github.com/pyenv/pyenv#installation). (i.e. the `pyenv` command should work.)

Then you can select a Python version and test with it:
```shell
pyenv install 3.8
pyenv virtualenv 3.8 coursys
pyenv activate coursys  # temporarily puts this shell into that Python version & virtualenv
pip install -r requirements.txt 
python ./manage.py test
pyenv deactivate
```