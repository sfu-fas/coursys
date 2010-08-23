// JavaScript Document

function pickRandom(range) {  // returns an integer value from 0 to (#-1)
if (range==0) return 0;
if (Math.random)
	return Math.round(Math.random() * (range-1));
else {
	var now = new Date();
	return (now.getTime() / 1000) % range;
	}
}
