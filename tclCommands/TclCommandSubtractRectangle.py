from collections import OrderedDict

from tclCommands.TclCommand import TclCommandSignaled


class TclCommandSubtractRectangle(TclCommandSignaled):
    """
    Tcl shell command to subtract a rectange from the given Geometry object.
    """

    # array of all command aliases, to be able use  old names for backward compatibility (add_poly, add_polygon)
    aliases = ['subtract_rectangle']

    # Dictionary of types from Tcl command, needs to be ordered.
    # For positional arguments
    arg_names = OrderedDict([
        ('name', str),
        ('x0', float),
        ('y0', float),
        ('x1', float),
        ('y1', float)
    ])

    # Dictionary of types from Tcl command, needs to be ordered.
    # For options like -optionname value
    option_types = OrderedDict()

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name', 'x0', 'y0', 'x1', 'y1']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Subtract rectange from the given Geometry object.",
        'args': OrderedDict([
            ('name', 'Name of the Geometry object from which to subtract.'),
            ('x0 y0', 'Bottom left corner coordinates.'),
            ('x1 y1', 'Top right corner coordinates.')
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

        obj_name = args['name']
        x0 = args['x0']
        y0 = args['y0']
        x1 = args['x1']
        y1 = args['y1']

        try:
            obj = self.app.collection.get_by_name(str(obj_name))
        except:
            return "Could not retrieve object: %s" % obj_name
        if obj is None:
            return "Object not found: %s" % obj_name

        obj.subtract_polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
