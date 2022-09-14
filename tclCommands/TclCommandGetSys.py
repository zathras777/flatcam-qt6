from collections import OrderedDict

from tclCommands.TclCommand import TclCommand


class TclCommandGetSys(TclCommand):
    """
    Tcl shell command to get the value of a system variable

    example:
        get_sys excellon_zeros
    """

    # List of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['get_sys', 'getsys']

    # Dictionary of types from Tcl command, needs to be ordered
    arg_names = OrderedDict([
        ('name', str)
    ])

    # Dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = OrderedDict([

    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Returns the value of the system variable.",
        'args': OrderedDict([
            ('name', 'Name of the system variable.'),
        ]),
        'examples': ['get_sys excellon_zeros']
    }

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """

        name = args['name']

        if name in self.app.defaults:
            return self.app.defaults[name]

