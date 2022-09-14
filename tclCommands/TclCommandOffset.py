from collections import OrderedDict

from tclCommands.TclCommand import TclCommand


class TclCommandOffset(TclCommand):
    """
    Tcl shell command to change the position of the object.

    example:
        offset my_geometry 1.2 -0.3
    """

    # List of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['offset']

    # Dictionary of types from Tcl command, needs to be ordered
    arg_names = OrderedDict([
        ('name', str),
        ('x', float),
        ('y', float)
    ])

    # Dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = OrderedDict()

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name', 'x', 'y']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Changes the position of the object.",
        'args': OrderedDict([
            ('name', 'Name of the object to offset.'),
            ('x', 'Offset distance in the X axis.'),
            ('y', 'Offset distance in the Y axis')
        ]),
        'examples': ['offset my_geometry 1.2 -0.3']
    }

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """

        name = args['name']
        x, y = args['x'], args['y']

        self.app.collection.get_by_name(name).offset((x, y))
