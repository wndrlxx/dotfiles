# frozen_string_literal: true

require_relative '../test_helper'

describe 'Ruby runtime' do
  it 'uses a modern Ruby instead of the macOS system Ruby' do
    _(Gem::Version.new(RUBY_VERSION)).must_be :>=, Gem::Version.new('3.4')
    _(RbConfig.ruby).wont_equal '/usr/bin/ruby'
  end

  it 'resolves test paths independently of the working directory' do
    _(File.directory?(SketchybarTest::PLUGIN_DIR)).must_equal true
    _(File.file?(SketchybarTest::RUBY_LAUNCHER)).must_equal true
  end
end
