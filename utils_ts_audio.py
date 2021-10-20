# Lint as: python2, python3
# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""
Convenience functions for use by tests or whomever.
"""
# pylint: disable=missing-docstring
from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib import utils
from autotest_lib.client.bin import test
from autotest_lib.client.cros.input_playback import input_playback
from autotest_lib.client.common_lib import ui_utils
from autotest_lib.client.common_lib.cros import chrome
from autotest_lib.client.cros.graphics import graphics_utils
from autotest_lib.client.cros.input_playback import keyboard
from autotest_lib.client.cros.audio import cras_utils
from autotest_lib.client.common_lib.utils import *
from autotest_lib.client.bin import utils_ts
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
WAIT = 10
def get_cras_nodes_cmd():
    """Gets a command to query the nodes from Cras.
    @returns: The command to query nodes information from Cras using dbus-send.
    """
    return ('dbus-send --system --type=method_call --print-reply '
            '--dest=org.chromium.cras /org/chromium/cras '
            'org.chromium.cras.Control.GetNodes') 

def get_cras_nodes():
    """Gets nodes information from Cras.
    @returns: A dict containing information of each node.
    """
    return get_cras_control_interface().GetNodes()

def get_selected_nodes():
    """Gets selected output nodes and input nodes.
    @returns: A tuple (output_nodes, input_nodes) where each
              field is a list of selected node IDs returned from Cras DBus API.
              Note that there may be multiple output/input nodes being selected
              at the same time.
    """
    output_nodes = []
    input_nodes = []
    nodes = get_cras_nodes()
    for node in nodes:
        if node['Active']:
            if node['IsInput']:
                input_nodes.append(node['Id'])
            else:
                output_nodes.append(node['Id'])
    return (output_nodes, input_nodes)

def node_type_is_plugged(node_type, nodes_info):
    """Determine if there is any node of node_type plugged.
    This method is used in the AudioLoopbackDongleLabel class, where the
    call is executed on autotest server. Use get_cras_nodes instead if
    the call can be executed on Cros device.
    Since Cras only reports the plugged node in GetNodes, we can
    parse the return value to see if there is any node with the given type.
    For example, if INTERNAL_MIC is of intereset, the pattern we are
    looking for is:
    dict entry(
       string "Type"
       variant             string "INTERNAL_MIC"
    )
    @param node_type: A str representing node type defined in CRAS_NODE_TYPES.
    @param nodes_info: A str containing output of command get_nodes_cmd.
    @returns: True if there is any node of node_type plugged. False otherwise.
    """
    match = re.search(r'string "Type"\s+variant\s+string "%s"' % node_type,
                      nodes_info)
    return True if match else False
# Cras node types reported from Cras DBus control API.
CRAS_OUTPUT_NODE_TYPES = ['HEADPHONE', 'INTERNAL_SPEAKER', 'HDMI', 'USB',
                          'BLUETOOTH', 'LINEOUT', 'UNKNOWN', 'ALSA_LOOPBACK']
CRAS_INPUT_NODE_TYPES = ['MIC', 'INTERNAL_MIC', 'USB', 'BLUETOOTH',
                         'POST_DSP_LOOPBACK', 'POST_MIX_LOOPBACK', 'UNKNOWN',
                         'KEYBOARD_MIC', 'HOTWORD', 'FRONT_MIC', 'REAR_MIC',
                         'ECHO_REFERENCE']
CRAS_NODE_TYPES = CRAS_OUTPUT_NODE_TYPES + CRAS_INPUT_NODE_TYPES

def get_selected_node_types():
    """Returns the pair of active output node types and input node types.
    @returns: A tuple (output_node_types, input_node_types) where each
              field is a list of selected node types defined in CRAS_NODE_TYPES.
    """
    def is_selected(node):
        """Checks if a node is selected.
        A node is selected if its Active attribute is True.
        @returns: True is a node is selected, False otherwise.
        """
        return node['Active']
    return get_filtered_node_types(is_selected)

def get_plugged_node_types():
    """Returns the pair of plugged output node types and input node types.
    @returns: A tuple (output_node_types, input_node_types) where each
              field is a list of plugged node types defined in CRAS_NODE_TYPES.
    """
    def is_plugged(node):
        """Checks if a node is plugged and is not unknown node.
        Cras DBus API only reports plugged node, so every node reported by Cras
        DBus API is plugged. However, we filter out UNKNOWN node here because
        the existence of unknown node depends on the number of redundant
        playback/record audio device created on audio card. Also, the user of
        Cras will ignore unknown nodes.
        @returns: True if a node is plugged and is not an UNKNOWN node.
        """
        return node['Type'] != 'UNKNOWN'
    return get_filtered_node_types(is_plugged)

def get_filtered_node_types(callback):
    """Returns the pair of filtered output node types and input node types.
    @param callback: A callback function which takes a node as input parameter
                     and filter the node based on its return value.
    @returns: A tuple (output_node_types, input_node_types) where each
              field is a list of node types defined in CRAS_NODE_TYPES,
              and their 'attribute_name' is True.
    """
    output_node_types = []
    input_node_types = []
    nodes = get_cras_nodes()
    for node in nodes:
        if callback(node):
            node_type = str(node['Type'])
            if node_type not in CRAS_NODE_TYPES:
                logging.warning('node type %s is not in known CRAS_NODE_TYPES',
                                node_type)
            if node['IsInput']:
                input_node_types.append(node_type)
            else:
                output_node_types.append(node_type)
    return (output_node_types, input_node_types)

def set_selected_node_types(output_node_types, input_node_types):
    """Sets selected node types.
    @param output_node_types: A list of output node types. None to skip setting.
    @param input_node_types: A list of input node types. None to skip setting.
    """
    if output_node_types is not None and len(output_node_types) == 1:
        set_single_selected_output_node(output_node_types[0])
    elif output_node_types:
        set_selected_output_nodes(output_node_types)
    if input_node_types is not None and len(input_node_types) == 1:
        set_single_selected_input_node(input_node_types[0])
    elif input_node_types:
        set_selected_input_nodes(input_node_types)

def set_single_selected_output_node(node_type):
    """Sets one selected output node.
    Note that Chrome UI uses SetActiveOutputNode of Cras DBus API
    to select one output node.
    @param node_type: A node type.
    @returns: True if the output node type is found and set active.
    """
    nodes = get_cras_nodes()
    for node in nodes:
        if node['IsInput']:
            continue
        if node['Type'] == node_type:
            set_active_output_node(node['Id'])
            return True
    return False

def set_single_selected_input_node(node_type):
    """Sets one selected input node.
    Note that Chrome UI uses SetActiveInputNode of Cras DBus API
    to select one input node.
    @param node_type: A node type.
    @returns: True if the input node type is found and set active.
    """
    nodes = get_cras_nodes()
    for node in nodes:
        if not node['IsInput']:
            continue
        if node['Type'] == node_type:
            set_active_input_node(node['Id'])
            return True
    return False

def set_selected_output_nodes(types):
    """Sets selected output node types.
    Note that Chrome UI uses SetActiveOutputNode of Cras DBus API
    to select one output node. Here we use add/remove active output node
    to support multiple nodes.
    @param types: A list of output node types.
    """
    nodes = get_cras_nodes()
    for node in nodes:
        if node['IsInput']:
            continue
        if node['Type'] in types:
            add_active_output_node(node['Id'])
        elif node['Active']:
            remove_active_output_node(node['Id'])

def set_selected_input_nodes(types):
    """Sets selected input node types.
    Note that Chrome UI uses SetActiveInputNode of Cras DBus API
    to select one input node. Here we use add/remove active input node
    to support multiple nodes.
    @param types: A list of input node types.
    """
    nodes = get_cras_nodes()
    for node in nodes:
        if not node['IsInput']:
            continue
        if node['Type'] in types:
            add_active_input_node(node['Id'])
        elif node['Active']:
            remove_active_input_node(node['Id'])

def set_active_input_node(node_id):
    """Sets one active input node.
    @param node_id: node id.
    """
    get_cras_control_interface().SetActiveInputNode(node_id)

def set_active_output_node(node_id):
    """Sets one active output node.
    @param node_id: node id.
    """
    get_cras_control_interface().SetActiveOutputNode(node_id)

def add_active_output_node(node_id):
    """Adds an active output node.
    @param node_id: node id.
    """
    get_cras_control_interface().AddActiveOutputNode(node_id)

def add_active_input_node(node_id):
    """Adds an active input node.
    @param node_id: node id.
    """
    get_cras_control_interface().AddActiveInputNode(node_id)

def remove_active_output_node(node_id):
    """Removes an active output node.
    @param node_id: node id.
    """
    get_cras_control_interface().RemoveActiveOutputNode(node_id)

def remove_active_input_node(node_id):
    """Removes an active input node.
    @param node_id: node id.
    """
    get_cras_control_interface().RemoveActiveInputNode(node_id)

def get_node_id_from_node_type(node_type, is_input):
    """Gets node id from node type.
    @param types: A node type defined in CRAS_NODE_TYPES.
    @param is_input: True if the node is input. False otherwise.
    @returns: A string for node id.
    @raises: CrasUtilsError: if unique node id can not be found.
    """
    nodes = get_cras_nodes()
    find_ids = []
    for node in nodes:
        if node['Type'] == node_type and node['IsInput'] == is_input:
            find_ids.append(node['Id'])
    if len(find_ids) != 1:
        raise CrasUtilsError(
                'Can not find unique node id from node type %s' % node_type)
    return find_ids[0]

def get_device_id_of(node_id):
    """Gets the device id of the node id.
    The conversion logic is replicated from the CRAS's type definition at
    third_party/adhd/cras/src/common/cras_types.h.
    @param node_id: A string for node id.
    @returns: A string for device id.
    @raise: CrasUtilsError: if device id is invalid.
    """
    device_id = str(int(node_id) >> 32)
    if device_id == "0":
        raise CrasUtilsError('Got invalid device_id: 0')
    return device_id

def get_device_id_from_node_type(node_type, is_input):
    """Gets device id from node type.
    @param types: A node type defined in CRAS_NODE_TYPES.
    @param is_input: True if the node is input. False otherwise.
    @returns: A string for device id.
    """
    node_id = get_node_id_from_node_type(node_type, is_input)
    return get_device_id_of(node_id)

def get_cras_control_interface(private=False):
    """Gets Cras DBus control interface.
    @param private: Set to True to use a new instance for dbus.SystemBus
                    instead of the shared instance.
    @returns: A dBus.Interface object with Cras Control interface.
    @raises: ImportError if this is not called on Cros device.
    """
    try:
        import dbus
    except ImportError as e:
        logging.exception(
                'Can not import dbus: %s. This method should only be '
                'called on Cros device.', e)
        raise
    bus = dbus.SystemBus(private=private)
    cras_object = bus.get_object('org.chromium.cras', '/org/chromium/cras')
    return dbus.Interface(cras_object, 'org.chromium.cras.Control')

def set_system_volume(volume):
    """Set the system volume.
    @param volume: the system output vlume to be set(0 - 100).
    """
    get_cras_control_interface().SetOutputVolume(volume)

def set_node_volume(node_id, volume):
    """Set the volume of the given output node.
    @param node_id: the id of the output node to be set the volume.
    @param volume: the volume to be set(0-100).
    """
    get_cras_control_interface().SetOutputNodeVolume(node_id, volume)

def set_selected_output_node_volume(volume):
    """Sets the selected output node volume.
    @param volume: the volume to be set (0-100).
    """
    selected_output_node_ids, _ = get_selected_nodes()
    for node_id in selected_output_node_ids:
        set_node_volume(node_id, volume)

def get_active_node_volume():
    """Returns volume from active node.
    @returns: int for volume
    @raises: CrasUtilsError: if node volume cannot be found.
    """
    nodes = get_cras_nodes()
    for node in nodes:
        if node['Active'] == 1 and node['IsInput'] == 0:
            return int(node['NodeVolume'])
    raise CrasUtilsError('Cannot find active node volume from nodes.')

def get_selected_output_device_type():
    """Returns the device type of the active output node.
    @returns: device type string. E.g. INTERNAL_SPEAKER
    """
    nodes = get_cras_nodes()
    for node in nodes:
        if node['Active'] and not node['IsInput']:
            return node['Type']
    return None

def get_selected_output_device_type():
    """Returns the device type of the active output node.
    @returns: device type string. E.g. INTERNAL_SPEAKER
    """
    nodes = get_cras_nodes()
    for node in nodes:
        if node['Active'] and not node['IsInput']:
            return node['Type']
    return None

def audio_playback_defaultplayer(cr,Files,test_Files):
    """ Playsback audio file using default audio player.
    @ cr: creating Chrome instance for getting ui elements
    @Files: App name to launch from Launcher and to open Downloads
    @ test_Files: Audio test files to push into device"""
    player1= utils_ts.warmup()
    ui = ui_utils.UI_Handler()
    ui.start_ui_root(cr)
    '''To launch Files App'''
    utils_ts.launch_an_app('Files',ui)
    '''To open Downloads'''
    ui.doDefault_on_obj('Downloads', False, 'treeItem')
    time.sleep(WAIT) 
    '''To Play the Test file'''
    ui.doDefault_on_obj(file, False, 'inlineTextBox')
    player1.blocking_playback_of_default_file(input_type='keyboard', filename='keyboard_enter')
    time.sleep(WAIT)

def default_player_pause_resume(ui):
    """ To pause and resume the audio playback in default audio player
    @ ui : To click on the Pause/Resume ui elemnts"""
    utils_ts.click_UI(ui,([["Pause",False,"button"]]))
    time.sleep(WAIT)
    utils_ts.click_UI(ui,([["Play",False,"button"]]))

def default_player_seek_forward_backward(seek_forward_time,seek_backward_time,ui):
    """To perform Seek operation on Audio file being played in Default player
    @seek_forward_time : Number of clicks that need to performed to Seek audio file forward
    @seek_backward_time : Number of clicks that need to be performed to Seek audio file backward
    @ui : To perform ui clicks on seek forward and seek backward"""
    for forward_time in range(seek_forward_time):
        utils_ts.click_UI(ui,([["Seek slider",False,"slider"]]))
    time.sleep(WAIT)
    _player= utils_ts.warmup()
    for backward_time in range(seek_backward_time):
        _player.blocking_playback_of_default_file(input_type='keyboard', filename='keyboard_down')

def mute_unmute():
    """ To Mute/Unmute the volume during Audio file playback in Default player"""
    '''To set the output node volume to 0'''
    set_selected_output_node_volume(0)
    '''Get the Current Volume'''
    current_volume = get_active_node_volume()
    time.sleep(WAIT)
    if (current_volume==0):
        logging.info("Current volume is set")
    else:
        raise error.TestError("Volume didnt change as expected")
    '''To set the output node volume to 100'''
    set_selected_output_node_volume(100)
    '''Get the Current Volume'''
    current_volume = get_active_node_volume()
    if (current_volume==100):
        logging.info("Current volume is set" )
    else:
        raise error.TestError("Volume didnt change as expected") 

def volume_change(volume):
    """To set thevolume to the required number
    @volume : Volume to set on device;Value Ranges from (0 - 100)"""
    set_selected_output_node_volume(volume)
    current_volume = get_active_node_volume()
    if (volume==current_volume):
        logging.info("Current volume is" ,current_volume)
    else:
        raise error.TestError("Volume didnt change")

def validate_audio_based_on_time_interval(ui_elements):
                time_intv=[]
                for dct1 in ui_elements:
                                for key,value in dct1.items():
                                                logging.info(key,value)
                                                val=value.encode("utf-8")
                                                reg=re.search("\d+.+\d+\s+/+\s+\d+.+\d+",val)
                                                if reg!=None:
                                                                reg=reg.group(0)
                                                                time_intv.append(reg)
                status={}
                logging.info(time_intv)
                ele=time_intv[2]
                time="00:00 / "+re.search('(.+)(?=/)',time_intv[0]).group(0)
                play_time=ele.replace(" ","")
                current_time=re.search('(.+)(?=/)',play_time).group(0)
                if (ele !="00:00 / 00:00") or (ele !=time):
                                var="file played for "+ele+" seconds"
                else:
                                raise error.TestFail("file not played")
                status["status"]=var
                return current_time

def check_audio_playing(ui):
    '''To get the current ui elements'''
                ui_elements=ui.get_name_role_list()
                old_var=validate_audio_based_on_time_interval(ui_elements)
                time.sleep(10)
    '''To get the current ui elements'''
                ui_elements_new=ui.get_name_role_list()
                new_var=validate_audio_based_on_time_interval(ui_elements_new)
                logging.info("audio file time",old_var, new_var)
    '''Compare old player time with new time'''
                if old_var < new_var:
                                logging.info("audio file is being played")
                else:
                                raise error.TestFail("Audio file is not being played")

def close_default_audio_player():
    """To close the default audio player"""
    _player= utils_ts.warmup()
    _player.blocking_playback_of_default_file(input_type='keyboard', filename='keyboard_ctrl+w')

def get_nodeid_from_nodetype():
    """Returns the nodeids of the nodetypes"""
    nodeid_Internal_Speaker = get_node_id_from_node_type('INTERNAL_SPEAKER', False)
    nodeid_Headphone = get_node_id_from_node_type('HEADPHONE', False)
    nodeid_USB = get_node_id_from_node_type('USB', False)
    nodeid_Bluetooth = get_node_id_from_node_type('BLUETOOTH', False)
    return nodeid_Internal_Speaker,nodeid_Headphone,nodeid_USB

def switching_from_speaker_to_other_peripheral(peripheral):
    """ To perform Swithcing from speaker to other peripheral
    @ peripheral : To perform switching between Speaker and Peripheral
    Peripheral - 3.5mm Jack/USB/Bluetooth """
    if peripheral == '3.5mm Jack':
        '''To get the node id of jack'''
        nodeid_Headphone = get_node_id_from_node_type('HEADPHONE', False)
        '''To remove the Headphone as output node'''
        remove_active_output_node(nodeid_Headphone)
        '''Set Speaker as output node'''
        set_selected_output_nodes('INTERNAL_SPEAKER')       
        time.sleep(30)
        '''To get the node id of Internal Speaker'''
        nodeid_Internal_Speaker = get_node_id_from_node_type('INTERNAL_SPEAKER', False)
        '''To remove Internal Speaker as Output node'''
        remove_active_output_node(nodeid_Internal_Speaker)
        '''To set Jack as output node'''       
        set_selected_output_nodes('HEADPHONE')
        time.sleep(10)
         '''Returns the device type of the active output node'''
        current_node = get_selected_output_device_type()      
        if current_node != 'HEADPHONE':
            raise error.TestFail("Device Switch not happened from Speaker to JACK")
            
    if peripheral == 'USB':
        '''To get the node id of USB'''
        nodeid_USB = get_node_id_from_node_type('USB', False)
        '''Set Speaker as output node'''
        set_selected_output_nodes('INTERNAL_SPEAKER')
        time.sleep(10)
        '''To get the node id of Internal Speaker'''
        nodeid_Internal_Speaker = get_node_id_from_node_type('INTERNAL_SPEAKER', False)
        '''To remove Internal Speaker as Output node'''
        remove_active_output_node(nodeid_Internal_Speaker)
        '''Set USB as output node'''
        set_selected_output_nodes('USB')
        time.sleep(10)
        current_node = get_selected_output_device_type()
        '''Returns the device type of the active output node'''
        if current_node != 'USB':
            raise error.TestFail("Device Switch not happened from Speaker to USB")
            
    if peripheral == 'Bluetooth':
        '''To get the node id of USB'''
        nodeid_USB = get_node_id_from_node_type('USB', False)
        '''Set Speaker as output node'''
        set_selected_output_nodes('INTERNAL_SPEAKER')
        time.sleep(10)
        '''To get the node id of Internal Speaker'''
        nodeid_Internal_Speaker = get_node_id_from_node_type('INTERNAL_SPEAKER', False)
        '''To remove Internal Speaker as Output node'''
        remove_active_output_node(nodeid_Internal_Speaker)
        '''Set Bluetooth as output node'''
        set_selected_output_nodes('BLUETOOTH')
        time.sleep(10)
        '''Returns the device type of the active output node'''
        current_status = get_selected_output_device_type()       
        if current_status != 'BLUETOOTH':
            raise error.TestFail("Device Switch not happened from Speaker to Bluetooth")

def switching_from_jack_to_other_peripheral(peripheral):
    """ To perform Swithcing from Jack to other peripheral
    @ peripheral : To perform switching between Jack and Peripheral
    Peripheral - Internal Speaker/USB/Bluetooth """
    if peripheral == 'Internal Speaker':
        '''To get the node id of 3.5mm Jack'''
        nodeid_Headphone = get_node_id_from_node_type('HEADPHONE', False)
        '''To remove 3.5mm Jack as Output node'''
        remove_active_output_node(nodeid_Headphone)
        time.sleep(10)
        '''Set Internal Speaker as output node'''
        set_selected_output_nodes('INTERNAL_SPEAKER')
        time.sleep(10)
        '''Returns the device type of the active output node'''
        current_node = get_selected_output_device_type()
        if current_node != 'INTERNAL_SPEAKER':
            raise error.TestFail("Device Switch not happened between 3.5mm jack and Internal Speaker")
            
    if peripheral == 'USB':
        '''To get the node id of 3.5mm Jack'''
        nodeid_Headphone = get_node_id_from_node_type('HEADPHONE', False)
        '''To remove 3.5mm Jack as Output node'''
        remove_active_output_node(nodeid_Headphone)
        '''Set USB as output node'''
        set_selected_output_nodes('USB')
        time.sleep(10)
        '''Returns the device type of the active output node'''
        current_node = get_selected_output_device_type()
        if current_node != 'USB':
            raise error.TestFail("Device Switch not happened between 3.5mm jack and USB")
            
    if peripheral == 'Bluetooth':
        '''Set 3.5mm Jack as output node'''
        set_selected_output_nodes('HEADPHONE')
        time.sleep(5)  
        '''To get the node id of 3.5mm Jack'''
        nodeid_Headphone = get_node_id_from_node_type('HEADPHONE', False)
        '''To remove 3.5mm Jack as Output node'''
        remove_active_output_node(nodeid_Headphone)
        '''Set Bluetooth as output node'''
        set_selected_output_nodes('BLUETOOTH')
        time.sleep(10)
        '''Returns the device type of the active output node'''
        current_node = get_selected_output_device_type()
        if current_node != 'BLUETOOTH':
            raise error.TestFail("Device Switch not happened between 3.5mm jack and bluetooth")
            
def switching_from_BT_to_other_peripheral(peripheral):
    """ To perform Swithcing from BT to other peripheral
    @ peripheral : To perform switching between BT and Peripheral
    Peripheral - Internal Speaker/USB/3.5mm Jack """
    if peripheral == '3.5mm Jack':
        '''Set Bluetooth as output node'''
        set_selected_output_nodes('BLUETOOTH')
        time.sleep(10)
        '''To get the node id of Bluetooth'''
        nodeid_Bluetooth = get_node_id_from_node_type('BLUETOOTH', False)
        '''To remove Bluetooth as Output node'''
        remove_active_output_node(nodeid_Bluetooth)
        '''Set 3.5mm Jack as output node'''
        set_selected_output_nodes('HEADPHONE')
        time.sleep(10)
        '''Returns the device type of the active output node'''
        current_node = get_selected_output_device_type()
        if current_node != 'HEADPHONE':
            raise error.TestFail("Device Switch not happened from BT Headset to JACK")
            
    if peripheral == 'USB':
        '''Set Bluetooth as output node'''
        set_selected_output_nodes('BLUETOOTH')
        time.sleep(10)
        '''To get the node id of Bluetooth'''
        nodeid_Bluetooth = cras_utils.get_node_id_from_node_type('BLUETOOTH', False)
        '''To remove Bluetooth as Output node'''
        remove_active_output_node(nodeid_Bluetooth)
        '''Set USB as output node'''
        set_selected_output_nodes('USB')
        time.sleep(10)
        '''Returns the device type of the active output node'''
        current_node = get_selected_output_device_type() #Returns the device type of the active output node
        if current_node != 'USB':
            raise error.TestFail("Device Switch not happened from BT Headset to USB")
            
    if peripheral == 'Internal Speaker':
        '''Set Bluetooth as output node'''
        set_selected_output_nodes('BLUETOOTH')
        time.sleep(10)
        '''To get the node id of Bluetooth'''
        nodeid_Bluetooth = get_node_id_from_node_type('BLUETOOTH', False)
        '''To remove Bluetooth as Output node'''
        remove_active_output_node(nodeid_Bluetooth)
        '''Set Internal Speaker as output node'''
        set_selected_output_nodes('INTERNAL_SPEAKER')
        time.sleep(10)
        current_node = cras_utils.get_selected_output_device_type()
        '''Returns the device type of the active output node'''
        if current_node != 'INTERNAL_SPEAKER':
            raise error.TestFail("Device Switch not happened from BT Headset to SPKR")
            
def switching_from_USB_to_other_peripheral(peripheral):
    """ To perform Swithcing from USB to other peripheral
    @ peripheral : To perform switching between USB and Peripheral
    Peripheral - Internal Speaker/Bluetooth/3.5mm Jack """
    if peripheral == 'Internal Speaker':
        '''Set USB as output node'''
        set_selected_output_nodes('USB')
        '''To get the node id of USB'''
        nodeid_USB = get_node_id_from_node_type('USB', False)
        '''To remove USB as Output node'''
        remove_active_output_node(nodeid_USB)
        '''Set Internal Speaker as output node'''
        set_selected_output_nodes('INTERNAL_SPEAKER')
        time.sleep(10)
        current_node = get_selected_output_device_type()
        '''Returns the device type of the active output node'''
        if current_node != 'INTERNAL_SPEAKER':
            raise error.TestFail("Device Switch not happened from USB to speaker")
            
    if peripheral == 'Bluetooth':
        '''Set USB as output node'''
        set_selected_output_nodes('USB')
        time.sleep(10)
        '''To get the node id of USB'''
        nodeid_USB = get_node_id_from_node_type('USB', False)
        '''To remove USB as Output node'''
        remove_active_output_node(nodeid_USB)
        '''Set Internal Speaker as output node'''
        set_selected_output_nodes('BLUETOOTH')
        time.sleep(10)
        current_node = get_selected_output_device_type()
        '''Returns the device type of the active output node'''
        if current_node != 'BLUETOOTH':
            raise error.TestFail("Device Switch not happened from USB to Bluetooth")
            
    if peripheral == '3.5mm Jack':
        '''Set USB as output node'''
        set_selected_output_nodes('USB')
        time.sleep(10)
        '''To get the node id of USB'''
        nodeid_USB = get_node_id_from_node_type('USB', False)
        '''To remove USB as Output node'''
        remove_active_output_node(nodeid_USB)
        '''Set Internal Speaker as output node'''
        set_selected_output_nodes('HEADPHONE')
        time.sleep(10)
        current_node = get_selected_output_device_type()
        '''Returns the device type of the active output node'''
        if current_node != 'HEADPHONE':
            raise error.TestFail("Device Switch not happened from USB to Jack")

def connect_bluetooth_headset(ui,name_bt_headset):
    utils_ts.click_UI(ui,([["/Status tray, /i",True,"button"],["Show Bluetooth settings. Bluetooth is on",False,"button"],[name_bt_headset,False,"button"]]))

def audio_playback_browser(tab, test_file):
    """Plays a media file in Chromium.
    @param test_file: Media file to test.
    @param vlaue: Index of the loop
    """
    tab.EvaluateJavaScript('play("%s")' % test_file)
    def get_current_time():
        return tab.EvaluateJavaScript('player.currentTime')
    '''Make sure the audio is being played'''
    old_time = get_current_time()
    utils.poll_for_condition(condition=lambda: get_current_time() > old_time,exception=error.TestError('Player never start until timeout.'))
    tab.EvaluateJavaScript('player.currentTime = %d' % get_current_time())

def browser_player_pause_resume():
     """ To pause and resume the audio playback in default audio player
    @ ui : To click on the Pause/Resume ui elemnts"""
    utils_ts.click_UI(ui,([["Pause",False,"button"]]))
    time.sleep(WAIT)
    utils_ts.click_UI(ui,([["play",False,"button"]]))