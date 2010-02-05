function firm()
{
	if(confirm("You can only join one group. If you choose to join this group, you will be kicked out of your current group")) {
		return true;
	}
	else {
		return false;
	}
}