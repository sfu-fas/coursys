#!/usr/bin/ruby

require 'github/markup'

data = STDIN.read
html = GitHub::Markup.render_s(GitHub::Markups::MARKUP_MARKDOWN, data)
puts(html)
