const preview_url = JSON.parse(document.getElementById('preview-url').textContent);

function update_preview(heading, preview, textarea, markup, math) {
        const params = new URLSearchParams();
        params.set('content', textarea.value);
        params.set('markup', markup.value);
        let m;
        if ( math === null ) {
            m = false;
        } else {
            m = math.checked;
        }
        params.set('math', m);

        let oReq = new XMLHttpRequest();
        oReq.open("GET", preview_url + "?" + params.toString());
        oReq.addEventListener("load", function() {
            if ( this.readyState == 4 && this.status == 200 ) {
                let resp = JSON.parse(this.responseText);
                preview.html('<h4 style="clear:right;">' + heading + '</h4>' + resp.html);
                if ( m ) {
                    MathJax.typeset(preview);
                }
            }
        });
        oReq.send();
}

function setup_preview(heading, editor) {
    let textarea = editor.querySelector('textarea');
    let markup = editor.querySelector('select');
    let math = editor.querySelector('input[type=checkbox]');

    let preview = $('<div class="markup-preview"></div>');
    $(textarea.closest('form')).append(preview);

    // "when-typing-stops" behaviour from https://schier.co/blog/wait-for-user-to-stop-typing-using-javascript
    let timeout = null;
    textarea.addEventListener('keyup', function (e) {
        clearTimeout(timeout);
        timeout = setTimeout(function () {
            update_preview(heading, preview, textarea, markup, math);
        }, 1000);
        return timeout;
    });
    markup.addEventListener('change', function(e) {
        update_preview(heading, preview, textarea, markup, math);
    });
    if ( math !== null ) {
        math.addEventListener('change', function (e) {
            update_preview(heading, preview, textarea, markup, math);
        });
    }
}

function setup_previews(heading) {
    $('.markup-content').each(function(i, e) {
        setup_preview(heading, e);
    });
}
