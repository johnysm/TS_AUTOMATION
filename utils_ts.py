# Lint as: python2, python3
# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Convenience functions for use by tests or whomever.
"""

# pylint: disable=missing-docstring

import base64
import collections
import errno
import glob
import json
import logging
import math
import multiprocessing
import os
import platform
import re
import shutil
import string
import subprocess
import time
import uuid
import six
from six.moves import map
from six.moves import range
from six.moves import zip
from telemetry.internal.actions import scroll
from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib import magic
from autotest_lib.client.bin import utils as bin_utils
from autotest_lib.client.common_lib.cros import cros_config
from autotest_lib.client.bin import test
from autotest_lib.client.cros.input_playback import keyboard
from autotest_lib.client.cros.input_playback import input_playback
from autotest_lib.client.common_lib import ui_utils
from autotest_lib.client.common_lib.cros import chrome
from autotest_lib.client.cros.graphics import graphics_utils
from autotest_lib.client.common_lib.utils import *
from autotest_lib.client.common_lib import utils
import py_utils
WAIT = 5
_WAKETIME = 8
_URL_WAKEUP_TIME = 10
Delay_time = 8
BUTTON_ROLE = "button"
STATUS_TRAY_REGEXP = "/Status tray, /i"
current_scaling_governor = 'cat /sys/devices/system/cpu/cpufreq/policy*/scaling_governor'
current_scaling_freq = 'cat /sys/devices/system/cpu/cpufreq/policy*/scaling_cur_freq'
min_frequency = 'cat /sys/devices/system/cpu/cpufreq/policy*/cpuinfo_max_freq'
max_frequency = 'cat /sys/devices/system/cpu/cpufreq/policy*/cpuinfo_min_freq'
_CPUINFO_RE = re.compile(r'^(?P<key>[^\t]*)\t*: ?(?P<value>.*)$')
_MEMINFO_RE = re.compile('^(\w+)(\(\w+\))?:\s+(\d+)')

def command_exe(cmd, file_name, folder=None):
    """
    To execute command line argument and write its output to a file given by the user
    @output:prints file_path,user can check the output@filepath    
    """
    if folder:
        file_path = os.path.join(folder, file_name)
        subprocess.call('%s > %s' % (cmd, file_path), shell=True)
        logging.info(file_path)
    else:
        file_path = os.path.join(os.getcwd(), file_name)
        subprocess.call('%s > %s' % (cmd, file_path), shell=True)
        logging.info(file_path)

def validate_string_findall(pattern, file):
    """
    Reads data from file,checks for required pattern given by the user
    using regex findall predefined in build python function
    and returns two outputs
    1)(True or False)
    2)prints pattern finding the string if found or not found in the form of list
    """
    try:
        file_open = open(file, 'r')
    except:
        logging.info("file not found")
        return -1
    file_data = file_open.read()
    ret_out = re.findall(pattern, file_data)
    if ret_out:
        return True, ret_out
    else:
        return False, ret_out

def validate_string_match(self, pattern, file):
    """
    Reads data from file,checks for required pattern given by the user
    using regex match predefined in build python function
    and returns two outputs
    1)(True or False)
    2)prints pattern matching string if matched or not matched in the form of list
    """
    try:
        file_open = open(file, 'r')
    except:
        logging.info("file not found")
        return -1
    file_data = file_open.read()
    ret_out = re.match(pattern, file_data)
    if ret_out:
        return True, ret_out
    else:
        return False, ret_out

def validate_string_search(self, pattern, file):
    """
    Reads data from file,checks for required pattern given by the user
    using regex match predefined in build python function
    and returns two outputs
    1)(True or False)
    2)prints pattern string data if searched or not searched as a object in the form of list
    """
    try:
        file_open = open(file, 'r')
    except:
        logging.info("file not found")
        return -1
    file_data = file_open.read()
    ret_out = re.search(pattern, file_data)
    if ret_out:
        return True, ret_out
    else:
        return False, ret_out

def validate_string_split(self, pattern, file):
    """
    Reads data from file,check for required pattern
    and returns pattern find or not (True or False) and output pattern
    """
    try:
        file_open = open(file, 'r')
    except:
        logging.info("file not found")
        return -1
    file_data = file_open.read()
    ret_out = re.split(pattern, file_data)
    if ret_out:
        return True, ret_out
    else:
        return False, ret_out

def change_permissions(path, permission='777'):
    """
    Applying permissions to file/path to write,change in the file
    @path - file/directory path
    @permission - required permission( default is 777)
    """
    if os.path.exists(path):
        subprocess.call('chmod -R %s %s'%(permission,path),shell=True)
    else:
        raise NameError('invalid path %s'% path)

def reboot(host=None):
    """
    To reboot the device.
    """
    if host:
        host.reboot()

def suspend(host=None,time=10):
    """
    suspend the device for certain time and wake the device
    @time - time limit to wake the device
    """
    if host:
        host.suspend(time)

def scaling_governor():
    """
    this function will return current scaling governor on all cores
    """
    ret_out = utils.run(current_scaling_governor).stdout.strip('\n').replace(',', ' ')
    return ret_out

def scaling_frequencies():
    """
    this function will return current scaling freq on all cores
    """
    ret_out = utils.run(current_scaling_freq).stdout.strip('\n').replace(',', ' ')
    return ret_out

def cpu_max_freq():
    """
    """
    ret_out = utils.run(max_frequency).stdout.strip('\n').replace(',', ' ')
    return ret_out

def cpu_min_freq():
    """
    """
    ret_out = utils.run(min_frequency).stdout.strip('\n').replace(',', ' ')
    return ret_out

def mkdir(name_folder,path):
    """
    This function will create directory
    @name_folder - name of the directory to be created
    @path - it is path where user need to create directory
    """
    folder_name = os.path.join(path,name_folder)
    if not os.path.exists(folder_name):
        os.mkdir(folder_name)
    else:
        raise NameError('path %s already exists'% path)

def read_dmesg_log(host=None):
    """
    This function will return dmesg logs
    """
    if host:
        ret_out = host.run('dmesg').stdout
        return ret_out
    else:
        ret_out = utils.run('dmesg').stdout
        return ret_out

def read_cbmem_log(host=None):
    """
    This function will return cbmem logs of last reboot
    """
    if host:
        ret_out = host.run('cbmem -1').stdout
        return ret_out
    else:
        ret_out = utils.run('cbmem -1').stdout
        return ret_out

def get_board_property(key):
    """
    Get a specific property from /etc/lsb-release.
    @param key: board property to return value for
    @return the value or '' if not present
    """
    with open('/etc/lsb-release') as f:
        pattern = '%s=(.*)' % key
        pat = re.search(pattern, f.read())
        if pat:
            return pat.group(1)
    return ''

def get_board():
    """
    Get the ChromeOS release board name from /etc/lsb-release.
    """
    try:
        get_board_property('BOARD')
    except:
        logging.info("board property not found")
        return -1

def get_chromeos_version():
    """
    Get the ChromeOS build version from /etc/lsb-release.
    @return chromeos release version.
    """
    try:
        get_board_property('CHROMEOS_RELEASE_VERSION')
    except:
        logging.info("CHROMEOS_RELEASE_VERSION not found")
        return -1

def get_chromeos_platform_name():
    """
    Get the ChromeOS platform name.
    For unibuild this should be equal to model name.  For non-unibuild
    it will either be board name or empty string.  In the case of
    empty string return board name to match equivalent logic in
    server/hosts/cros_host.py
    @returns platform name
    """
    try:
        platform = cros_config.call_cros_config_get_output('/ name', utils.run)
        if platform == '':
            platform = get_board()
        return platform
    except:
        logging.info("Not found")
        return -1
'''
def get_ec_version():
    """Get the ec version as strings.
    @returns a string representing this host's ec version.
    """
    try:
        command = 'mosys ec info -s fw_version'
        result = utils.run(command, ignore_status=True)
        if result.exit_status != 0:
            return ''
        return result.stdout.strip()
    except:
        logging.info("Not Found")
        return -1
'''

def get_firmware_version():
    """Get the firmware version as strings.
    @returns a string representing this host's firmware version.
    """
    return utils.run('crossystem fwid').stdout.strip()

def get_hardware_id():
    """Get hardware id as strings.
    @returns a string representing this host's hardware id.
    """
    try:
        return utils.run('crossystem hwid').stdout.strip()
    except:
        logging.info("Not Found")
        return -1  
'''def get_hardware_revision():
    """Get the hardware revision as strings.
    @returns a string representing this host's hardware revision.
    """
    command = 'mosys platform version'
    result = utils.run(command, ignore_status=True)
    if result.exit_status != 0:
        return ''
    return result.stdout.strip()
'''

def get_kernel_version():
    """Get the kernel version as strings.
    @returns a string representing this host's kernel version.
    """
    try:
        return utils.run('uname -r').stdout.strip()
    except:
        logging.info("Not Found")
        return -1

def cat_file_to_cmd(file, command, ignore_status=0, return_output=False):
    """
    Generally cat is used to see the hidden command output
    where this function is equivalent to 'cat file | command' but knows to use
    zcat or bzcat if appropriate
    """
    if not os.path.isfile(file):
        raise NameError('invalid file %s to cat to command %s'
                % (file, command))
    if return_output:
        run_cmd = utils.system_output
    else:
        run_cmd = utils.system
    if magic.guess_type(file) == 'application/x-bzip2':
        cat = 'bzcat'
    elif magic.guess_type(file) == 'application/x-gzip':
        cat = 'zcat'
    else:
        cat = 'cat'
    return run_cmd('%s %s | %s' % (cat, file, command),
                   ignore_status=ignore_status)

def force_copy(src, dest):
    """Replaces destination with a new copy of src, even if it exists"""
    if os.path.isfile(dest):
        os.remove(dest)
    if os.path.isdir(dest):
        dest = os.path.join(dest, os.path.basename(src))
    shutil.copyfile(src, dest)
    return dest

def file_contains_pattern(file, pattern):
    """function will return true if file contains the specified egrep pattern"""
    if not os.path.isfile(file):
        raise NameError('file %s does not exist' % file)
    return not utils.system('egrep -q "' + pattern + '" ' + file,
                            ignore_status=True)
def list_grep(list, pattern):
    """Returns 1 if any item in list matches the specified pattern else returns 0."""
    compiled = re.compile(pattern)
    for line in list:
        match = compiled.search(line)
        if (match):
            return 1
    return 0

def get_cpuinfo():
    """Read information of cpu using /proc/cpuinfo and converts to a list of dicts."""
    cpuinfo = []
    with open('/proc/cpuinfo', 'r') as f:
        cpu = {}
        for line in f:
            line = line.strip()
            if not line:
                cpuinfo.append(cpu)
                cpu = {}
                continue
            match = _CPUINFO_RE.match(line)
            cpu[match.group('key')] = match.group('value')
        if cpu:
            # cpuinfo usually ends in a blank line, so this shouldn't happen.
            cpuinfo.append(cpu)
    return cpuinfo

def get_current_kernel_arch():
    """To get the machine architecture, its just a wrap of 'uname -m'."""
    try:
        return os.popen('uname -m').read().rstrip()
    except:
        logging.info("Not Found")
        return -1

def count_cpus():
    """Counts number of CPUs in the local machine by using /proc/cpuinfo command """
    try:
        return multiprocessing.cpu_count()
    except Exception:
        logging.exception('can not get cpu count from'
                          ' multiprocessing.cpu_count()')
    cpuinfo = get_cpuinfo()
    # Returns at least one cpu. Check comment #1 in crosbug.com/p/9582.
    return len(cpuinfo) or 1

def cpu_online_map():
    """
    Check out the available cpu online map@like how many cpus are on/off
    """
    cpuinfo = get_cpuinfo()
    cpus = []
    for cpu in cpuinfo:
        cpus.append(cpu['processor'])  # grab cpu number
    return cpus
# Returns total memory in kb

def read_from_meminfo(key):
    """
    Check out the system memory information@ by using regex search expression
    """
    meminfo = utils.system_output('grep %s /proc/meminfo' % key)
    return int(re.search(r'\d+', meminfo).group(0))

def memtotal():
    """
    To get total memory information
    """
    try:
        return read_from_meminfo('MemTotal')
    except:
        logging.info("Not Found")
        return -1

def get_meminfo():
    """Returns a namedtuple of pairs from /proc/meminfo.
    Example /proc/meminfo snippets:
        MemTotal:        2048000 kB
        Active(anon):     409600 kB
    Example usage:
        meminfo = utils.get_meminfo()
        print meminfo.Active_anon
    """
    info = {}
    with open('/proc/meminfo') as f:
        for line in f:
            m = _MEMINFO_RE.match(line)
            if m:
                if m.group(2):
                    name = m.group(1) + '_' + m.group(2)[1:-1]
                else:
                    name = m.group(1)
                info[name] = int(m.group(3))
    return collections.namedtuple('MemInfo', list(info.keys()))(**info)

def usb_devices():
    """
    This function return list of connected usb devices/hubs
    @returns list of connected usb devices
    """
    ret_out = utils.run('lsusb').stdout.strip('\n').replace(',', ' ')
    return ret_out

def mounts():
    """
    This function returns all mount points and other details of disks/partitions/file systems
    @returns list of dictionaries. each dictionary contains partition/fs, mount point and mount/fs type
    """
    ret = []
    with open('/proc/mounts') as f:
        lines = f.readlines()
    for line in lines:
        m = re.match(
            r'(?P<src>\S+) (?P<dest>\S+) (?P<type>\S+)', line)
        if m:
            ret.append(m.groupdict())
    return ret

def is_mountpoint(path):
    """
    This function verifies whether given path is mount point or not
    @ param path : mount point/ mount point path
    @returns True if path is already mount point else False
    """
    return path in [m['dest'] for m in mounts()]

def require_mountpoint(path):
    """
    Raises an exception if path is not a mountpoint.
    """
    if not is_mountpoint(path):
        raise error.TestFail('Path not mounted: "%s"' % path)

def list_mount_devices():
    """
    @returns all mountable/mounted devices/partitions
    """
    devices = []
    # list mounted filesystems
    for line in utils.system_output('mount').splitlines():
        devices.append(line.split()[0])
    return devices

def _get_thermal_zone_temperatures():
    """
    Returns the maximum currently observered temperature in thermal_zones.
    """
    temperatures = []
    for path in glob.glob('/sys/class/thermal/thermal_zone*/temp'):
        try:
            temperatures.append(
                bin_utils._get_float_from_file(path, 0, None, None) * 0.001)
        except IOError:
            # Some devices (e.g. Veyron) may have reserved thermal zones that
            # are not active. Trying to read the temperature value would cause a
            # EINVAL IO error.
            continue
    return temperatures

def get_root_device():
    """
    Return root device.
    Will return correct disk device even system boot from /dev/dm-0
    Example: return /dev/sdb for falco booted from usb
    """
    return utils.system_output('rootdev -s -d')
'''
def read_from_storage(block_size,count):
    """
    """
    read_out = utils.run('dd if=/dev/zero of=/home/user/read_file bs=%s count=%s'%().stdout.strip('\n').replace(',', ' ')
'''

def disconnect_from_wifi_network(SSID):
    """
        This function is to disconnect from SSID
        @params SSID name of the Network
    """
    Disconnect_cmd="./wifi disconnect "+ SSID
    get_output=subprocess.Popen(Disconnect_cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE, stderr=subprocess.PIPE,shell=True)
    print("output ",get_output.stderr.readlines())
    for ele in get_output.stderr.readlines():
        if "already connected" in ele:
            return True
        else:
            raise error.TestError("Failed to DisConnect from SSID ")
    time.sleep(Delay_time)

def connect_to_wifi_network(SSID,Passphrase,security_mode):
    """
    Connect to SSID network
    @params SSID --name of the network
    @params Passphrase --password
    @params security_mode -- security property
    """
    read_outputDict={}
    read_outputDict["status"]=''
    #default path to connect wifi
    script_path="/usr/local/autotest/cros/scripts"
    # os.chdir() is used to change dir to wifi script path
    change_dir = os.chdir(script_path)
    #cmd is used to connect to SSID with/without passphrase
    connect_cmd="./wifi connect "+ SSID +" "+Passphrase +" "+ security_mode +" >" + "status.txt"
    #Popen then cmd and get th output to validate whether is connected or not
    get_output=subprocess.Popen(connect_cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE, stderr=subprocess.PIPE,shell=True) 
    """if get_output.stderr:
        raise error.TestFail("Failed to connect to network",SSID)
    else:
        print("Error ",get_output.stderr.readlines()) """   
    time.sleep(Delay_time)

def copy_file_to_server():
    """Copy the recorded file to log location"""
    utils.system_output('mv /home/chronos/user/Downloads/* /usr/local/autotest/results/default/',ignore_status=True)
    logging.info("Video Copied to Log location")

def scrolling(URL1,URL2,Scroll_Speed,Scroll_Distance,cr):
    """Perform scroll action on URLs given to the specified distance with specified speed
    @param URL1,URL2 : URLs to perform scroll operation
    @param Scroll_Speed(pixels): Speed of scrolling Eg: 1500,2000
    @param Scroll_Distance(pixels): Distance to which scroll has to happen Eg: 2000,3000 """
    list_of_urls = [URL1,URL2]
    for url in list_of_urls:
        #To open new tab for each url
        tab = cr.browser.tabs.New()
        tab.Navigate(url)
        try:
            tab.WAITForDocumentReadyStateToBeComplete(timeout=_URL_WAKEUP_TIME)
            ui = ui_utils.UI_Handler()
            ui.start_ui_root(cr)
            list=ui.get_name_role_list() 
            #To get the list of ui elements
        except py_utils.TimeoutException:
            logging.warning('Time out during loading url ' + url)
            #Performs scrolling
            page_scroll = scroll.ScrollAction(
            direction="up",
            speed_in_pixels_per_second=Scroll_Speed,distance=Scroll_Distance)
            page_scroll.WillRunAction(tab)
            page_scroll.RunAction(tab)

def click_UI(ui,ele_list):   
    """fun used for ui clicks
        UIelement_list --ui element list it contains Uistr, bool True/False True-if it is Regular Expression False -if it is Constant , and button Type
    """
    try:
        for lst in ele_list:
            list_index=0
            ui.wait_for_ui_obj(lst[list_index],lst[list_index+1],lst[list_index+2])
            ui.doDefault_on_obj(lst[list_index],lst[list_index+1],lst[list_index+2])
            time.sleep(8)
            get_ui_list=ui.get_name_role_list()
            print(get_ui_list)
    except error.TestFail:
        raise
    except Exception as e:
        logging.error('Exception "%s" seen during test', e)
        raise error.TestFail('Exception "%s" seen during test' % e)

def warmup():
    """Test setup.
    Emulate keyboard.
    See input_playback. The keyboard is used to play back shortcuts.
    returns keyboards input device """
    _player = input_playback.InputPlayback()
    _player.emulate(input_type='keyboard')
    _player.find_connected_inputs()
    return _player

def launch_an_app(appname,ui):
    """Launch an app from Launcher
    @param appname - Application name which needs to be minimized
    @ui To click on the UI element - Launcher,Expand,App"""
    ui = ui
    time.sleep(WAIT)
    """Clicking on Launcher button"""
    ui.doDefault_on_obj('Launcher', False, role='button') 
    time.sleep(WAIT)
    ui.doDefault_on_obj(name='Expand to all apps', role='button')
    time.sleep(WAIT)
    """Launching an APK"""
    ui.doDefault_on_obj(appname, False, 'button') 
    time.sleep(WAIT)

def minimize_app(appname,ui):
    """Minimizing App from Shelf
    @param appname - Application name which needs to be minimized
    @ui To click on the UI element - Minimize button of the app window"""
    ui=ui
    ui.doDefault_on_obj('Minimize', False, 'button') 
    time.sleep(WAIT)

def maximize_app( appname,ui):
    """Maximizing App from Shelf
    @param appname - Application name which needs to be maximized
    @ui To click on ui element - appname from Shelf"""
    ui=ui
    ui.doDefault_on_obj(appname, False, 'button') 

def validate_orientation():
    """opening system tray and launching settings"""
    ui.click_and_WAIT_for_item_with_retries('/tray/', 'Settings', True)
    time.sleep(WAIT)
    ui.doDefault_on_obj(name='Settings', role='button')
    time.sleep(WAIT)
    ui.doDefault_on_obj(name='Displays', role='link')
    time.sleep(WAIT)

def default_login():
    """Login to device with default credential
    returns cr object"""
    cr=chrome.Chrome(disable_default_apps=False,autotest_ext=True)
    return cr

def login_with_credentials(username,password):
    """ Login to device with given credentials
    @param username to loin into device
    @param password for the given username
    returns cr object"""
    cr=chrome.Chrome(username=username,password=password,disable_default_apps=False,autotest_ext=True)
    return cr

def change_orientation():
    """Test to rotate internal display"""
    facade = facade_resource.FacadeResource()
    facade.start_default_chrome()
    display_facade = display_facade_native.DisplayFacadeNative(facade)
    """Get internal display ID"""
    internal_display_id = display_facade.get_internal_display_id()
    logging.info("Internal display ID is %s", internal_display_id)
    """Get display orientation value before changing orientation"""
    rotation_before_starts = display_facade.get_display_rotation(internal_display_id)
    logging.info("Rotation before test starts is %d",rotation_before_starts)
    for angle in ROTATIONS:
        logging.info("Rotation to be set %d", angle)
        """changing diplay orientation"""
        display_facade.set_display_rotation(internal_display_id,
                                        angle,
                                        DELAY_BEFORE_ROTATION,
                                        DELAY_AFTER_ROTATION)
        rotation = display_facade.get_display_rotation(internal_display_id)
        logging.info("Internal display rotation is set to %s", rotation)
        if rotation != angle:
            raise error.TestFail('Failed to set %d rotation' % angle)
    """Autotest cleanup method"""
    # If the rotation is not standard then change rotation to standard
    if display_facade:
        if display_facade.get_display_rotation(
            internal_display_id) != STANDARD_ROTATION:
            logging.info("Setting standard rotation")
            display_facade.set_display_rotation(internal_display_id, STANDARD_ROTATION,DELAY_BEFORE_ROTATION, DELAY_AFTER_ROTATION)

def open_status_tray(cr):
    """To get ui elements and open Status tray by clicking on it"""
    ui = ui_utils.UI_Handler()
    ui.start_ui_root(cr)
    logging.info("Opening status tray")
    ui.doDefault_on_obj(STATUS_TRAY_REGEXP, True, role='button')
    list=ui.get_name_role_list()
    return ui

def start_record(cr):
    """Emulate the Keyboard,get ui elements and start screen recording
    @ param cr: Creating Chrome instance
    @ return cr object """
    """Emulate the keyboard    """
    _player = input_playback.InputPlayback()
    _player.emulate(input_type='keyboard')
    _player.find_connected_inputs()
    """To get list of UI elements"""
    ui = ui_utils.UI_Handler()
    ui.start_ui_root(cr)
    list=ui.get_name_role_list()
    """To Open status tray and click on Screen Recording option"""
    logging.info("Opening status tray")
    ui.doDefault_on_obj(STATUS_TRAY_REGEXP, True, role='button')
    time.sleep(WAIT)
    ui.doDefault_on_obj('/Close/i', True, role='button')
    ui.doDefault_on_obj('/Screen capture/i', True, role='button')
    ui.doDefault_on_obj('/Screen record/i', True,role='toggleButton')
    ui.doDefault_on_obj('/Record full screen/i', True,role='toggleButton')
    _player.blocking_playback_of_default_file(input_type='keyboard', filename='keyboard_enter')
    """To open Chrome Page"""
    _player.blocking_playback_of_default_file(input_type='keyboard', filename='keyboard_ctrl+t')
    time.sleep(WAIT)
    logging.info("Recording Started")
    return ui

def stop_record(ui):
    """stop the screen recording to save the file to Downloads
       @ param ui- to get ui objects"""
    # To stop screen recording
    ui.WAIT_for_ui_obj('/Stop screen recording/i', True, role='button')
    ui.doDefault_on_obj('/Stop screen recording/i',True,role='button')
    time.sleep(WAIT)
    logging.info("Recording Stopped")  

def copyFile(source,destination):
    """ To copy a file from source location to destination.
    @ param source - Location of file to be copy from it
    @ param destination - Location of folder into which file need to be copied"""
    logging.info("source",source)
    logging.info("destination",destination)
    try:
        shutil.copy(source, destination)
        logging.info("File copied successfully.")
        """If source and destination are same"""
    except shutil.SameFileError:
        logging.info("File not copied sucessfuly.")
        """List files and directories"""
        logging.info("After copying file:")
        logging.info(os.listdir(destination))
        """logging.info path of newly
        created file"""
        logging.info("Destination path:", destination)

def change_dir(path): 
    """
    To change the present working directory to path given
    @ params path to change current working directory into it
    """   
    os.chdir(path)
