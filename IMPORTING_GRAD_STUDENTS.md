
So, it's the beginning of the semester, and you need to import some grad students! 

Let's imagine that the current semester is 1157, and the unit is MSE

Simply run: 

    python manage.py new_grad_students --semester=1157 --unit=MSE

This should work with MSE, ENSC, or CMPT. For units that aren't MSE, ENSC, or CMPT, 
you may need to modify the code in /grad/management/commands/new_grad_students.py, which
contains a hard-coded mapping between SIMS program codes (like "MSEPH") and CourSys GradPrograms 
(like <GradProgram "Mechatronics PhD Program">)

It might ask you to reconcile some grad student records with records that already exist.
90% of the time, new applications should mean new grad records, so the best option
is almost always "N".

Hey, wouldn't it be nice if this were automatic? 

Yes. Yes it would be. Integrating this with the automatic grad update functionality in grad/models.py
would be a wonderful idea. 
