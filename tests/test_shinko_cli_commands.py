from click.testing import CliRunner
from shinko.cli import main

def test_shinko_subcommands_exist():
    runner = CliRunner()
    result = runner.invoke(main, ['--help'])
    assert result.exit_code == 0
    assert 'recent' in result.output
    assert 'blockers' in result.output
    assert 'status' in result.output
    assert 'worklist' in result.output
    assert 'insight' in result.output
