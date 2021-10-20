#!/usr/bin/python3

import logging

import os,time

import subprocess

from autotest_lib.client.bin import test,utils

from autotest_lib.client.common_lib import error

from autotest_lib.client.common_lib.cros import chrome

from autotest_lib.client.cros.networking.chrome_testing import test_utils

from autotest_lib.client.cros.networking.chrome_testing import chrome_networking_test_context as cntc

from autotest_lib.client.cros.enterprise import enterprise_network_api as ena

from autotest_lib.client.cros.networking import wifi_proxy

from autotest_lib.client.cros.networking.chrome_testing import chrome_networking_test_api as cnta

import utils_ts

class ChromeEnterpriseNetworkContext(object):

        SHORT_TIMEOUT = 20

        LONG_TIMEOUT = 120

        def __init__(self, browser=None):

                testing_context = cntc.ChromeNetworkingTestContext()

                testing_context.setup(browser)

                self.chrome_net_context = cnta.ChromeNetworkProvider(testing_context)

                #nws=self.chrome_net_context.get_wifi_networks()

               

                #self.enable_wifi_on_dut()

        def disable_network_device(self, network):

                logging.info('Disabling: %s', network)

                disable_network_result = self.chrome_net_context.\

                _chrome_testing.call_test_function_async(

                    'disableNetworkDevice',

                    '"' + network + '"')

                return True

        def enable_wifi_on_dut(self):

                enabled_devices = self.chrome_net_context.get_enabled_devices()

                if self.chrome_net_context.WIFI_DEVICE not in enabled_devices:

                        self.chrome_net_context.enable_network_device(

                        self.chrome_net_context.WIFI_DEVICE)

                return True

        def enable_network_device(self, network):

                """Enable given network device.

                @param network: string name of the network device to be enabled. Options

                include 'WiFi', 'Cellular' and 'Ethernet'.

                """

                logging.info('Enabling: %s', network)

                enable_network_result = self.chrome_net_context._chrome_testing.call_test_function_async(

                'enableNetworkDevice',

                '"' + network + '"')

                # Allow enough time for the DUT to fully transition into enabled state.

                time.sleep(self.SHORT_TIMEOUT)

                return True

        def get_enabled_devices(self):

 

                enabled_network_types = self.chrome_net_context._chrome_testing.call_test_function(test_utils.LONG_TIMEOUT,'getEnabledNetworkDevices')

                for key, value in enabled_network_types.items():

                        if key == 'result':

                                logging.info('Enabled Network Devices: %s', value)

                                return value

        def check_WiFi_status(self):

                result={}

                result["WiFi-interface"]=''

                enabled_interfaces=self.get_enabled_devices()

                for interface in enabled_interfaces:

                        if interface=="WiFi":

                                pass

                        else:

                                self.enable_network_device("WiFi")               

                result["WiFi-interface"]="enabled"

                return result

        def disconnect_from_network(self,SSID):

                """

                        fun to disconnect from SSID

                        @params SSID name of the Network

                """

                script_path="/usr/local/autotest/cros/scripts"

                # os.chdir() is used to change dir to wifi script path

                change_dir = os.chdir(script_path)

 

                Disconnect_cmd="./wifi disconnect "+ SSID

 

        	get_output=subprocess.Popen(Disconnect_cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE, stderr=subprocess.PIPE,shell=True)

 

                time.sleep(self.SHORT_TIMEOUT)

 

                print("output ",get_output.stderr.readlines())

 

                output_list=get_output.stdout.readlines()

 

                output_list.extend(get_output.stderr.readlines())       

               

                return output_list

        def connect_to_wifi_network(self,SSID,Passphrase,security_mode):

                """

                        fun to use to connect to SSID network

                        @params SSID --name of the network

                        @params Passphrase --password

                        @params security_mode -- security property

                """

                #default path to connect wifi

                script_path="/usr/local/autotest/cros/scripts"

                # os.chdir() is used to change dir to wifi script path

                change_dir = os.chdir(script_path)

 

                #cmd is used to connect to SSID with/without passphrase

                connect_cmd="./wifi connect "+ SSID +" "+Passphrase +" "+ security_mode +" >" + "status.txt"

 

                #Popen then cmd and get th output to validate whether is connected or not

        	get_output=subprocess.Popen(connect_cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE, stderr=subprocess.PIPE,shell=True) 

 

                output_list=get_output.stdout.readlines()

 

                output_list.extend(get_output.stderr.readlines())

 

                return output_list

 

        def validate_output(self,output,string):

                for ele in output:

                        if string in ele:

                                return True

                        else:

                                pass

                return

 

        def check_wlan_ssr(self):

                utils_ts.command_exe('echo enabled > /sys/class/remoteproc/remoteproc0/coredump','/usr/local/autotest/results/default/coredump.txt')

                utils_ts.command_exe('echo assert > /sys/kernel/debug/ath11k/wcn6750\ hw1.0/simulate_fw_crash','/usr/local/autotest/results/default/coredump.txt')

                time.sleep(self.SHORT_TIMEOUT)

        	utils_ts.command_exe('dmesg','/usr/local/autotest/results/default/reset_log.txt')

        	return_status=utils.file_contains_pattern('/usr/local/autotest/results/default/reset_log.txt','0.wifi: pdev 0 successfully recovered')

                if return_status==True:

                        logging.debug('%s',return_status)

                        logging.debug("wlan-ssr reset has been successfully done")

                if return_status==False:

                        raise error.TestFail(" Failed to do Wlan SSR ")

        def verify_url(self,tab, correct_url):

                _WAIT=5

                current_url = tab.url.encode('utf8').rstrip('/')

                utils.poll_for_condition(lambda: current_url == correct_url,exception=error.TestFail('Incorrect navigation: %s'% current_url),timeout=_WAIT)

 

        def bluetooth_ssr(self):

                #subprocess to run the Bluetooth ssr command

                output=subprocess.Popen("hcitool cmd 0x3f 0x0c 0x26",stdin=subprocess.PIPE,stdout=subprocess.PIPE, stderr=subprocess.PIPE,shell=True)

 

                output_list=output.stdout.readlines()

 

                return output_list

        def connect_bluetooth_headset(self,ui,ui_list,BT_Device_name):

                utils_ts.click_UI(ui,ui_list)

 

        def open_multiple_tabs(self,cr,num_of_tabs):

                for new_tab in range(0,num_of_tabs):

                        URL=https://chromium.googlesource.com/

                        tab = cr.browser.tabs[new_tab]

                        self.verify_url(tab,URL)

 
