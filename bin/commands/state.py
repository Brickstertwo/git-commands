"""View the state of the working tree."""

import os
import shlex
import sys
from ast import literal_eval
from collections import OrderedDict
from subprocess import call, check_output, PIPE, Popen

import colorama

from . import settings
from stateextensions import branches, log, reflog, stashes, status
from utils import directories
from utils.messages import error


def _print_section(title, accent=None, text=None, format='compact', show_empty=False):
    """Print a section."""

    if not show_empty and not text:
        return ""

    if accent:
        section = '# {}{} {}{}'.format(colorama.Fore.GREEN, title, accent, colorama.Fore.RESET) + os.linesep
    else:
        section = '# {}{}{}'.format(colorama.Fore.GREEN, title, colorama.Fore.RESET) + os.linesep

    if format == 'pretty' and text is not None and len(text) > 0:
        # pretty print
        section += os.linesep
        text = text.splitlines()
        for line in text:
            section += '    ' + line + os.linesep
        section += os.linesep
    elif format == 'pretty':
        # there's no text but we still want some nicer formatting
        section += os.linesep
    elif format == 'compact':
        section += text
    else:
        error("unknown format '{}'".format(format))

    return section


def _is_new_repository():
    """Determines whether a repository is empty."""

    with open(os.devnull, 'w') as devnull:
        log_proc = Popen(['git', 'log', '--oneline', '-1'], stdout=devnull, stderr=devnull)
        log_proc.wait()
        return log_proc.returncode != 0


def state(**kwargs):
    """Print the state of the working tree."""

    if not directories.is_git_repository():
        error('{0!r} not a git repository'.format(os.getcwd()))

    show_color = kwargs.get('show_color').lower()
    if show_color == 'never' or (show_color == 'auto' and not sys.stdout.isatty()):
        show_color = 'never'
        colorama.init(strip=True)
    elif show_color == 'auto' and sys.stdout.isatty():
        show_color = 'always'
        colorama.init()

    kwargs['show_color'] = show_color
    kwargs['show_clean_message'] = settings.get(
        'git-state.status.show-clean-message',
        default=True,
        as_type=settings.as_bool
    )

    state = ''
    format = kwargs.get('format')
    if _is_new_repository():
        status_output = status.get(new_repository=True, **kwargs)
        status_title = status.title()
        status_accent = status.accent(new_repository=True, **kwargs)
        sections = {status_title: _print_section(status_title, status_accent, status_output, format)}
    else:
        sections = OrderedDict()
        if kwargs.get('show_status'):
            status_output = status.get(**kwargs)
            status_title = status.title()
            status_accent = status.accent(show_color=show_color)
            sections[status_title] = _print_section(status_title, status_accent, status_output, format, show_empty=True)

        if kwargs.get('log_count'):
            log_output = log.get(**kwargs)
            log_title = log.title()
            sections[log_title] = _print_section(log_title, text=log_output, format=format)

        if kwargs.get('reflog_count'):
            reflog_output = reflog.get(**kwargs)
            reflog_title = reflog.title()
            sections[reflog_title] = _print_section(reflog_title, text=reflog_output, format=format)

        if kwargs.get('show_branches'):
            branches_output = branches.get(**kwargs)
            branches_title = branches.title()
            sections[branches_title] = _print_section(branches_title, text=branches_output, format=format)

        if kwargs.get('show_stashes'):
            stashes_output = stashes.get(show_color=show_color)
            stashes_title = stashes.title()
            sections[stashes_title] = _print_section(
                stashes_title,
                text=stashes_output,
                format=format,
                show_empty=kwargs.get('show_empty')
            )

        # show any user defined sections
        extensions = settings.list(
            section='git-state.extensions',
            config=None,
            count=False,
            keys=True,
            format=None,
            file=None
        ).splitlines()
        extensions = list(set(extensions) - set(kwargs.get('ignore_extensions')))
        options = kwargs.get('options')
        for extension in extensions or []:
            extension_command = settings.get('git-state.extensions.' + extension)
            extension_name = settings.get('git-state.extensions.' + extension + '.name', extension)
            extension_options = options[extension_name] if extension_name in options else []
            extension_command = shlex.split(extension_command) + ['--color={}'.format(show_color)] + extension_options
            extension_proc = Popen(extension_command, stdout=PIPE, stderr=PIPE)
            extension_out, extension_error = extension_proc.communicate()

            sections[extension_name] = _print_section(
                title=extension_name,
                text=extension_out if not extension_proc.returncode else extension_error,
                format=format,
                show_empty=kwargs.get('show_empty')
            )

    state = ''

    # print sections with a predefined order
    order = kwargs.get('order', settings.get('git-state.order', default=[], as_type=settings.as_delimited_list('|')))
    for section in order:
        if section in sections:
            state += sections.pop(section)

    # print any remaining sections in the order they were defined
    for section_info in sections:
        state += sections[section_info]

    state = state[:-1] # strip the extra trailing newline
    state_lines = len(state.splitlines())
    terminal_lines = literal_eval(check_output(['tput', 'lines']))
    if terminal_lines >= state_lines + 2: # one for the newline and one for the prompt
        if kwargs.get('clear') and sys.stdout.isatty():
            call('clear')
        print state
    else:
        echo = Popen(['echo', state], stdout=PIPE)
        call(['less', '-r'], stdin=echo.stdout)
        echo.wait()
