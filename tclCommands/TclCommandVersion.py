from collections import OrderedDict

from tclCommands.TclCommand import TclCommand


class TclCommandVersion(TclCommand):
    """
    Tcl shell command to check the program version.

    example:

    """

    # List of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['version']

    # Dictionary of types from Tcl command, needs to be ordered
    arg_names = OrderedDict()

    # Dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = OrderedDict()

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = []

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Checks the program version.",
        'args': OrderedDict(),
        'examples': []
    }

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """

        self.app.version_check()

