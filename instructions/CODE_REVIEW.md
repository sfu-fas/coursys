# Doing Code Review

Our standard for code making it into production: at least one other developer (who didn't write the code) should review
it before it's deployed. This may be through a pull request and approval process, or something else.

## Security Concerns

Security is the most important thing to review for: does this code open any security risks? Reviewing the
[Top 10 Web Application Security Risks](https://owasp.org/www-project-top-ten/) may be pragmatic.

Access control is likely the biggest worry in code review: does each view have appropriate access control to the actions
and/or data they present? Often, each view having the right decorator from [courselib/auth.py](../courselib/auth.py)
is sufficient, but there are certainly more intricate cases that need to be double-checked by someone who understands
the system, organization, and workflow in question.


## Performance

In general, we don't seem to have performance problems unless something has gone wrong.

By far the most common thing that goes wrong is an [n+1 query problem](https://dev.to/herchila/how-to-avoid-n1-queries-in-django-tips-and-solutions-2ajo).
That is, a loop (possibly in code, possibly in a template) causes one or more database queries. The usual cause is
fetching a related object (e.g. we have the object `member` but access `member.person`, causing a query to the persons
table).

This can be detected by eye, or by looking at the queries made (add to your `localsettings.py` this line: `DEBUG_TOOLBAR = True`)
with a non-trivial amount of test data and scanning for many similar queries.

Usually,  some combination of `select_related` and `prefetch_related` on an ORM query can fix the problem. In rarer
cases, it can be necessary to restructure the view code to fetch all related objects and build some appropriate
data structure to hold them for the template to process.

