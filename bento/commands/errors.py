from optparse \
    import \
        OptionError

class UsageException(Exception):
    pass

class ConvertionError(Exception):
    pass

class CommandExecutionFailure(Exception):
    pass
