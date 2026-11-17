# frozen_string_literal: true

require 'minitest/autorun'
require 'minitest/spec'
require 'open3'
require 'tmpdir'
require 'rbconfig'

module SketchybarTest
  CONFIG_DIR = File.expand_path('..', __dir__).freeze
  PLUGIN_DIR = File.join(CONFIG_DIR, 'plugins').freeze
  RUBY_LAUNCHER = File.join(PLUGIN_DIR, 'ruby.sh').freeze
end
