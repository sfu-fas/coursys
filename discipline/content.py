# this module requires a lot of text content: separated into this file to make it more managable.
import string

EMAIL_TEMPLATE = string.Template("""$introsentence I believe this may be a violation of SFU's Code of Academic Integrity and Good Conduct, Policy S10.01. I take academic honesty very seriously and intend to pursue this apparent violation of SFU's standards for academic honesty.

As required by SFU Policy S10.02, Principles and Procedures for Academic Discipline, I am offering you the opportunity to meet with me to discuss this incident. You are not required to accept this offer. If you would like to meet, please contact me to make an appointment outside of my regular office hours.

You may wish to refer to SFU's policies and procedures on academic integrity,
  http://www.sfu.ca/policies/Students/index.html .
You can also contact the Office of the Ombudsperson for assistance in navigating University procedures.""")
