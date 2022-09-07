import pkgutil

__all__ = []

def register_all_commands(app, commands):
    """
    Static method which register all known commands.

    All files within this directory will be scanned and commands found will be loaded.

    :param app: FlatCAMApp
    :param commands: array of commands  which should be modified
    :return: None
    """

    tcl_modules = {}
    for loader, name, is_pkg in pkgutil.walk_packages(__path__):
        tcl_modules[name] = loader.find_module(name).load_module(name)

    for key, mod in tcl_modules.items():
        class_type = getattr(mod, key)
        command_instance = class_type(app)

        for alias in command_instance.aliases:
            commands[alias] = {
                'fcn': command_instance.execute_wrapper,
                'help': command_instance.get_decorated_help()
            }
