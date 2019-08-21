#!/usr/bin/env python3

import atexit
import os, time, sys
import json, csv
import requests
import argparse
import logging
from termcolor import colored
from tabulate import tabulate
import subprocess
import random

logging.basicConfig(format='%(asctime)s] %(filename)s:%(lineno)d %(levelname)s '
                           '- %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

class algo_vlan_reuse(object):
    def __init__(self, create_topo_log_level=None, ToRsw=None, sw=None, vm=None, pm=None):
        self.logger = logging.getLogger("vnir")
        atexit.register(self.goodbye)  # register a message to print out when exit
        if create_topo_log_level:
            if create_topo_log_level == 'debug':
                self.logger.setLevel(logging.DEBUG)
            elif create_topo_log_level == 'info':
                self.logger.setLevel(logging.INFO)
            elif create_topo_log_level == 'warn':
                self.logger.setLevel(logging.WARNING)
            elif create_topo_log_level == 'error':
                self.logger.setLevel(logging.ERROR)
            elif create_topo_log_level == 'critic':
                self.logger.setLevel(logging.CRITICAL)

        self.number_of_ToRsw = int(ToRsw)
        self.number_of_edegesw = int(sw)
        self.number_of_vm = int(vm)
        self.number_of_pm = int(pm)
        self.total_number_of_vm = 0
        self.allocated_vm = 0
        self.vlan_id_start = 0
        self.allocated_VLANID = 0
        self.available_vm_per_subnet = 0
        self.total_available_vm = 0
        self.tenant_req = 0
        self.resource_array = list()
        self.vm_array=[]
        self.vn_time_slot = 0
        self.tabular_data = None
        self.tree_path_url='http://127.0.0.1:8282/controller/nb/v3/peregrinedte/getPrimaryTree/'
        self.dbh_internal_url='/usr/local/peregrine-controller/bin/client -u karaf dbh_internal'
        self.peregrine_client_url='/usr/local/peregrine-controller/bin/client -u karaf'

    def build(self):
        self.get_tenant_request()
        pass

    def parse_vm_info(self):
        print(colored('[*] Detailed resource info', 'yellow'))
        for i in range(0, self.number_of_edegesw,1):
            tmp = [i+1,self.number_of_pm,self.number_of_vm,0,0,0,self.number_of_pm,self.number_of_vm]
            self.resource_array.append(tmp)
            self.total_number_of_vm = self.total_number_of_vm + self.number_of_vm
        self.tabular_data = (tabulate(self.resource_array, headers=['edge_sw', 'number_of_pm', 'number_of_vm', 'allocated_pm', 'allocated_vms',
                                   'allocated_vlanid', 'available_pm', 'available_vm']))
        message='Resource info parsed'
        self.logger.info(message)
        print(self.tabular_data)
        time.sleep(1)
        # self.get_tenant_request()
        self.get_random_tenant_request() #uniform random distribution

    def initiate_tree_topology(self):
        print(colored('[*] ToRsw = ' + str(self.number_of_ToRsw) + ', edegesw = ' + str(self.number_of_edegesw) + ', pm = ' + str(
            self.number_of_pm * self.number_of_edegesw) + ', vm = ' + str(self.number_of_vm * self.number_of_edegesw), 'cyan'))
        print(colored('So here each PM can host ' + str(int(int(self.number_of_vm) / int(self.number_of_pm))) + ' VMs',
                      'yellow'))
        message = "Make sure mininet cache is cleared and peregrine controller is running"
        self.logger.info(message)
        time.sleep(1)
        if input('Continue [y/n] ') != 'y':
            self.goodbye()
        message = "Running Peregrin Controller"
        self.logger.info(message)
        # ctl_cmd = ''.join(["gnome-terminal"," -e 'sh -c",' "peregrine"',"'"])
        # os.system(ctl_cmd)
        # topo_clr=''.join(["sudo mn -c"])
        # os.system(topo_clr)
        message = "Simulating mininet topology"
        self.logger.info(message)
        topo_cmd = ''.join(["gnome-terminal"," -e 'sh -c ",'"cd ../VLAN_ID_reuse/ && sudo python -E ../VLAN_ID_reuse/SDN_PGS.py  -t topology.json -i host.csv -s 12"',"'"])
        os.system(topo_cmd)
        if input('Continue to parse pm/vm info [y/n] ') == 'y':
            self.parse_vm_info()

    def get_tenant_request(self):
        self.vm_array.clear()
        print(colored('[#] Ready to serve tenants. Press CTRL + C to exit anytime.', 'cyan'))
        number = input(colored("Enter the number of VN : ", 'green'))
        print(colored('Enter number of VM required in each VN : ', 'green'))
        for i in range(int(number)):
            n = input("VN " + str(i + 1) + " : ")
            self.tenant_req = self.tenant_req + int(n)
            self.vm_array.append(int(n))
        print('Tenant requested : ', self.vm_array)
        if self.tenant_req > self.total_number_of_vm:
            print(colored("Excceds the total capacity !! Try Again !!!", 'red'))
            self.get_tenant_request()
        time.sleep(1)
        self.greedy_vm_selection()

    def get_random_tenant_request(self):
        self.vm_array.clear()
        print(colored('[#] Ready to serve tenants. Press CTRL + C to exit anytime.', 'cyan'))
        number = random.randint(1,5)
        # print(colored('Enter number of VM required in each VN : ', 'green'))
        for i in range(int(number)):
            n = random.randint(1,15)
            self.tenant_req = self.tenant_req + int(n)
            self.vm_array.append(int(n))
        self.vn_time_slot = random.randint(20,30)
        message='Tenant requested : {} with time slot duration of {} seconds'.format( self.vm_array, self.vn_time_slot)
        self.logger.info(message)
        self.vm_array.append(self.vn_time_slot)

        #if self.tenant_req > self.total_number_of_vm:
            #print(colored("Excceds the total capacity !! Try Again !!!", 'red'))
            #self.get_random_tenant_request()
            #time.sleep(3)

        time.sleep(3)
        self.greedy_vm_selection()
        # self.get_random_tenant_request()

    def greedy_vm_selection(self):
        message = "Performing greedy search for locating vm"
        self.logger.info(message)
        # do greedy delection algorithm
        # self.vm_array = [7, 10, 12, 5]
        tmp_time_slot=self.vm_array[-1] # get time slot information
        self.vm_array.pop((len(self.vm_array)-1)) # remove time slot information
        for i in range (0, self.number_of_edegesw, 1):
            if self.resource_array[i][7] != 0:
                if (self.tenant_req > self.resource_array[i][7]) or (self.tenant_req == self.resource_array[i][7]):
                    self.resource_array[i] = [i+1, self.number_of_pm, self.number_of_vm, self.number_of_pm, self.number_of_vm, 0, 0, 0,  tmp_time_slot]
                    self.tenant_req = self.tenant_req - self.number_of_vm
                else :
                    self.resource_array[i] = [i+1, self.number_of_pm, self.number_of_vm, 0, self.tenant_req,0, self.number_of_pm, self.number_of_vm - self.tenant_req, 0]
                    self.tenant_req = 0
                    pass
        message='Resource allocated'
        self.logger.info(message)
        time.sleep(1)
        self.tabular_data = (tabulate(self.resource_array, headers=['edge_sw', 'number_of_pm', 'number_of_vm', 'allocated_pm', 'allocated_vms',
                                   'allocated_vlanid', 'available_pm', 'available_vm', 'time_slot_duration']))
        print(self.tabular_data)
        #self.get_tenant_request()
        time.sleep(3)
        self.get_random_tenant_request()

        #self.get_tenant_request()

########################################################################################################################
    ############### Peregrine controller methods ###############
########################################################################################################################
    def get_tree_path(self, vlan_id):
        null = None
        tree_path = []
        tree_path_data = requests.get(self.tree_path_url+'/'+self.vlan_id,auth=('admin','admin'))
        for x in range (len(tree_path_data['bulkRequest'])):
          tree_path.append(tree_path_data['bulkRequest'][x]['tailSwIp'])
        candidate_switch_list=list(dict.fromkeys(tree_path))
        message="Peregrin tree path is "+candidate_switch_list
        self.logger.info(message)
        return candidate_switch_list

    def get_user_input_vlan(self):
        command=''.join([self.dbh_internal_url,' ','show usrInputVLAN'])
        message='Getting user input VLAN info'
        self.logger.info(message)
        out = subprocess.check_output(command, shell=True)
        return out.decode("utf-8")

    def get_user_input_switch(self):
        command=''.join([self.dbh_internal_url,' ','show usrInputSw'])
        message='Getting user input Switch info'
        self.logger.info(message)
        out = subprocess.check_output(command, shell=True)
        return out.decode("utf-8")

    def reset_db(self):
        command = ''.join([self.dbh_internal_url, ' ', 'resetdb'])
        response = os.system(command)

    def add_user_input_vlan(self, switch_ip, vlan_id):
        request = 'http://127.0.0.1:8282/controller/nb/v3/peregrinepm/addUsrInputVLanOnEdgeSw'+'/'+str(vlan_id)+'/'+str(vlan_id)+'/'+str(switch_ip)
        response = requests.put(request,auth=('admin','admin'))
        message='vlan {} added on edge switch {}'.format(vlan_id, switch_ip)
        self.logger.info(message)
    def enable_peregrine_bundles(self):
        bundles='405-415 425 426'
        command=''.join([self.peregrine_client_url,' bundle:start ', bundles])
        os.system(command)
        print(command)

########################################################################################################################
############### Peregrine controller methods ###############
########################################################################################################################

    def goodbye(self):
        print(colored("[*] You are now leaving ITRI's VLAN reuse framework .....", "green"))
        sys.exit(0)

if __name__ == '__main__':
        parser = argparse.ArgumentParser(
            description='Process commandline arguments and override configurations')
        parser.add_argument('--log', metavar='[level]', action='store', type=str,
                            required=False, default='debug',
                            help='set the log level: debug, info (default), warning, error, critical. default = info')

        parser.add_argument('--ToRsw', metavar='[number]', action='store', type=str,
                            required=False, default='4',
                            help='set the ToR switch number. default = 4')

        parser.add_argument('--edege_sw', metavar='[number]', action='store', type=str,
                            required=False, default='8',
                            help='set the edege switch number. default = 8')

        parser.add_argument('--pm', metavar='[number]', action='store', type=str,
                            required=False, default='1',
                            help='set the PM number per switch. default = 1')

        parser.add_argument('--vm', metavar='[number]', action='store', type=str,
                            required=False, default='10',
                            help='set the VM number per PM. default = 10')
        args = parser.parse_args()

        algo = algo_vlan_reuse(args.log, args.ToRsw, args.edege_sw, args.vm, args.pm )

        #algo.initiate_tree_topology()

        #algo.parse_vm_info()
        # algo.greedy_vm_selection()

        # algo.get_tenant_request()
        # algo.greedy_vm_selection()
        algo.enable_peregrine_bundles()
        #algo.get_random_tenant_request()
        #data=algo.get_user_input_switch()
        #print("Here ",data)