# adapted from the RPC server at https://www.rabbitmq.com/tutorials/tutorial-six-ruby.html
require 'bunny'
require 'github/markup'
require 'json'

class MarkdownServer
  def initialize
    @connection = Bunny.new(:host => "rabbitmq", :vhost => "myvhost", :user => "coursys", :password => "supersecretpassword")
    @connection.start
    @channel = @connection.create_channel
  end

  def start(queue_name)
    @queue = channel.queue(queue_name)
    @exchange = channel.default_exchange
    subscribe_to_queue
  end

  def stop
    channel.close
    connection.close
  end

  def loop_forever
    # This loop only exists to keep the main thread
    # alive. Many real world apps won't need this.
    loop { sleep 5 }
  end

  private

  attr_reader :channel, :exchange, :queue, :connection

  def subscribe_to_queue
    queue.subscribe do |_delivery_info, properties, data|
      puts Time.now.strftime("%Y-%m-%d %H:%M:%S") + ' Received request'
      arg = JSON.parse(data.encode('utf-8'))
      md = arg['md']
      result = GitHub::Markup.render_s(GitHub::Markups::MARKUP_MARKDOWN, md)
      exchange.publish(
        JSON.generate({:html => result}).encode('utf-8'),
        routing_key: properties.reply_to,
        correlation_id: properties.correlation_id
      )
    end
  end
end

begin
  server = MarkdownServer.new

  puts Time.now.strftime("%Y-%m-%d %H:%M:%S") + ' Awaiting RPC requests'
  server.start('markdown2html_queue')
  server.loop_forever
rescue Interrupt => _
  server.stop
end