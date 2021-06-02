const forum_base_url = JSON.parse(document.getElementById('forum-url').textContent);

function by_score(a, b) {
    const ascore = parseFloat(a.getElementsByClassName('reactions')[0].dataset.score);
    const bscore = parseFloat(b.getElementsByClassName('reactions')[0].dataset.score);
    if ( ascore == bscore ) {
        return by_time(a, b);
    } else {
        return bscore - ascore;
    }
}

function by_time(a, b) {
    const atime = a.getElementsByClassName('post-header')[0].dataset.datetime;
    const btime = b.getElementsByClassName('post-header')[0].dataset.datetime;
    return atime.localeCompare(btime, 'en');
}

function by_time_newest(a, b) {
    const atime = a.getElementsByClassName('post-header')[0].dataset.datetime;
    const btime = b.getElementsByClassName('post-header')[0].dataset.datetime;
    return btime.localeCompare(atime, 'en');
}

function sort_replies(button_id, cmp) {
    var replies = Array.from(document.getElementsByClassName('thread-reply'));
    replies.sort(cmp);
    for (let i = 0; i < replies.length; i++) {
        replies[i].parentNode.appendChild(replies[i]);
    }
}

$(document).ready(() => {
    $('#sort-score').click(() => sort_replies('sort-score', by_score));
    $('#sort-time').click(() => sort_replies('sort-time', by_time));
    $('#sort-time-newest').click(() => sort_replies('sort-time-newest', by_time_newest));
});
