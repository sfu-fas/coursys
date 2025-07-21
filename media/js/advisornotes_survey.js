function hideInput (field) {
    $('label[for=id_' + field + '_0]').parent().hide()
    $('label[for=id_' + field + ']').parent().hide()
    $('#id_' + field).parent().parent().hide()
}

function showInput (field) {
    $('label[for=id_' + field + '_0]').parent().show()
    $('label[for=id_' + field + ']').parent().show()
    $('#id_' + field).parent().parent().show()
}

function otherQuestionsUnansweredUpdate () {
    var questions_unanswered_checked = $('input[name=questions_unanswered]').is(':checked')
    var questions_unanswered = $('input[name=questions_unanswered]:checked')
    if (questions_unanswered.val() == 'OT' && questions_unanswered_checked === true) {
        showInput(['other_questions_unanswered'])
    } else {
        hideInput(['other_questions_unanswered'])
    }
}

function otherAdvisorReviewUpdate () {
    var advisor_review_checked = $('input[name=advisor_review]').is(':checked')
    console.log(advisor_review_checked)
    var advisor_review = $('input[name=advisor_review][value="OT"]:checked')
    console.log(advisor_review)
    if (advisor_review.val() == 'OT' && advisor_review_checked === true) {
        showInput(['other_advisor_review'])
    } else {
        hideInput(['other_advisor_review'])
    }
}

function otherReasonUpdate () {
    var reason_checked = $('input[name=reason]').is(':checked')
    var reason = $('input[name=reason]:checked')
    if (reason.val() == 'OT' && reason_checked === true) {
        showInput(['other_reason'])
    } else {
        hideInput(['other_reason'])
    }
}

$(document).ready(function() {
    otherQuestionsUnansweredUpdate()
    otherAdvisorReviewUpdate()
    otherReasonUpdate()
    $('#id_reason').change(otherReasonUpdate)
    $('#id_questions_unanswered').change(otherQuestionsUnansweredUpdate)
    $('#id_advisor_review').change(otherAdvisorReviewUpdate)
    
})