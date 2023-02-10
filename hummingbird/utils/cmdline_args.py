import argparse
import logging
import sys

argparser = argparse.ArgumentParser(description='Hummingbird - '
                                    'Monitoring and Analysing FXI experiments.')
_group = argparser.add_mutually_exclusive_group()
_group.add_argument("-i", "--interface",
                    help="start the control and display interface",
                    action="store_true")
_group.add_argument('-b', '--backend', metavar='conf.py',
                    type=str, help="start the backend with "
                    "given configuration file", nargs='?', const=True)
_group.add_argument('-r', '--reload', help='reloads the backend',
                    action='store_true')
argparser.add_argument('-m', '--batch-mode', help='running only backend without any interactive front end',
                       action='store_true')
argparser.add_argument("-p", "--port",
                       type=int, default=13131, help="overwrites the port, defaults to 13131")
argparser.add_argument("-I", "--influxdb", const="influxdb://localhost/hummingbird",
                        type=str, help="spool all scalar data to the specified InfluxDB instance", nargs = "?")
argparser.add_argument("-v", "--verbose", help="increase output verbosity",
                       action="store_true")
argparser.add_argument("-d", "--debug", help="output debug messages",
                       action="store_true")
argparser.add_argument("--profile", help="generate and output profiling information for the backend",
                       action="store_true")
argparser.add_argument("--no-restore", help="no restoring of Qsettings",
                       action="store_false")

# Add LCLS-specific arguments to argparser
try:
    from hummingbird.backend.lcls import add_cmdline_args
    add_cmdline_args()
except ImportError:
    pass

# Add euxfel-specific arguments to argparser
try:
    from hummingbird.backend.euxfel import add_cmdline_args
    add_cmdline_args()
    from hummingbird.backend.euxfel_trains import add_cmdline_args
    add_cmdline_args()
except ImportError:
    pass

_config_argument_group = None
_config_file_arguments_added = []
def add_config_file_argument(*args, **kwargs):
    global _config_argument_group
    if _config_argument_group is None:
        _config_argument_group = argparser.add_argument_group('Configuration file', 'Configuration file specific options')
    # Avoid that arguments get added twice when reloading the configuration file
    added = any([(args == args_added) and all(set(kwargs.items()) & set(kwargs_added.items())) for args_added,kwargs_added in _config_file_arguments_added])
    if not added:
        _config_argument_group.add_argument(*args, **kwargs)
        _config_file_arguments_added.append((args, kwargs))
