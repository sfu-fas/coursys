#!/usr/bin/ruby

require 'github/markup'

data = STDIN.read
file = 'foo.md'
html = GitHub::Markup.render_s(GitHub::Markups::MARKUP_MARKDOWN, data, options: {:unsafe => true})
puts(html)


