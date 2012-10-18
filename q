diff --git a/onlineforms/views.py b/onlineforms/views.py
index 71c0f64..a1d5a8a 100644
--- a/onlineforms/views.py
+++ b/onlineforms/views.py
@@ -48,6 +48,8 @@ def new_group(request):
 
 
 def manage_group(request, formgroup_slug):
+    # print "in manage group"
+    # editting existing form...
     pass
 
 
diff --git a/templates/onlineforms/manage_groups.html b/templates/onlineforms/manage_groups.html
index 63d513c..4b7f57a 100644
--- a/templates/onlineforms/manage_groups.html
+++ b/templates/onlineforms/manage_groups.html
@@ -7,7 +7,39 @@
 {% block subbreadcrumbs %}{% endblock %}
 
 {% block content %}
-{% for g in groups %}
-	{{ g.name }}
-{% endfor %}
-{% endblock %}
\ No newline at end of file
+<div class="datatable_container">
+    <table class="display" id="groups">
+        <thead>
+            <tr>
+				<th scope="col">Faculty</th>
+                <th scope="col">Name of Group</th>
+                <th scope="col">Tag Name</th>
+                <th scope="col">Edit Group</th>
+                <th scope="col">Delete</th>
+			</tr>
+		</thead>
+		<tbody>
+		{% for grp in groups %}
+			<tr>
+				<td>{{grp.unit}}</td>
+				<td>{{grp.name}}</td>
+				<td>{{grp.slug}}</td>
+				<td class="miniaction">
+					<form action="{% url onlineforms.views.manage_group formgroup_slug=grp.slug %}">{% csrf_token %}
+						<input type="hidden" name="group_id" value="{{grp.id}}" />
+						<input type="submit" value="Edit">
+					</form>
+				<td class="miniaction"> 
+                    <form action="" method="post">{% csrf_token %}
+                        <input type="hidden" name="group_id" value="{{grp.id}}"/>
+                        <input type="hidden" name="action" value="delete"/>
+                        <input type="submit" value="Remove"/>
+				    </form>
+                </td>
+			</tr>
+		{% endfor %}
+		</tbody>
+    </table>
+</div>
+
+{% endblock %}
