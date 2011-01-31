function use_template(n) {
  // put corresponding template text in its field
  var t = templates[n];
  var input = $('#id_'+t['field']);
  input.val(t['text']);
}

function setup_templates(field) {
  // set up the template selector for this field
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

  setup_groupmembers(field);
}

function setup_groupmembers(field) {
  // set up the "use same value for other group members" box for this field
  var div, h3, ul, li, check, label, member;
  if ( groupmembers.length > 0 ) {
    div = document.getElementById('group_'+field);
    h3 = document.createElement('h3');
    h3.appendChild(document.createTextNode("Set same value for:"));
    div.appendChild(h3);
    ul = document.createElement('ul');
    div.appendChild(ul);
    
    for ( i=0; i<groupmembers.length; i++ ) {
      member = groupmembers[i];
      check = document.createElement('input');
      check.setAttribute('type', 'checkbox');
      check.setAttribute('name', 'also-' + field + "-" + member.id);

      label = document.createElement('label');
      label.appendChild(check);
      label.appendChild(document.createTextNode(member.name));
      li = document.createElement('li');
      li.appendChild(label)
      ul.appendChild(li);
    }
    
    div.style.setProperty('display','block',null);
  }
}
