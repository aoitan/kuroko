from click.testing import CliRunner
from kanpe.cli import main

def test_kanpe_subcommands_exist():
    runner = CliRunner()
    result = runner.invoke(main, ['--help'])
    assert result.exit_code == 0
    assert 'report' in result.output
    assert 'view' in result.output
