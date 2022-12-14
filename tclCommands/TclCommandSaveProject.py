from collections import OrderedDict

from tclCommands.TclCommand import TclCommandSignaled


class TclCommandSaveProject(TclCommandSignaled):
    """
    Tcl shell command to save the FlatCAM project to file.
    """

    # array of all command aliases, to be able use  old names for backward compatibility (add_poly, add_polygon)
    aliases = ['save_project']

    # Dictionary of types from Tcl command, needs to be ordered.
    # For positional arguments
    arg_names = OrderedDict([
        ('filename', str)
    ])

    # Dictionary of types from Tcl command, needs to be ordered.
    # For options like -optionname value
    option_types = OrderedDict()

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['filename']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Saves the FlatCAM project to file.",
        'args': OrderedDict([
            ('filename', 'Path to file.'),
        ]),
        'examples': []
    }

    def execute(self, args, unnamed_args):
        """
        execute current TCL shell command

        :param args: array of known named arguments and options
        :param unnamed_args: array of other values which were passed into command
            without -somename and  we do not have them in known arg_names
        :return: None or exception
        """

        self.app.save_project(args['filename'])
