'Visualize' is a JQuery plugin which generate accessible charts and graphs from table elements using HTML 5 canvas

reference: http://www.filamentgroup.com/lab/jquery_visualize_plugin_accessible_charts_graphs_from_tables_html5_canvas/


Note for Internet Explorer support: (copied from the reference link above)
This plugin uses the HTML 5 canvas element, which is not supported in an version of Internet Explorer at this time. 
Fortunately, Google maintains a library that translates canvas scripting into VML, allowing it to work in all versions
 of internet explorer. The script is included in the zip. To use it, just be sure to include the script in your page 
using a conditional comment, like this:
<!--[if IE]><script type="text/javascript" src="excanvas.compiled.js"></script><![endif]-->
