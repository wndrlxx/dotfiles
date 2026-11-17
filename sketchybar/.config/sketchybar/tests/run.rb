# frozen_string_literal: true

# Keep Ruby discovery separate from Python's test_*.py discovery.
suite = ARGV.shift || 'all'
unless %w[all unit integration].include?(suite)
  warn 'Usage: ruby tests/run.rb [all|unit|integration] [minitest options]'
  exit 1
end

directories = suite == 'all' ? %w[unit integration] : [suite]
directories.each do |directory|
  Dir[File.join(__dir__, directory, 'test_*.rb')].sort.each { |path| require path }
end
