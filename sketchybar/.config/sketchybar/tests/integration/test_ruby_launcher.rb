# frozen_string_literal: true

require_relative '../test_helper'

describe 'Ruby launcher' do
  it 'launches in a service environment and preserves arguments and exit status' do
    Dir.mktmpdir('sketchybar ruby ') do |directory|
      script = File.join(directory, 'fixture plugin.rb')
      File.write(script, <<~RUBY)
        require 'rbconfig'
        puts File.realpath(RbConfig.ruby)
        puts ENV.fetch('CONFIG_DIR')
        puts ARGV
        exit 23
      RUBY
      output, error, status = Open3.capture3(
        { 'PATH' => '/usr/bin:/bin:/usr/sbin:/sbin', 'HOME' => ENV.fetch('HOME'),
          'MISE_CACHE_DIR' => File.join(directory, 'mise-cache'),
          'CONFIG_DIR' => SketchybarTest::CONFIG_DIR },
        '/bin/sh', SketchybarTest::RUBY_LAUNCHER, script,
        'argument with spaces', '$(must stay literal)',
        unsetenv_others: true, chdir: directory
      )

      _(status.exitstatus).must_equal 23
      _(error).must_be_empty
      _(output.lines.map(&:chomp)).must_equal [
        File.realpath(RbConfig.ruby), SketchybarTest::CONFIG_DIR,
        'argument with spaces', '$(must stay literal)'
      ]
    end
  end

  it 'resolves mise from HOME and propagates resolution failures without fallback' do
    Dir.mktmpdir('mise home ') do |home|
      bin = File.join(home, '.local', 'bin')
      FileUtils.mkdir_p(bin)
      mise = File.join(bin, 'mise')
      File.write(mise, <<~SH)
        #!/bin/sh
        [ "$1" = '-C' ] && [ "$2" = "$HOME" ] &&
          [ "$3" = 'which' ] && [ "$4" = 'ruby' ] || exit 42
        printf '%s\\n' "$TEST_RUBY"
      SH
      File.chmod(0o700, mise)
      output, error, status = Open3.capture3(
        { 'HOME' => home, 'PATH' => '/usr/bin:/bin', 'TEST_RUBY' => RbConfig.ruby },
        '/bin/sh', SketchybarTest::RUBY_LAUNCHER, '-e', 'puts RUBY_VERSION',
        unsetenv_others: true, chdir: '/'
      )
      _(status.success?).must_equal true, error
      _(output).must_equal "#{RUBY_VERSION}\n"

      File.write(mise, "#!/bin/sh\nexit 19\n")
      output, _error, status = Open3.capture3(
        { 'HOME' => home, 'PATH' => '/usr/bin:/bin' },
        '/bin/sh', SketchybarTest::RUBY_LAUNCHER, '-e', 'puts RUBY_VERSION',
        unsetenv_others: true
      )
      _(status.exitstatus).must_equal 19
      _(output).must_be_empty
    end
  end
end
