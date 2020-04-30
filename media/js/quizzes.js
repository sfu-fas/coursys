function get_fingerprint() {
    var options = {excludes: {canvas: true, webgl: true, enumerateDevices: true}};
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
        setTimeout(function() { update_time_left(ends_at) }, 0.5)
    } else {
        $('#time-left').html('<span class="errormessage">Time is up. Submit immediately!</span>');
    }
}
