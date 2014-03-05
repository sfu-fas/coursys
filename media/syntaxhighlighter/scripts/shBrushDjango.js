/**
 * SyntaxHighlighter
 * http://alexgorbatchev.com/SyntaxHighlighter
 *
 * SyntaxHighlighter is donationware. If you are using it, please donate.
 * http://alexgorbatchev.com/SyntaxHighlighter/donate.html
 *
 * @version
 * 3.0.83 (July 02 2010)
 * 
 * @copyright
 * Copyright (C) 2004-2010 Alex Gorbatchev.
 *
 * @license
 * Dual licensed under the MIT and GPL licenses.
 */
;(function()
{
	// CommonJS
	typeof(require) != 'undefined' ? SyntaxHighlighter = require('shCore').SyntaxHighlighter : null;

	function Brush() {
	    function process_htmltag(match, regexInfo){
			var constructor = SyntaxHighlighter.Match;
			var code = match[0];
			var tag = new XRegExp('(&lt;|<)[\\s\\/\\?]*(?<name>[:\\w-\\.]+)', 'xg').exec(code);
			var result = [];

			if (match.attributes != null) {
				var attributes;
				var regex = new XRegExp('(?<name> [\\w:\\-\\.]+)' +
										'\\s*=\\s*' +
										'(?<value> ".*?"|\'.*?\'|\\w+)',
										'xg');

				while ((attributes = regex.exec(code)) != null) {
					result.push(new constructor(attributes.name, match.index + attributes.index, 'color1'));
					result.push(new constructor(attributes.value, match.index + attributes.index + attributes[0].indexOf(attributes.value), 'string'));
				}
			}

			if (tag != null)
				result.push(
					new constructor(tag.name, match.index + tag[0].indexOf(tag.name), 'keyword')
				);

			return result;
		}

		function process_djangotag(match, regexInfo) {
			var constructor = SyntaxHighlighter.Match;
			var keywords = /^block$|^comment$|^extends$|^filter$|^for$|^if$|^ifchanged$|^ifequal$|^ifnotequal$|^end.*$|^load$/g;
			var operators = /^and$|^or$|^not$|^in$|^as$|^by$/g;
			var i = 0;
			var result = [];
			XRegExp.iterate(match[2], /(\S+)/g, function(innermatch){
			    if (++i == 1) {
                    result.push(new constructor(innermatch[1], match.index + match[0].indexOf(innermatch[1]), 'keyword'));
			    } else if (innermatch[0].match(operators) != null){
                    result.push(new constructor(innermatch[1], match.index + match[0].indexOf(innermatch[1]), 'keyword'));
			    } else if (innermatch[0].match(/['"].*["']/g) != null){
                    result.push(new constructor(innermatch[1], match.index + match[0].indexOf(innermatch[1]), 'string'));
			    } else {
			        result.push(new constructor(innermatch[1], match.index + match[0].indexOf(innermatch[1]), 'variable'));
			    }
			});
			return result;
		}
		this.regexList = [
            { regex: new XRegExp('(\\{%)\\s*(.+?)\\s*(%\\})', 'g'), func: process_djangotag },
            { regex: /\{\{.+\}\}/g, css: 'variable'},
		    { regex: /\{#.+#\}/g, css: 'comments'},
			{ regex: new XRegExp('(\\&lt;|<)\\!\\[[\\w\\s]*?\\[(.|\\s)*?\\]\\](\\&gt;|>)', 'gm'),			css: 'color2' },	// <![ ... [ ... ]]>
			{ regex: SyntaxHighlighter.regexLib.xmlComments,												css: 'comments' },	// <!-- ... -->
			{ regex: new XRegExp('(&lt;|<)[\\s\\/\\?]*(\\w+)(?<attributes>.*?)[\\s\\/\\?]*(&gt;|>)', 'sg'), func: process_htmltag }
		];

	};

	Brush.prototype	= new SyntaxHighlighter.Highlighter();
	Brush.aliases	= ['django', 'dj'];

	SyntaxHighlighter.brushes.Django = Brush;
	// CommonJS
	typeof(exports) != 'undefined' ? exports.Brush = Brush : null;
})();