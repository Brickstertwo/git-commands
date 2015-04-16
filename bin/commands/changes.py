from subprocess import call, check_output
from utils.messages import info


def changes(branch, count=False):
    '''Print the changes between a given branch and HEAD'''

    command = ['git', 'log', '--oneline', '{}..HEAD'.format(branch)]
    if count:
        log = check_output(command)
        log = log.splitlines()
        info(len(log))
    else:
        call(command)