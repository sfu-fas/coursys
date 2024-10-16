function checkRemoveAdd(slug, formIndex, maxForms) {
    var firstForm = 'tr.row_' + slug + ':first';
    // max forms allowed per grad
    if (formIndex >= maxForms) {
        $(firstForm).find('.add_button').hide();
        $(firstForm).find('.max_forms').show();
    } else {
        $(firstForm).find('.add_button').show();
        $(firstForm).find('.max_forms').hide();
    }
}

// reference: https://stackoverflow.com/questions/501719/dynamically-adding-a-form-to-a-django-formset
function addForm(slug, maxForms) {
    var formIndex= $('tr.row_' + slug).length;
    var lastForm = 'tr.row_' + slug + ':last';
    // copy new form
    var newForm = $(lastForm).clone(true);
    // update buttons
    $(newForm).find('.add_button').hide();
    $(newForm).find('.remove_button').show();
    $(lastForm).find('.remove_button').hide();
    newForm.find(':input:not([type=hidden]):not([type=button])').each(function() {
        var name = $(this).attr('name');
        // update ids for new form
        name = name ? name.replace('-' + (formIndex-1) + '-supervisor','-' + (formIndex) + '-supervisor') : '';
        var id = 'id_' + name;
        // update each new input to initially be set to 'blank'
        if (name.endsWith('supervisor_0')) {
            $(this).attr({'name': name, 'id': id}).val("-1");
        } else {
            $(this).attr({'name': name, 'id': id}).val('');
        }
    });
    newForm[0].classList = 'row_' + slug + ' subsequent';
    formIndex++;
    checkRemoveAdd(slug, formIndex, maxForms);
    $('#id_' + slug + '-TOTAL_FORMS').val(formIndex);
    $(lastForm).after(newForm);
}
function removeForm(slug, maxForms) {
    var formIndex = $('tr.row_' + slug).length;
    formIndex--;
    checkRemoveAdd(slug, formIndex, maxForms);
    $('#id_' + slug + '-TOTAL_FORMS').val(formIndex);
    // update buttons
    var lastForm = 'tr.row_' + slug + ':last';
    $(lastForm).remove();
    if (formIndex > 1) {
        var newLastForm = 'tr.row_' + slug + ':last';
        $(newLastForm).find('.remove_button').show();
    }
}

function confirmSubmit() {
    return confirm("Are you sure you wish to add these Committee Members?");
  }