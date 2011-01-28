function use_template(n) {
  var t = templates[n];
  var input = $('#id_'+t['field']);
  input.val(t['text']);
}

function setup_templates(field) {
  var div = document.getElementById('templates_'+field);
  var h3, ul, li, a, i, t;
  var count = 0;
  ul = document.createElement('ul');
  for ( i=0; i<templates.length; i++ ) {
    t = templates[i];
    if ( t['field'] == field ) {
      count += 1;
      li = document.createElement('li');
      a = document.createElement('a');
      a.setAttribute('href', 'javascript:use_template(' + i + ')');
      a.setAttribute('title', t['text']);
      a.appendChild(document.createTextNode(t['label']));
      li.appendChild(a);
      ul.appendChild(li);
    }
  }

  if ( count > 0 ) {
    h3 = document.createElement('h3');
    h3.appendChild(document.createTextNode("Templates"));
    div.appendChild(h3);
    div.appendChild(ul);
    div.style.setProperty('display','block',null);
  }
  return;
}

