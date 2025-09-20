# First Name Usage

Short answer: we import the "chosen name" for each person, what SIMS calls "preferred name". It should be used everywhere unless there is a very good reason otherwise.

## Legal Names

We do store "legal name" as `Person.config['legal_first_name_do_not_use']` and can produce a person's legal first name with `Person.legal_first_name_because_its_unavoidable()`. These names should give a hint about how much they should be used, and should also be easily greppable if it's necessary to find their use.

## Using Legal Name

In short, CourSys treats legal name as "regulated data", not "internal data" according to [SFU's Data security standard](https://www.sfu.ca/information-systems/information-security/data-security-standard/types-of-data.html).

If there is a particular context where it seems like legal name is necessary, its use should be discussed with and approved by an appropriate data steward within the University. That may be:
* the Registrar for students, particularly undergraduate students;
* the Director of Grad Studies for graduate students;
* Directors in Human Resources or Faculty Relations for HR matters;
* Directors in IT Services who oversee information systems, who can at least guide us to the appropriate domain expert.

I will point out that none of of the data stewards work in FAS or any of its departments: this may be a time when developers have to say no and refer to University policy.

## Uses of Legal Name

Places we actually use legal name in the system:

### Search Indexes

Anywhere people can be searched for by name (`*/search_indexes.py`), we include legal name in the index but **not** the display. This is often necessary when people identify themselves by legal name (in email, on a form, on an exam paper, etc) and staff need to find them. Indexing legal name will allow people who already know someone's legal name to find them but won't directly expose it.

### Grad Letters

Some of the grad letters (`grad.models.LetterTemplate` and `grad.models.Letter`) are used externally (e.g. for visa applications) for now, these use legal name exclusively, which has been the previous behaviour. Decisions on necessity and/or code to control this is pending. (Sept 2025)

### TA/RA/Sessional Contracts

From Daisy Larosa, Labour and Employee Relations Specialist, 2025-09-16:

> I’ve reached out to OGC (Kailey Graham) and below is their response:
> 
> “Strictly speaking there is no requirement that we use an employee’s legal name on offer letters. Our court has enforced employment agreements without the employee’s legal name (e.g. Adams v Thinkific Labs Inc., 2024 BCSC 1129). As you have stated below though, it is best practice to use legal names in contracts to ensure enforceability, and it may also be needed for other purposes like government documentation. If IT wants to proceed with chosen names, I would recommend still identifying the legal name as well as the chosen name in the preamble of the letter so that there can be no confusion as to who the employee is.”

We have applied this to:
* RA offer letters (`ra.views.request_offer_letter`): signed by appointee.
* **not** RA payroll appointment forms (`ra.views.request_paf`): internal communication identified by emplid.
* Sessional contracts (`sessional.views.print_contract`): signed by appointee.
* TA contract offer (`ta.views.accept_contract`): agreed to online.
* TA appointment form (`ta.views.view_form` and `tacontract.views.print_contract`): signed by appointee.
