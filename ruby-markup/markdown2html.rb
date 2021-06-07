#!/usr/bin/ruby

require 'github/markup'

data = STDIN.read
# allowing UNSAFE here, because we sanitize with bleach in Python
html = GitHub::Markup.render_s(GitHub::Markups::MARKUP_MARKDOWN, data, options: {commonmarker_opts: [:UNSAFE]})
puts(html)
