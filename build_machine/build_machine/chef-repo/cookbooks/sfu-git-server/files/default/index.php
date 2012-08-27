<?php 
// This is a script allowing for arbitrary users to add themselves to the 'authorized_keys' file for the 'git' user.

// The 'git' user has no shell, so this user can only be used to access git repositories. 

$error = '';

if ($_POST['key'] && $_POST['key'] != ''){
  $attempted_key = $_POST['key'];
  $exploded_key = explode( ' ', $attempted_key );
  if (count( $exploded_key ) != 3){
    $error = "Your key wasn't formatted in a way that I can understand. Perhaps you included erroneous whitespace?";
  } 
  else if ( $exploded_key[0] != "ssh-rsa"){
    $error = "Please provide a key of type 'ssh-rsa'";
  } 
  else {
    $error = "Success!";
    file_put_contents( '/home/git/.ssh/authorized_keys', "\n".$_POST['key'], FILE_APPEND | LOCK_EX ); 
  }
}

$authorized_keys_string = file_get_contents( '/home/git/.ssh/authorized_keys' );

$authorized_keys = array();
foreach( explode( "\n", $authorized_keys_string) as $authorized_key_string ){
  $split_string = explode(' ', $authorized_key_string);
  $key = array();
  if( count( $split_string ) == 3 )
  {
    $key['type'] = $split_string[0];
    $key['value'] = $split_string[1];
    $key['owner'] = $split_string[2];
    $authorized_keys[] = $key;
  }
}

?>
<!DOCTYPE html>
<html>
<head>
  <style type='text/css'>
    body{
      max-width: 800px; 
      margin: auto;
      
    }
    table{
      width: 100%;
    }
    table .value{
      max-width: 300px;
      overflow: hidden;
    }
    table td{
      padding: 3px;
      background-color: #CCC;
    }
    #key{
      width: 100%;
      height: 200px;
    }
    .error{
        width: 100%;
        height: 50px;
        background-color: salmon;
        padding: 10px;
    }

  </style> 
</head>
<body>

<?php if ($error != ''){
  echo "<div class='error'>$error</div>";
}?>

<h2> Existing Keys </h2>
<table>
  <thead>
    <tr>
      <th>Type</th>
      <th>Key</th>
      <th>Owner</th>
    </tr> 
  </thead>
  <tbody>
<?php foreach ($authorized_keys as $key)
{
  echo "<tr> <td class='type'>".$key['type']."</td> <td class='value'>".$key['value']."</td> <td class='owner'>".$key['owner']."</td> </tr>";
}?>
  </tbody>
</table>

<h2> Add A Key </h2>

<p> To connect to git via ssh, you'll need to generate a private key. </p>

<form method="POST">
  <textarea id='key' name='key' placeholder="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC8/QDeDKfx+YNq8xIndzFnicnCi69IrgXckZbwbzmnfopVxYJsFG8cvQws+iyLb9Y/vv3PIQLt300BiX3DD488L8A9wr4mYzGsphWcuXIURN82uTw19iKL3W843WElbn9FOU9vuOSkljaCzzA1BxNAaOkE5S0Y3HIBnxFNUWpS22Yx1kJQNcF54ZOittGglzWmVDm8n77CpfaOcAvI1EJZnUkAYpVxwuuTdCzl415622rMS7pLP+Q7NpRwKBdE66cSgxCa+JUP+s3whpxLdK4PeRf/bXGAqZN6LUQy/rhboDeZejCjsxoaYQDPz625tTvs8RVfXjmohezJoNkalHqj classam@waterfall"></textarea>
  <input type='submit' value="Add Key"></input>
  
</form>

</body>
</html>

