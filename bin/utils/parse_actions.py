import argparse


def flag_as_value(value):
    class FlagAsInt(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            setattr(namespace, self.dest, value)
    return FlagAsInt


def multi_set(dest1, value1):
    class MultiSet(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            setattr(namespace, dest1, value1)
            setattr(namespace, self.dest, values)
    return MultiSet