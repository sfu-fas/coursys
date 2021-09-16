const thread_list_url = JSON.parse(document.getElementById('thread-list-url').textContent);
const preview_url = JSON.parse(document.getElementById('preview-url').textContent);

function by_score(a, b) {
    const ascore = parseFloat(a.getElementsByClassName('reactions')[0].dataset.score);
    const bscore = parseFloat(b.getElementsByClassName('reactions')[0].dataset.score);
    if ( ascore == bscore ) {
        return by_time_oldest(a, b);
    } else {
        return bscore - ascore;
    }
}

function by_time_oldest(a, b) {
    const atime = a.getElementsByClassName('post-header')[0].dataset.datetime;
    const btime = b.getElementsByClassName('post-header')[0].dataset.datetime;
    return atime.localeCompare(btime, 'en');
}

function by_time_newest(a, b) {
    return by_time_oldest(b, a);
}

function sort_replies(button_id, cmp) {
    var replies = Array.from(document.getElementsByClassName('thread-reply'));
    // sort by the requested comparator
    replies.sort(cmp);
    for (let i = 0; i < replies.length; i++) {
        replies[i].parentNode.appendChild(replies[i]);
    }
    // highlight the current sort button
    $('.sort-button').removeClass('active');
    $('#' + button_id).addClass('active');
}
function sort_setup(button_id, cmp) {
    const button = $('#' + button_id);
    button.click(() => sort_replies(button_id, cmp));
}

function fragment_update(target_id, url, inplace) {
    // update #target_id with content fetched from url?fragment=yes
    // if inplace, we're refreshing the current content, else it's a new page and scroll to the top
    // TODO https://stackoverflow.com/questions/7949040/restoring-content-when-clicking-back-button-with-history-js
    // TODO mathjax rendering
    let oReq = new XMLHttpRequest();
    if ( url.indexOf('?') > -1 ) {
        oReq.open("GET", url + '&fragment=yes');
    } else {
        oReq.open("GET", url + '?fragment=yes');
    }

    oReq.addEventListener("load", function() {
        if ( this.readyState == 4 && this.status == 200 ) {
            document.getElementById(target_id).innerHTML = this.responseText;
            if ( target_id == 'main-panel' ) {
                if ( ! inplace ) {
                    window.scroll({top: 0, left: 0, behavior: 'smooth'});
                }
                const real_url = this.responseURL.replace('fragment=yes', '');
                history.pushState({}, '', real_url);
            }
            partial_links_setup();
            if ( this.getResponseHeader('X-update-thread-list') == 'yes' ) {
                fragment_update('thread-list', thread_list_url)
            }
        }
    });
    oReq.send();
}

function partial_links_setup() {
    // set up all links with data-target="" to be partial page redraws
    document.querySelectorAll('a[data-target]').forEach((a) => {
        a.onclick = function(e) {
            e.preventDefault();
            fragment_update(this.dataset.target, this.getAttribute('href'), a.hasAttribute('data-inplace'))
        };
    });
    // and forum class="xref" links
    document.querySelectorAll('a.xref').forEach((a) => {
        a.onclick = function(e) {
            e.preventDefault();
            fragment_update('main-panel', this.getAttribute('href'), false)
        };
    });
}

function update_preview(preview, textarea, markup, math) {
        const params = new URLSearchParams();
        params.set('content', textarea.value);
        params.set('markup', markup.value);
        params.set('math', math.checked);

        let oReq = new XMLHttpRequest();
        oReq.open("GET", preview_url + "?" + params.toString());
        oReq.addEventListener("load", function() {
            if ( this.readyState == 4 && this.status == 200 ) {
                let resp = JSON.parse(this.responseText);
                preview.html('<h4 style="clear:right;">Post Preview</h4>' + resp.html);
                if ( math.checked ) {
                    MathJax.typeset(preview);
                }
            }
        });
        oReq.send();
}

function setup_preview(editor) {
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
            update_preview(preview, textarea, markup, math);
        }, 2000);
        return timeout;
    });
    markup.addEventListener('change', function(e) {
        update_preview(preview, textarea, markup, math);
    });
    math.addEventListener('change', function(e) {
        update_preview(preview, textarea, markup, math);
    });
}

$(document).ready(() => {
    //partial_links_setup();
    sort_setup('sort-score', by_score);
    sort_setup('sort-time', by_time_oldest);
    sort_setup('sort-time-newest', by_time_newest);

    $('.markup-content').each(function(i, e) {
        setup_preview(e);
    });
});
