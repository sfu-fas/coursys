function substitution_popup() {
  $('#subpop').dialog({
      width: 500
      });
}
function textile_popup() {
  $('#texpop').dialog({
      width: 500
      });
}

function penalty_select_logic(e) {
    // handle incompatible values in the UI
    const val = e.target.value;
    if ( e.target.checked ) {
        if (val == 'WAIT') {
            $('input[name=penalty][value!=WAIT]').prop("checked", false);
        } else if (val == 'NONE') {
            $('input[name=penalty][value!=NONE]').prop("checked", false);
        } else {
            $('input[name=penalty][value=WAIT]').prop("checked", false);
            $('input[name=penalty][value=NONE]').prop("checked", false);
        }
    }
    refer_select_logic();
}

function refer_select_logic(e) {
    // gently prod for penalty consistency when referring to chair
    const refer = $('input[name=refer]').is(':checked');
    const zero = $('input[name=penalty][value=ZERO]').is(':checked');
    let err = $('input[name=refer]').next();
    if ( err.length == 0 ) {
        $('input[name=refer]').after('<span></span>');
        err = $('input[name=refer]').next();
    }
    if ( refer && !zero ) {
        err.html('<ul class="errorlist"><li id="dynamicerror">Referring a case to the Chair is generally done because it &ldquo;deserves a penalty more severe than that imposed by the instructor&rdquo;. It is unusual (but not disallowed) to refer the case without assigning an F for the work.</li></ul>');
    } else {
        err.html('<span></span>');
    }
}

function confirm_penalty(e) {
    // setting penalty to "NONE" has more consequences than are obvious: confirm.
    if ( $('input[name=penalty][value=NONE]').prop('checked') ) {
        const confirm = window.confirm("Are you sure you want drop the case without penalty? This will close the case and make it uneditable.");
        return confirm;
    } else {
        return true;
    }
}

function setup_templates(heading) {
    let links = document.getElementsByClassName('template-link');
    for (let a of links) {
        a.addEventListener('click', function () {
            const txt = a.dataset.text;
            let fld = document.getElementById(a.dataset.field);
            if ( ! fld ) {
                fld = document.getElementById(a.dataset.field + '_0');
            }
            fld.value = txt;
        });
    }

    setup_previews(heading);

    $('input[name=penalty]').change(penalty_select_logic);
    $('input[name=refer]').change(refer_select_logic);
    $('form#penalty-form').submit(confirm_penalty);
}