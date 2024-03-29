"""
Argparse was written by Steven Bethard <steven.bethard@gmail.com>.

Copyright (c) 2006 Steven J. Bethard.  All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

  * Redistributions of source code must retain the above copyright
    notice, this list of conditions and the following disclaimer.

  * Redistributions in binary form must reproduce the above copyright
    notice, this list of conditions and the following disclaimer in the
    documentation and/or other materials provided with the distribution.
    
  * Neither the name of the author nor the names of its
    contributors may be used to endorse or promote products derived from
    this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS
IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE AUTHOR OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import os as _os
import re as _re
import sys as _sys
import textwrap as _textwrap

from gettext import gettext as _

SUPPRESS = '==SUPPRESS=='

OPTIONAL = '?'
ZERO_OR_MORE = '*'
ONE_OR_MORE = '+'
PARSER = '==PARSER=='

# =============================
# Utility functions and classes
# =============================

class _AttributeHolder(object):
    """Abstract base class that provides __repr__.

    The __repr__ method returns a string in the format:
        ClassName(attr=name, attr=name, ...)
    The attributes are determined either by a class-level attribute,
    '_kwarg_names', or by inspecting the instance __dict__.
    """
    
    def __repr__(self):
        type_name = type(self).__name__
        arg_strings = []
        for arg in self._get_args():
            arg_strings.append(repr(arg))
        for name, value in self._get_kwargs():
            arg_strings.append('%s=%r' % (name, value))
        return '%s(%s)' % (type_name, ', '.join(arg_strings))

    def _get_kwargs(self):
        return sorted(self.__dict__.items())

    def _get_args(self):
        return []

def _ensure_value(namespace, name, value):
    if getattr(namespace, name, None) is None:
        setattr(namespace, name, value)
    return getattr(namespace, name)
    


# ===============
# Formatting Help
# ===============

class HelpFormatter(object):

    def __init__(self,
                 prog,
                 indent_increment=2,
                 max_help_position=24,
                 width=None):

        # default setting for width
        if width is None:
            try:
                width = int(_os.environ['COLUMNS'])
            except (KeyError, ValueError):
                width = 80
            width -= 2
        
        self._prog = prog
        self._indent_increment = indent_increment
        self._max_help_position = max_help_position
        self._width = width

        self._current_indent = 0
        self._level = 0
        self._action_max_length = 0

        self._root_section = self._Section(self, None)
        self._current_section = self._root_section

        self._long_break_matcher = _re.compile(r'\n\n\n+')

    # ===============================
    # Section and indentation methods
    # ===============================

    def _indent(self):
        self._current_indent += self._indent_increment
        self._level += 1

    def _dedent(self):
        self._current_indent -= self._indent_increment
        assert self._current_indent >= 0, 'Indent decreased below 0.'
        self._level -= 1

    class _Section(object):
        def __init__(self, formatter, parent, heading=None):
            self.formatter = formatter
            self.parent = parent
            self.heading = heading
            self.items = []

        def format_help(self):
            # format the indented section
            if self.parent is not None:
                self.formatter._indent()
            join = self.formatter._join_parts
            for func, args in self.items:
                func(*args)
            item_help = join(func(*args) for func, args in self.items)
            if self.parent is not None:
                self.formatter._dedent()

            # return nothing if the section was empty            
            if not item_help:
                return ''

            # add the heading if the section was non-empty
            if self.heading is not SUPPRESS and self.heading is not None:
                current_indent = self.formatter._current_indent
                heading = '%*s%s:\n' % (current_indent, '', self.heading)
            else:
                heading = ''

            # join the section-initial newline, the heading and the help
            return join(['\n', heading, item_help, '\n'])

    def _add_item(self, func, args):
        self._current_section.items.append((func, args))

    # ========================
    # Message building methods
    # ========================

    def start_section(self, heading):
        self._indent()
        section = self._Section(self, self._current_section, heading)
        self._add_item(section.format_help, [])
        self._current_section = section

    def end_section(self):
        self._current_section = self._current_section.parent
        self._dedent()

    def add_text(self, text):
        if text is not SUPPRESS and text is not None:
            self._add_item(self._format_text, [text])

    def add_usage(self, usage, optionals, positionals, prefix=None):
        if usage is not SUPPRESS:
            args = usage, optionals, positionals, prefix
            self._add_item(self._format_usage, args)

    def add_argument(self, action):
        if action.help is not SUPPRESS:
            
            # update the maximum item length
            invocation = self._format_action_invocation(action)
            action_length = len(invocation) + self._current_indent
            self._action_max_length = max(self._action_max_length,
                                          action_length)

            # add the item to the list        
            self._add_item(self._format_action, [action])

    def add_arguments(self, actions):
        for action in actions:
            self.add_argument(action)

    # =======================
    # Help-formatting methods
    # =======================

    def format_help(self):
        help = self._root_section.format_help() % dict(prog=self._prog)
        if help:
            help = self._long_break_matcher.sub('\n\n', help)
            help = help.strip('\n') + '\n'
        return help

    def _join_parts(self, part_strings):
        return ''.join(part
                       for part in part_strings
                       if part and part is not SUPPRESS)

    def _format_usage(self, usage, optionals, positionals, prefix):
        if prefix is None:
            prefix = _('usage: ')

        # if no optionals or positionals are available, usage is just prog
        if usage is None and not optionals and not positionals:
            usage = '%(prog)s'
            
        # if optionals and positionals are available, calculate usage
        elif usage is None:
            usage = '%(prog)s' % dict(prog=self._prog)
                
            # determine width of "usage: PROG" and width of text
            prefix_width = len(prefix) + len(usage) + 1
            prefix_indent = self._current_indent + prefix_width
            text_width = self._width - self._current_indent

            # put them on one line if they're short enough
            format = self._format_actions_usage
            action_usage = format(optionals + positionals)
            if prefix_width + len(action_usage) + 1 < text_width:
                usage = '%s %s' % (usage, action_usage)
            
            # if they're long, wrap optionals and positionals individually
            else:
                optional_usage = format(optionals)
                positional_usage = format(positionals)
                indent = ' ' * prefix_indent

                # usage is made of PROG, optionals and positionals
                parts = [usage, ' ']
                
                # options always get added right after PROG
                if optional_usage:
                    parts.append(_textwrap.fill(
                        optional_usage, text_width,
                        initial_indent=indent,
                        subsequent_indent=indent).lstrip())

                # if there were options, put arguments on the next line
                # otherwise, start them right after PROG
                if positional_usage:
                    part = _textwrap.fill(
                        positional_usage, text_width,
                        initial_indent=indent,
                        subsequent_indent=indent).lstrip()
                    if optional_usage:
                        part = '\n' + indent + part
                    parts.append(part)
                usage = ''.join(parts)

        # prefix with 'usage:'
        return '%s%s\n\n' % (prefix, usage)

    def _format_actions_usage(self, actions):
        parts = []
        for action in actions:
            if action.help is SUPPRESS:
                continue

            # produce all arg strings        
            if not action.option_strings:
                parts.append(self._format_args(action, action.dest))

            # produce the first way to invoke the option in brackets
            else:
                option_string = action.option_strings[0]

                # if the Optional doesn't take a value, format is:
                #    -s or --long
                if action.nargs == 0:
                    parts.append('[%s]' % option_string)

                # if the Optional takes a value, format is:
                #    -s ARGS or --long ARGS
                else:
                    default = action.dest.upper()
                    args_string = self._format_args(action, default)
                    parts.append('[%s %s]' % (option_string, args_string))

        return ' '.join(parts)


    def _format_text(self, text):
        text_width = self._width - self._current_indent
        indent = ' ' * self._current_indent
        return _textwrap.fill(text, text_width,
                              initial_indent=indent,
                              subsequent_indent=indent) + '\n\n'

    def _format_action(self, action):
        # determine the required width and the entry label
        help_position = min(self._action_max_length + 2,
                            self._max_help_position)
        help_width = self._width - help_position
        action_width = help_position - self._current_indent - 2
        action_header = self._format_action_invocation(action)

        # ho nelp; start on same line and add a final newline
        if not action.help:
            tup = self._current_indent, '', action_header
            action_header = '%*s%s\n' % tup
            
        # short action name; start on the same line and pad two spaces
        elif len(action_header) <= action_width:
            tup = self._current_indent, '', action_width, action_header
            action_header = '%*s%-*s  ' % tup
            indent_first = 0

        # long action name; start on the next line
        else:
            tup = self._current_indent, '', action_header
            action_header = '%*s%s\n' % tup
            indent_first = help_position

        # collect the pieces of the action help
        parts = [action_header]

        # if there was help for the action, add lines of help text
        if action.help:
            help_text = self._expand_help(action)
            help_lines = _textwrap.wrap(help_text, help_width)
            parts.append('%*s%s\n' % (indent_first, '', help_lines[0]))
            for line in help_lines[1:]:
                parts.append('%*s%s\n' % (help_position, '', line))

        # or add a newline if the description doesn't end with one
        elif not action_header.endswith('\n'):
            parts.append('\n')

        # return a single string            
        return self._join_parts(parts)

    def _format_action_invocation(self, action):
        if not action.option_strings:
            return self._format_metavar(action, action.dest)

        else:
            parts = []

            # if the Optional doesn't take a value, format is:
            #    -s, --long
            if action.nargs == 0:
                parts.extend(action.option_strings)

            # if the Optional takes a value, format is:
            #    -s ARGS, --long ARGS
            else:
                default = action.dest.upper()
                args_string = self._format_args(action, default)
                for option_string in action.option_strings:
                    parts.append('%s %s' % (option_string, args_string))

            return ', '.join(parts)

    def _format_metavar(self, action, default_metavar):
        if action.metavar is not None:
            name = action.metavar
        elif action.choices is not None:
            choice_strs = (str(choice) for choice in action.choices)
            name = '{%s}' % ','.join(choice_strs)
        else:
            name = default_metavar
        return name

    def _format_args(self, action, default_metavar):
        name = self._format_metavar(action, default_metavar)
        if action.nargs is None:
            result = name
        elif action.nargs == OPTIONAL:
            result = '[%s]' % name
        elif action.nargs == ZERO_OR_MORE:
            result = '[%s [%s ...]]' % (name, name)
        elif action.nargs == ONE_OR_MORE:
            result = '%s [%s ...]' % (name, name)
        elif action.nargs is PARSER:
            result = '%s ...' % name
        else:
            result = ' '.join([name] * action.nargs)
        return result

    def _expand_help(self, action):
        params = dict(vars(action), prog=self._prog)
        for name, value in params.items():
            if value is SUPPRESS:
                del params[name]
        if params.get('choices') is not None:
            choices_str = ', '.join(str(c) for c in params['choices'])
            params['choices'] = choices_str
        return action.help % params


# =====================
# Options and Arguments
# =====================

class ArgumentError(Exception):
    """ArgumentError(message, argument)

    Raised whenever there was an error creating or using an argument
    (optional or positional).

    The string value of this exception is the message, augmented with
    information about the argument that caused it.
    """
    
    def __init__(self, argument, message):
        if argument.option_strings:
            self.argument_name =  '/'.join(argument.option_strings)
        elif argument.metavar not in (None, SUPPRESS):
            self.argument_name = argument.metavar
        elif argument.dest not in (None, SUPPRESS):
            self.argument_name = argument.dest
        else:
            self.argument_name = None
        self.message = message

    def __str__(self):
        if self.argument_name is None:
            format = '%(message)s'
        else:
            format = 'argument %(argument_name)s: %(message)s'
        return format % dict(message=self.message,
                             argument_name=self.argument_name)

# ==============
# Action classes
# ==============

class Action(_AttributeHolder):
    """Action(*strings, **options)

    Action objects hold the information necessary to convert a
    set of command-line arguments (possibly including an initial option
    string) into the desired Python object(s).

    Keyword Arguments:

    option_strings -- A list of command-line option strings which
        should be associated with this action.
    
    dest -- The name of the attribute to hold the created object(s)
    
    nargs -- The number of command-line arguments that should be consumed.
        By default, one argument will be consumed and a single value will
        be produced.  Other values include:
            * N (an integer) consumes N arguments (and produces a list)
            * '?' consumes zero or one arguments
            * '*' consumes zero or more arguments (and produces a list)
            * '+' consumes one or more arguments (and produces a list)
        Note that the difference between the default and nargs=1 is that
        with the default, a single value will be produced, while with
        nargs=1, a list containing a single value will be produced.

    const -- The value to be produced if the option is specified and the
        option uses an action that takes no values.

    default -- The value to be produced if the option is not specified.

    type -- The type which the command-line arguments should be converted
        to, should be one of 'string', 'int', 'float', 'complex' or a
        callable object that accepts a single string argument. If None,
        'string' is assumed.
        
    choices -- A container of values that should be allowed. If not None,
        after a command-line argument has been converted to the appropriate
        type, an exception will be raised if it is not a member of this
        collection.

    help -- The help string describing the argument.

    metavar -- The name to be used for the option's argument with the help
        string. If None, the 'dest' value will be used as the name.
    """


    def __init__(self,
                 option_strings,
                 dest,
                 nargs=None,
                 const=None,
                 default=None,
                 type=None,
                 choices=None,
                 help=None,
                 metavar=None):
        self.option_strings = option_strings
        self.dest = dest
        self.nargs = nargs
        self.const = const
        self.default = default
        self.type = type
        self.choices = choices
        self.help = help
        self.metavar = metavar

    def _get_kwargs(self):
        names = [
            'option_strings',
            'dest',
            'nargs',
            'const',
            'default',
            'type',
            'choices',
            'help',
            'metavar'
        ]
        return [(name, getattr(self, name)) for name in names]

    def __call__(self, parser, namespace, values, option_string=None):
        raise NotImplementedError(_('.__call__() not defined'))

class StoreAction(Action):
    def __init__(self,
                 option_strings,
                 dest,
                 nargs=None,
                 const=None,
                 default=None,
                 type=None,
                 choices=None,
                 help=None,
                 metavar=None):
        if nargs == 0:
            raise ValueError('nargs must be > 0')
        if const is not None and nargs != OPTIONAL:
            raise ValueError('nargs must be %r to supply const' % OPTIONAL)
        super(StoreAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=nargs,
            const=const,
            default=default,
            type=type,
            choices=choices,
            help=help,
            metavar=metavar)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)

class StoreConstAction(Action):
    def __init__(self,
                 option_strings,
                 dest,
                 const,
                 default=None,
                 help=None,
                 metavar=None):
        super(StoreConstAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=0,
            const=const,
            default=default,
            help=help)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, self.const)

class StoreTrueAction(StoreConstAction):
    def __init__(self,
                 option_strings,
                 dest,
                 default=False,
                 help=None):
        super(StoreTrueAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            const=True,
            default=default,
            help=help)

class StoreFalseAction(StoreConstAction):
    def __init__(self,
                 option_strings,
                 dest,
                 default=True,
                 help=None):
        super(StoreFalseAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            const=False,
            default=default,
            help=help)
    
class AppendAction(Action):
    def __init__(self,
                 option_strings,
                 dest,
                 nargs=None,
                 const=None,
                 default=None,
                 type=None,
                 choices=None,
                 help=None,
                 metavar=None):
        if nargs == 0:
            raise ValueError('nargs must be > 0')
        if const is not None and nargs != OPTIONAL:
            raise ValueError('nargs must be %r to supply const' % OPTIONAL)
        super(AppendAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=nargs,
            const=const,
            default=default,
            type=type,
            choices=choices,
            help=help,
            metavar=metavar)

    def __call__(self, parser, namespace, values, option_string=None):
        _ensure_value(namespace, self.dest, []).append(values)

class AppendConstAction(Action):
    def __init__(self,
                 option_strings,
                 dest,
                 const,
                 default=None,
                 help=None,
                 metavar=None):
        super(AppendConstAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=0,
            const=const,
            default=default,
            help=help,
            metavar=metavar)

    def __call__(self, parser, namespace, values, option_string=None):
        _ensure_value(namespace, self.dest, []).append(self.const)

class CountAction(Action):
    def __init__(self,
                 option_strings,
                 dest,
                 default=None,
                 help=None):
        super(CountAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=0,
            default=default,
            help=help)

    def __call__(self, parser, namespace, values, option_string=None):
        new_count = _ensure_value(namespace, self.dest, 0) + 1
        setattr(namespace, self.dest, new_count)

class HelpAction(Action):
    def __init__(self,
                 option_strings,
                 dest,
                 help=None):
        super(HelpAction, self).__init__(
            option_strings=option_strings,
            dest=SUPPRESS,
            nargs=0,
            help=help)

    def __call__(self, parser, namespace, values, option_string=None):
        parser.print_help()
        parser.exit()

class VersionAction(Action):
    def __init__(self,
                 option_strings,
                 dest,
                 help=None):
        super(VersionAction, self).__init__(
            option_strings=option_strings,
            dest=SUPPRESS,
            nargs=0,
            help=help)

    def __call__(self, parser, namespace, values, option_string=None):
        parser.print_version()
        parser.exit()
        
class SubParsersAction(Action):

    def __init__(self,
                 option_strings,
                 prog,
                 parser_class,
                 dest=SUPPRESS,
                 help=None,
                 metavar=None):
        
        self._prog_prefix = prog
        self._parser_class = parser_class
        self._name_parser_map = {}        

        super(SubParsersAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=PARSER,
            choices=self._name_parser_map,
            help=help,
            metavar=metavar)

    def add_parser(self, name, **kwargs):
        if kwargs.get('prog') is None:
            kwargs['prog'] = '%s %s' % (self._prog_prefix, name)

        parser = self._parser_class(**kwargs)        
        self._name_parser_map[name] = parser
        return parser        

    def __call__(self, parser, namespace, values, option_string=None):
        parser_name = values[0]
        arg_strings = values[1:]

        # set the parser name if requested
        if self.dest is not SUPPRESS:
            setattr(namespace, self.dest, parser_name)

        # select the parser        
        try:
            parser = self._name_parser_map[parser_name]
        except KeyError:
            tup = parser_name, ', '.join(self._name_parser_map)
            msg = _('unknown parser %r (choices: %s)' % tup)
            raise ArgumentError(self, msg)

        # parse all the remaining options into the namespace
        parser.parse_args(arg_strings, namespace)


# ===========================
# Optional and Positional Parsing
# ===========================

class Namespace(_AttributeHolder):

    def __init__(self, **kwargs):
        for name, value in kwargs.iteritems():
            setattr(self, name, value)

    def __eq__(self, other):
        return vars(self) == vars(other)

    def __ne__(self, other):
        return not (self == other)


class _ActionsContainer(object):
    def __init__(self,
                 description,
                 conflict_handler):
        superinit = super(_ActionsContainer, self).__init__
        superinit(description=description)

        self.description = description
        self.conflict_handler = conflict_handler

        # set up registries
        self._registries = {}

        # register actions
        self.register('action', None, StoreAction)
        self.register('action', 'store', StoreAction)
        self.register('action', 'store_const', StoreConstAction)
        self.register('action', 'store_true', StoreTrueAction)
        self.register('action', 'store_false', StoreFalseAction)
        self.register('action', 'append', AppendAction)
        self.register('action', 'append_const', AppendConstAction)
        self.register('action', 'count', CountAction)
        self.register('action', 'help', HelpAction)
        self.register('action', 'version', VersionAction)
        self.register('action', 'parsers', SubParsersAction)
        
        # raise an exception if the conflict handler is invalid
        self._get_handler()

        # action storage
        self._optional_actions_list = []
        self._positional_actions_list = []
        self._short_option_strings = {}
        self._long_option_strings = {}

    # ====================
    # Registration methods
    # ====================

    def register(self, registry_name, value, object):
        registry = self._registries.setdefault(registry_name, {})
        registry[value] = object

    def _registry_get(self, registry_name, value, default=None):
        return self._registries[registry_name].get(value, default)

    # =======================
    # Adding argument actions
    # =======================

    def add_argument(self, *args, **kwargs):
        """
        add_argument(dest, ..., name=value, ...)
        add_argument(option_string, option_string, ..., name=value, ...)
        """

        # if no positional args are supplied or only one is supplied and
        # it doesn't look like an option string, parse a positional
        # argument
        if not args or len(args) == 1 and args[0][0] != '-':
            kwargs = self._get_positional_kwargs(*args, **kwargs)

        # otherwise, we're adding an optional argument
        else:
            kwargs = self._get_optional_kwargs(*args, **kwargs)
            
        # create the action object, and add it to the parser
        action_class = self._pop_action_class(kwargs)
        action = action_class(**kwargs)
        return self._add_action(action)

    def _add_action(self, action):
        # resolve any conflicts
        self._check_conflict(action)

        # add to optional or positional list
        if action.option_strings:
            self._optional_actions_list.append(action)
        else:
            self._positional_actions_list.append(action)
        action.container = self

        # index the action by any option strings it has
        for option_string in action.option_strings:
            if option_string.startswith('--'):
                self._long_option_strings[option_string] = action
            else:
                self._short_option_strings[option_string] = action

        # return the created action
        return action

    def _add_container_actions(self, container):
        for action in container._optional_actions_list:
            self._add_action(action)
        for action in container._positional_actions_list:
            self._add_action(action)

    def _get_positional_kwargs(self, dest, **kwargs):
        # all necessary parsing is done by the signature above
        # simply return the keyword arguments with no option strings
        return dict(kwargs, dest=dest, option_strings=[])

    def _get_optional_kwargs(self, *args, **kwargs):
        # determine short and long option strings
        option_strings = list(args)
        short_option_strings = []
        long_option_strings = []
        for option_string in option_strings:
            # error on one-or-fewer-character option strings
            if len(option_string) < 2:
                msg = _('invalid option string %r: '
                        'must be at least two characters long')
                raise ValueError(msg % option_string)

            # two-character option strings should be a dash and a character
            elif len(option_string) == 2:
                if option_string[0] != '-' or option_string[1] == '-':
                    msg = _('invalid short option string %r: must be of '
                            'the form -x, (x any non-dash char)')
                    raise ValueError(msg % option_string)
                short_option_strings.append(option_string)

            # three-or-more-character option strings start with two dashes
            else:
                if option_string[0:2] != '--' or option_string[2] == '-':
                    msg = _('invalid long option string %r: must start '
                            'with --, followed by non-dash')
                    raise ValueError(msg % option_string)
                long_option_strings.append(option_string)

        # infer destination, '--foo-bar' -> 'foo_bar' and '-x' -> 'x'
        dest = kwargs.pop('dest', None)
        if dest is None:
            if long_option_strings:
                dest = long_option_strings[0][2:].replace('-', '_')
            else:
                dest = short_option_strings[0][1:]

        # return the updated keyword arguments
        return dict(kwargs, dest=dest, option_strings=option_strings)

    def _split_option_strings(self, option_strings):
        # return the option strings, split into short and long
        return short_option_strings, long_option_strings                

    def _pop_action_class(self, kwargs, default=None):
        action = kwargs.pop('action', default)
        return self._registry_get('action', action, action)

    def _get_handler(self):
        # determine function from conflict handler string
        handler_func_name = '_handle_conflict_%s' % self.conflict_handler
        try:
            return getattr(self, handler_func_name)
        except AttributeError:
            msg = _('invalid conflict_resolution value: %r')
            raise ValueError(msg % self.conflict_handler)

    def _check_conflict(self, action):

        # find all options that conflict with this option        
        confl_optionals = []
        for option_string in action.option_strings:
            if option_string in self._short_option_strings:
                confl_optional = self._short_option_strings[option_string]
                confl_optionals.append((option_string, confl_optional))
            elif option_string in self._long_option_strings:
                confl_optional = self._long_option_strings[option_string]
                confl_optionals.append((option_string, confl_optional))

        # resolve any conflicts
        if confl_optionals:
            conflict_handler = self._get_handler()
            conflict_handler(action, confl_optionals)

    def _handle_conflict_error(self, action, conflicting_actions):
        message = _('conflicting option string(s): %s')
        conflict_string = ', '.join(option_string
                                    for option_string, action
                                    in conflicting_actions)
        raise ArgumentError(action, message % conflict_string)

    def _handle_conflict_resolve(self, action, conflicting_actions):

        # remove all conflicting options        
        for option_string, action in conflicting_actions:
            
            # remove the conflicting option
            action.option_strings.remove(option_string)
            self._short_option_strings.pop(option_string, None)
            self._long_option_strings.pop(option_string, None)

            # if the option now has no option string, remove it from the
            # container holding it
            if not action.option_strings:
                action.container._optional_actions_list.remove(action)


class ArgumentGroup(_ActionsContainer):

    def __init__(self, container, title=None, description=None, **kwargs):
        # add any missing keyword arguments by checking the container
        update = kwargs.setdefault
        update('conflict_handler', container.conflict_handler)
        superinit = super(ArgumentGroup, self).__init__
        superinit(description=description, **kwargs)
        
        self.title = title
        self._registries = container._registries
        self._short_option_strings = container._short_option_strings
        self._long_option_strings = container._long_option_strings


class ArgumentParser(_AttributeHolder, _ActionsContainer):

    def __init__(self,
                 prog=None,
                 usage=None,
                 description=None,
                 epilog=None,
                 version=None,
                 parents=[],
                 argument_group_class=ArgumentGroup,
                 formatter_class=HelpFormatter,
                 conflict_handler='error',
                 add_help=True):

        superinit = super(ArgumentParser, self).__init__
        superinit(description=description,
                  conflict_handler=conflict_handler)

        # default setting for prog
        if prog is None:
            prog = _os.path.basename(_sys.argv[0])

        self.prog = prog
        self.usage = usage
        self.epilog = epilog
        self.version = version
        self.argument_group_class = argument_group_class
        self.formatter_class = formatter_class
        self.add_help = add_help

        self._has_subparsers = False
        self._optionals_groups = []
        self._defaults = {}

        # register types
        def identity(string):
            return string
        def outfile(string):
            return open(string, 'w')
        self.register('type', None, identity)
        self.register('type', 'outfile', outfile)

        # add help and version arguments if necessary        
        if self.add_help:
            self._add_help_argument()
        if self.version:
            self._add_version_argument()

        # add parent arguments and defaults
        for parent in parents:
            self._add_container_actions(parent)
            try:
                defaults = parent._defaults
            except AttributeError:
                pass
            else:
                self._defaults.update(defaults)
                

    # =======================
    # Pretty __repr__ methods
    # =======================

    def _get_kwargs(self):
        names = [
            'prog',
            'usage',
            'description',
            'version',
            'argument_group_class',
            'formatter_class',
            'conflict_handler',
            'add_help',
        ]
        return [(name, getattr(self, name)) for name in names]

    # ==================================
    # Namespace default settings methods
    # ==================================

    def set_defaults(self, **kwargs):
        self._defaults.update(kwargs)

    # ==================================
    # Optional/Positional adding methods
    # ==================================

    def add_argument_group(self, *args, **kwargs):
        group = self.argument_group_class(self, *args, **kwargs)
        self._optionals_groups.append(group)
        return group

    def add_subparsers(self, **kwargs):
        if self._has_subparsers:
            self.error(_('cannot have multiple subparser arguments'))
        
        # add the parser class to the arguments if it's not present
        kwargs.setdefault('parser_class', type(self))

        # prog defaults to the usage message of this parser, skipping
        # optional arguments and with no "usage:" prefix
        if kwargs.get('prog') is None:
            formatter = self._get_formatter()
            formatter.add_usage(self.usage, [],
                                self._positional_actions_list, '')
            kwargs['prog'] = formatter.format_help().strip()

        # create the parsers action and add it to the positionals list
        parsers_class = self._pop_action_class(kwargs, 'parsers')
        action = parsers_class(option_strings=[], **kwargs)
        self._positional_actions_list.append(action)
        self._has_subparsers = True

        # return the created parsers action
        return action

    def _add_container_actions(self, container):
        super(ArgumentParser, self)._add_container_actions(container)
        try:
            groups = container._optionals_groups
        except AttributeError:
            pass
        else:
            for group in groups:
                new_group = self.add_argument_group(
                    title=group.title,
                    description=group.description,
                    conflict_handler=group.conflict_handler)
                new_group._add_container_actions(group)

    def _get_all_optionals(self):
        optionals = []
        optionals.extend(self._optional_actions_list)
        for optionals_group in self._optionals_groups:
            optionals.extend(optionals_group._optional_actions_list)
        return optionals

    def _add_help_argument(self):
        self.add_argument('-h', '--help', action='help',
                          help=_('show this help message and exit'))

    def _add_version_argument(self):
        self.add_argument('-v', '--version', action='version',
                          help=_("show program's version number and exit"))


    # =====================================
    # Command line argument parsing methods
    # =====================================

    def parse_args(self, args=None, namespace=None):
        # args default to the system args
        if args is None:
            args = _sys.argv[1:]

        # default Namespace built from parser defaults
        if namespace is None:
            namespace = Namespace()
            
        # add any action defaults that aren't present
        actions = self._get_all_optionals() + self._positional_actions_list
        for action in actions:
            if action.dest is not SUPPRESS:
                if not hasattr(namespace, action.dest):
                    if action.default is not SUPPRESS:
                        default = action.default
                        if isinstance(action.default, basestring):
                            default = self._get_value(action, default)
                        setattr(namespace, action.dest, default)

        # add any parser defaults that aren't present
        for dest, value in self._defaults.iteritems():
            if not hasattr(namespace, dest):
                setattr(namespace, dest, value)
            
        # parse the arguments and exit if there are any errors
        try:
            return self._parse_args(args, namespace)
        except ArgumentError, err:
            self.error(str(err))

    def _parse_args(self, arg_strings, namespace):            

        # find all option indices, and determine the arg_string_pattern
        # which has an 'O' if there is an option at an index,
        # an 'A' if there is an argument, or a '-' if there is a '--'
        option_string_indices = set()
        arg_string_pattern_parts = []
        arg_strings_iter = iter(arg_strings)
        for i, arg_string in enumerate(arg_strings_iter):

            # all args after -- are non-options
            if arg_string == '--':
                arg_string_pattern_parts.append('-')
                for arg_string in arg_strings_iter:
                    arg_string_pattern_parts.append('A')

            # otherwise, add the arg to the arg strings
            # and note the index if it was an option
            else:
                if arg_string.startswith('-'):
                    option_string_indices.add(i)
                    pattern = 'O'
                else:
                    pattern = 'A'
                arg_string_pattern_parts.append(pattern)

        # join the pieces together to form the pattern
        arg_strings_pattern = ''.join(arg_string_pattern_parts)

        # converts arg strings to the appropriate and then takes the action
        def take_action(action, argument_strings, option_string=None):
            argument_values = self._get_values(action, argument_strings)
            action(self, namespace, argument_values, option_string)

        # function to convert arg_strings into an optional action
        def consume_optional(start_index):
            
            # determine the optional action and parse any explicit
            # argument out of the option string
            option_string = arg_strings[start_index]
            parse = self._parse_optional
            action, option_string, explicit_arg = parse(option_string)
            match_argument = self._match_argument

            # if there is an explicit argument, try to match the
            # optional's string arguments to only this
            if explicit_arg is not None:
                arg_count = match_argument(action, 'A')
                if arg_count != 1:
                    msg = _('ignored explicit argument %r') % explicit_arg
                    raise ArgumentError(action, msg)
                stop = start_index + 1
                args = [explicit_arg]
            
            # if there is no explicit argument, try to match the
            # optional's string arguments with the following strings
            else:
                start = start_index + 1
                selected_patterns = arg_strings_pattern[start:]
                arg_count = match_argument(action, selected_patterns)
                stop = start + arg_count
                args = arg_strings[start:stop]

            # add the Optional to the list and return the index at which
            # the Optional's string args stopped
            take_action(action, args, option_string)
            return stop

        # the list of Positionals left to be parsed; this is modified
        # by consume_positionals()
        positionals = list(self._positional_actions_list)

        # function to convert arg_strings into positional actions
        def consume_positionals(start_index):
            # match as many Positionals as possible
            match_partial = self._match_arguments_partial
            selected_pattern = arg_strings_pattern[start_index:]
            arg_counts = match_partial(positionals, selected_pattern)

            # slice off the appropriate arg strings for each Positional
            # and add the Positional and its args to the list
            for action, arg_count in zip(positionals, arg_counts):
                args = arg_strings[start_index: start_index + arg_count]
                start_index += arg_count
                take_action(action, args)

            # slice off the Positionals that we just parsed and return the
            # index at which the Positionals' string args stopped
            positionals[:] = positionals[len(arg_counts):]
            return start_index

        # consume Positionals and Optionals alternately, until we have
        # passed the last option string
        start_index = 0
        if option_string_indices:
            max_option_string_index = max(option_string_indices)
        else:
            max_option_string_index = -1
        while start_index <= max_option_string_index:
            
            # consume any Positionals preceding the next option
            next_option_string_index = min(
                index
                for index in option_string_indices
                if index >= start_index)
            if start_index != next_option_string_index:
                positionals_end_index = consume_positionals(start_index)

                # only try to parse the next optional if we didn't consume
                # the option string during the positionals parsing
                if positionals_end_index > start_index:
                    start_index = positionals_end_index
                    continue
                else:
                    start_index = positionals_end_index

            # if we consumed all the positionals we could and we're not
            # at the index of an option string, there were unparseable
            # arguments
            if start_index not in option_string_indices:
                msg = _('extra arguments found: %s')
                extras = arg_strings[start_index:next_option_string_index]
                self.error(msg % ' '.join(extras))

            # consume the next optional and any arguments for it
            start_index = consume_optional(start_index)

        # consume any positionals following the last Optional
        stop_index = consume_positionals(start_index)

        # if we didn't consume all the argument strings, there were too
        # many supplied
        if stop_index != len(arg_strings):
            extras = arg_strings[stop_index:]
            self.error(_('extra arguments found: %s') % ' '.join(extras))

        # if we didn't use all the Positional objects, there were too few
        # arg strings supplied.
        if positionals:
            self.error(_('too few arguments'))

        # return the updated namespace
        return namespace

            
    def _match_argument(self, action, arg_strings_pattern):
        # match the pattern for this action to the arg strings
        nargs_pattern = self._get_nargs_pattern(action)
        match = _re.match(nargs_pattern, arg_strings_pattern)

        # raise an exception if we weren't able to find a match        
        if match is None:
            nargs_errors = {
                None:_('expected one argument'),
                OPTIONAL:_('expected at most one argument'),
                ONE_OR_MORE:_('expected at least one argument')
            }
            default = _('expected %s argument(s)') % action.nargs
            msg = nargs_errors.get(action.nargs, default)
            raise ArgumentError(action, msg)

        # return the number of arguments matched
        return len(match.group(1))

    def _match_arguments_partial(self, actions, arg_strings_pattern):
        # progressively shorten the actions list by slicing off the
        # final actions until we find a match
        result = []
        for i in xrange(len(actions), 0, -1):
            actions_slice = actions[:i]
            pattern = ''.join(self._get_nargs_pattern(action)
                              for action in actions_slice)
            match = _re.match(pattern, arg_strings_pattern)
            if match is not None:
                result.extend(len(string) for string in match.groups())
                break

        # return the list of arg string counts
        return result
    
    def _parse_optional(self, option_string):
        # for long option strings, split off '=' arguments if necessary
        # and call _match_long_option_string()
        if option_string.startswith('--'):
            if '=' in option_string:
                option_string, explicit_arg = option_string.split('=')
            else:
                explicit_arg = None
            action = self._match_long_option_string(option_string)

        # for short option strings, split off the characters past 1 if
        # necessary and check the _short_option_strings dict
        else:
            if len(option_string) > 2:
                explicit_arg = option_string[2:]
                option_string = option_string[:2]
            else:
                explicit_arg = None
            try:
                action = self._short_option_strings[option_string]
            except KeyError:
                action = None

        # if we found no optional action, raise an error
        if action is None:
            self.error(_('no such option: %s') % option_string)

        # otherwise return the optional and the explicit string argument
        return action, option_string, explicit_arg

    def _match_long_option_string(self, option_string):
        long_opts = self._long_option_strings

        # short path: just look it up in the table
        try:
            action = long_opts[option_string]

        # long path: check all words with the argument string as a prefix
        except KeyError:
            possible_option_strings = [
                word for word in long_opts if word.startswith(option_string)
            ]

            # see if there is exactly one possible string
            try:
                option_string, = possible_option_strings

            # if there are zero or multiple matches, report errors
            except ValueError:
                if possible_option_strings:
                    tup = option_string, ', '.join(possible_option_strings)
                    self.error(_('ambiguous option: %s (%s?)') % tup)
                else:
                    self.error(_('no such option: %s') % option_string)

            # if there was exactly one match, return the Optional for it
            else:
                action = long_opts[option_string]

        return action
                
    def _get_nargs_pattern(self, action):
        # in all examples below, we have to allow for '--' args
        # which are represented as '-' in the pattern
        nargs = action.nargs
        
        # the default (None) is assumed to be a single argument
        if nargs is None:
            nargs_pattern = '(-*A-*)'

        # allow zero or one arguments
        elif nargs == OPTIONAL:
            nargs_pattern = '(-*A?-*)'

        # allow zero or more arguments
        elif nargs == ZERO_OR_MORE:
            nargs_pattern = '(-*[A-]*)'

        # allow one or more arguments
        elif nargs == ONE_OR_MORE:
            nargs_pattern = '(-*A[A-]*)'

        # allow one argument followed by any number of options or arguments
        elif nargs is PARSER:
            nargs_pattern = '(-*A[-AO]*)'

        # all others should be integers            
        else:
            nargs_pattern = '(-*%s-*)' % '-*'.join('A' * nargs)
        
        # return the pattern
        return nargs_pattern

    # ========================
    # Value conversion methods
    # ========================

    def _get_values(self, action, arg_strings):
        # for everything but PARSER args, strip out '--'
        if action.nargs is not PARSER:
            arg_strings = [s for s in arg_strings if s != '--']
        
        # optional argument produces a default when not present
        if not arg_strings and action.nargs == OPTIONAL:
            if action.option_strings:
                value = action.const
            else:
                value = action.default
            if isinstance(value, basestring):
                value = self._get_value(action, value)
                self._check_value(action, value)
        
        # single argument or optional argument produces a single value
        elif len(arg_strings) == 1 and action.nargs in [None, OPTIONAL]:
            arg_string, = arg_strings
            value = self._get_value(action, arg_string)
            self._check_value(action, value)

        # PARSER arguments convert all values, but check only the first
        elif action.nargs is PARSER:
            value = list(self._get_value(action, v) for v in arg_strings)
            self._check_value(action, value[0])

        # all other types of nargs produce a list
        else:
            value = list(self._get_value(action, v) for v in arg_strings)
            for v in value:
                self._check_value(action, v)

        # return the converted value            
        return value

    def _get_value(self, action, arg_string):
        type_func = self._registry_get('type', action.type, action.type)
        if not callable(type_func):
            msg = _('%r is not callable')
            raise ArgumentError(action, msg % type_func)
        
        # convert the value to the appropriate type
        try:
            result = type_func(arg_string)

        # TypeErrors or ValueErrors indicate errors
        except (TypeError, ValueError):
            name = getattr(action.type, '__name__', repr(action.type))
            msg = _('invalid %s value: %r')
            raise ArgumentError(action, msg % (name, arg_string))

        # return the converted value
        return result

    def _check_value(self, action, value):
        # converted value must be one of the choices (if specified)
        if action.choices is not None and value not in action.choices:
            tup = value, ', '.join(map(repr, action.choices))
            msg = _('invalid choice: %r (choose from %s)') % tup
            raise ArgumentError(action, msg)

        

    # =======================
    # Help-formatting methods
    # =======================

    def format_usage(self):
        formatter = self._get_formatter()
        formatter.add_usage(self.usage,
                            self._get_all_optionals(),
                            self._positional_actions_list)
        return formatter.format_help()

    def format_help(self):
        formatter = self._get_formatter()

        # usage
        formatter.add_usage(self.usage,
                            self._get_all_optionals(),
                            self._positional_actions_list)

        # description        
        formatter.add_text(self.description)

        # positionals
        formatter.start_section(_('positional arguments'))
        formatter.add_arguments(self._positional_actions_list)
        formatter.end_section()

        # optionals
        formatter.start_section(_('optional arguments'))
        formatter.add_arguments(self._optional_actions_list)
        for optionals_group in self._optionals_groups:
            formatter.start_section(optionals_group.title)
            formatter.add_text(optionals_group.description)
            formatter.add_arguments(optionals_group._optional_actions_list)
            formatter.end_section()
        formatter.end_section()

        # epilog
        formatter.add_text(self.epilog)

        # determine help from format above
        return formatter.format_help()

    def format_version(self):
        formatter = self._get_formatter()
        formatter.add_text(self.version)
        return formatter.format_help()

    def _get_formatter(self):
        return self.formatter_class(prog=self.prog)

    # =====================
    # Help-printing methods
    # =====================

    def print_usage(self, file=None):
        self._print_message(self.format_usage(), file)

    def print_help(self, file=None):
        self._print_message(self.format_help(), file)

    def print_version(self, file=None):
        self._print_message(self.format_version(), file)

    def _print_message(self, message, file=None):
        if message:
            if file is None:
                file = _sys.stderr
            file.write(message)


    # ===============
    # Exiting methods
    # ===============

    def exit(self, status=0, message=None):
        if message:
            _sys.stderr.write(message)
        _sys.exit(status)

    def error(self, message):
        """error(message: string)

        Prints a usage message incorporating the message to stderr and
        exits.
        
        If you override this in a subclass, it should not return -- it
        should either exit or raise an exception.
        """
        self.print_usage(_sys.stderr)
        self.exit(2, _('%s: error: %s\n') % (self.prog, message))
