function get_fingerprint() {
    var options = {excludes: {canvas: true, webgl: true, enumerateDevices: true, availableScreenResolution: true}};
    if (window.requestIdleCallback) {
        requestIdleCallback(function () {
            Fingerprint2.get(options, function (components) {
              $('#fingerprint').val(JSON.stringify(components));
            })
        })
    } else {
        setTimeout(function () {
            Fingerprint2.get(options, function (components) {
              $('#fingerprint').val(JSON.stringify(components));
            })
        }, 500)
    }
}

function update_time_left(ends_at) {
    var now = Date.now() / 1000;
    var seconds_left = ends_at - now;
    if ( seconds_left >= 0 ) {
        var m = Math.floor(seconds_left/60);
        var s = "00" + Math.floor(seconds_left % 60); // zero-pad the seconds
        s = s.substr(s.length - 2);
        var cls = '';
        if ( seconds_left < 60 ) {
            cls = 'warningmessage';
        }

        $('#time-left').html('<span class="' + cls + '">' + m + '&#8239;m ' + s + '&#8239;s</span> (approximate)');
        setTimeout(function() { update_time_left(ends_at) }, 500)
    } else {
        $('#time-left').html('<span class="errormessage">Time is up. Submit immediately!</span>');
    }
}

function randomly_perturb(v) {
    // wiggle +- 10%, to prevent dogpiling on autosave
    return v - v*0.1 + v*0.2*Math.random()
}
function start_autosave(interval) {
    setTimeout(function() { do_autosave(interval); }, randomly_perturb(interval));
}
function do_autosave(interval) {
    var form = $("form.quiz");
    var data = new FormData(form.get(0));

    $.ajax({
        type: "POST",
        url: form.attr('action') + '?autosave=yes',
        data: data,
        processData: false,
        contentType: false,
        success: function(resp) {
            if( resp.status == 'ok' ) {
                window.createNotification({
                    theme: 'success',
                    showDuration: 5000
                })({ message: 'Answers auto-saved.' });
            } else {
                // form validation problem
                var errors = resp.errors;
                Object.keys(errors).forEach(function(field) {
                    var error_div = $('#' + field).find('div.dynamic-errors');
                    error_div.html(errors[field])
                });
                window.createNotification({
                    theme: 'warning',
                    showDuration: 5000
                })({ message: 'Unable to auto-save your answers: there is a problem with one of your answers that cannot be saved.' });
            }
            },
        error: function(msg) {
            window.createNotification({
                theme: 'warning',
                showDuration: 5000
            })({ message: 'Unable to auto-save your answers: check your network connection.' });
        }
    });
    setTimeout(function() { do_autosave(interval); }, randomly_perturb(interval));
}

function show_honour_code() {
    $('#quiz-body').hide();
    $('#photo-verification').hide();
    $('form.quiz input[type=submit].submit').hide();
    $('#honour-yes').click(function(ev) {
        $('#quiz-body').show();
        $('#photo-verification').show();
        $('form.quiz input[type=submit].submit').show();
        $('#input-honour-code').val('YES');
        $('#honour-agree').hide();
        ev.preventDefault();
    });
    $('#honour-no').click(function(ev) {
        window.location = '/';
        ev.preventDefault();
    });
}


// Photo-taking based on https://developer.mozilla.org/en-US/docs/Web/API/WebRTC_API/Taking_still_photos

var width = 320;
var height = 0;
var streaming = false;
var video = null;
var canvas = null;
var photo = null;
var startbutton = null;
var photoinput = null;

function capture_startup() {
    video = $('#capture video')[0];
    canvas = $('#capture canvas')[0];
    photo = $('#capture img')[0];
    startbutton = $('#capture #capture-photo')[0];
    photoinput = $('#capture input')[0];
    $('#restart-capture').click(function(ev) {capture_startup(); ev.preventDefault();});
    $('#abort-capture').click(function(ev) {submit_enable(); ev.preventDefault();});

    navigator.mediaDevices.getUserMedia({video: true, audio: false})
    .then(function(stream) {
        video.srcObject = stream;
        video.play();
    })
    .catch(function(err) {
        console.log("An error occurred: " + err);
    });

    video.addEventListener('canplay', function(ev){
        if (!streaming) {
            height = video.videoHeight / (video.videoWidth/width);
            if (isNaN(height)) {
                height = width / (4/3);
            }
            video.setAttribute('width', width);
            video.setAttribute('height', height);
            canvas.setAttribute('width', width);
            canvas.setAttribute('height', height);
            streaming = true;
        }
    }, false);

    startbutton.addEventListener('click', function(ev){
        takepicture();
        ev.preventDefault();
    }, false);

    clearphoto();
}

function clearphoto() {
    var context = canvas.getContext('2d');
    context.fillStyle = "#AAA";
    context.fillRect(0, 0, canvas.width, canvas.height);

    var data = canvas.toDataURL('image/png');
    photo.setAttribute('src', data);
    submit_disable();
}

function takepicture() {
    var context = canvas.getContext('2d');
    if (width && height) {
        canvas.width = width;
        canvas.height = height;
        context.drawImage(video, 0, 0, width, height);

        var data = canvas.toDataURL('image/png');
        photo.setAttribute('src', data);
        photoinput.value = data;
        submit_enable();
    } else {
        clearphoto();
    }
}

function submit_disable() {
    var submit = $('form.quiz input[type=submit].submit');
    submit.click(function(ev) {
        alert("You must take a verification photo before submitting.")
        ev.preventDefault();
    });
}
function submit_enable() {
    var submit = $('form.quiz input[type=submit].submit');
    submit.unbind('click');
}