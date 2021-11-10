# Lint as: python2, python3
"""This module gives the mkfs creation options for an existing filesystem.

tune2fs or xfs_growfs is called according to the filesystem. The results,
filesystem tunables, are parsed and mapped to corresponding mkfs options.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os, re, tempfile
import six
import common
import time
import os.path

from autotest_lib.client.bin import test
from autotest_lib.client.bin import utils
from autotest_lib.client.common_lib import error, utils
from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros import chrome
from autotest_lib.client.cros.input_playback import input_playback


_WAIT = 10
#_TMP = '/tmp'
DOWNLOADS = '/home/chronos/user/Downloads'
SCREENSHOT = 'Screenshot*'
ERROR = list()



def screenshot():
    """Test setup."""
    # Emulate keyboard.
    # See input_playback. The keyboard is used to play back shortcuts.
    player = input_playback.InputPlayback()
    player.emulate(input_type='keyboard')
    player.find_connected_inputs()
    player.blocking_playback_of_default_file(
            input_type='keyboard', filename='keyboard_ctrl+f5')
    time.sleep(_WAIT)
    
    
def confirm_file_exist(filepath):
    """Check if screenshot file can be found and with minimum size.

    @param filepath file path.

    @raises: error.TestFail if screenshot file does not exist.

   """
    if not os.path.isdir(filepath):
        raise error.TestNAError("%s folder is not found" % filepath)

    if not (utils.system_output('sync; sleep 2; find %s -name "%s"'
                                    % (filepath, SCREENSHOT))):
        ERROR.append('Screenshot was not found under:%s' % filepath)

    filesize = utils.system_output('ls -l %s/%s | cut -d" " -f5'
                                       % (filepath, SCREENSHOT))
    
    