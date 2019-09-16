#!/usr/bin/env python3
import atexit
import os, time, sys
import json, csv
import readline
import time
import requests
import argparse
import logging
from termcolor import colored
from tabulate import tabulate
import subprocess
import random
import math
import copy

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
        self.core_sw = []
        self.edge_sw = []
        self.allocated_vlanids = []
        self.tagged_switches = []
        self.total_number_of_vm = 0
        self.allocated_vm = 0
        self.vlan_id = 0
        self.vlan_id_list = []
        self.allocated_VLANID = 0
        self.available_vm_per_subnet = 0
        self.total_available_vm = 0
        self.tenant_req = 0
        self.sum_tenant_req = 0
        self.resource_array = list()
        self.vm_array=[]
        self.vn_time_slot = 0
        self.consumption = 0
        self.consumption_full = 100
        self.consumption_threshold = 75
        self.current_rack_number = 0 # Edge switch where current VN is hosting ends
        self.tabular_data = None # This is matrix holding all information
        self.fragmentation = False
        self.tree_path_url='http://127.0.0.1:8282/controller/nb/v3/peregrinedte/getPrimaryTree/'
        self.dbh_internal_url='/usr/local/peregrine-controller/bin/client -u karaf dbh_internal'
        self.peregrine_client_url='/usr/local/peregrine-controller/bin/client -u karaf'

    def build(self):
        self.get_tenant_request()
        pass

    def parse_vm_info(self):
        print(colored('[*] Detailed resource info', 'yellow'))
        for j in range(0, self.number_of_edegesw,1):
            for i in range(0, self.number_of_pm,1):
                if i == 0:
                    tmp = [j+1,self.number_of_pm,self.number_of_vm,i+1,0,0,0, self.number_of_vm]
                    self.resource_array.append(tmp)
                    self.total_number_of_vm = self.total_number_of_vm + self.number_of_vm
                else:
                    tmp = ['','','',i+1,0,0,0,self.number_of_vm]
                    self.resource_array.append(tmp)
                    self.total_number_of_vm = self.total_number_of_vm + self.number_of_vm
            tmp = ['-------', '-------', '-------', '-------', '-------', '-------', '-------', '-------']
            self.resource_array.append(tmp)
        self.tabular_data = (tabulate(self.resource_array, headers=['edge_sw', 'number_of_pm', 'number_of_vm','pm', 'allocated_pm', 'allocated_vms',
                                   'allocated_vlanid', 'available_vm', 'tagged_sw']))
        message='Resource info parsed'
        self.logger.info(message)
        print(self.tabular_data)
        time.sleep(3)
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
            n = random.randint(5,15)
            self.tenant_req = self.tenant_req + int(n)
            self.vm_array.append(int(n))
        self.sum_tenant_req  = sum(self.vm_array)
        time.sleep(1)
        message='Tenant requested : {}'.format( self.vm_array)
        self.logger.info(message)
        time.sleep(1)
        self.greedy_vm_selection()
        # self.get_random_tenant_request()

    def greedy_vm_selection(self):
        message = "Performing greedy search for locating vm"
        self.logger.info(message)
        # do greedy delection algorithm
        # self.vm_array = [14, 8, 13, 3, 5, 15]
        self.vm_array =  [11, 13]
        self.vm_array.sort() # sort tenant request in scending order
        num_edge_sw = math.ceil(sum(self.vm_array)/self.number_of_vm)
        message='Tenant request sorted {} , requires {} PMs and {} VMs'.format(self.vm_array, num_edge_sw, self.sum_tenant_req)
        self.logger.info(message)
        ##### VM allocation

        current_pm = 0
        tmp = []
        for k in range (len(self.vm_array)):
            self.tenant_req = self.vm_array[k]
            for i in range (0, self.number_of_edegesw, 1): # Check for every edge switch
                if self.tenant_req == 0 : # Move to next VN request element if no more VM req in VN
                    break
                for j in range(0,self.number_of_pm,1):   # Check for every physical machine
                    current_pm = i * self.number_of_pm + j + i # Current physical machine
                    if self.resource_array[current_pm][7] != 0: # Only if VM is available for allocation
                        if (self.tenant_req > self.resource_array[current_pm][7]) or (self.tenant_req == self.resource_array[current_pm][7]):
                            tmp_vlan_list = self.resource_array[current_pm][6]
                            if type(tmp_vlan_list) is int:
                                tmp_vlan_list = [tmp_vlan_list]
                            ##['edge_sw', 'number_of_pm', 'number_of_vm','pm','allocated_pm', 'allocated_vms','allocated_vlanids', 'available_vm', 'tagged_switches', 'available vlanids']
                            self.tenant_req = self.tenant_req - self.resource_array[current_pm][7]
                            if j == 0:  # This is just for prety printing
                                self.resource_array[current_pm] = [i+1, self.number_of_pm, self.number_of_vm, j+1, 1,self.number_of_vm, tmp_vlan_list, 0, 0, 0]
                            else:
                                self.resource_array[current_pm] = ['', '', '', j+1, 1,self.number_of_vm, tmp_vlan_list, 0, 0, 0]
                            # self.tenant_req = self.tenant_req - self.resource_array[i][7]
                            if self.tenant_req !=0: # Means VN is fragmented, so we need to get VLAN id
                                if self.fragmentation == True:
                                    tmp_vlan_list = []
                                else:
                                    self.vlan_id = self.vlan_id + 1
                                tmp_vlan_list.append(self.vlan_id)
                                self.resource_array[current_pm][6] = tmp_vlan_list
                            self.fragmentation = True
                        else :
                            ##['edge_sw', 'number_of_pm', 'number_of_vm','pm', 'allocated_pm', 'allocated_vms', 'allocated_vlanids', 'available_vm', 'tagged_switches', 'available vlanids']
                            if self.fragmentation == False:
                                #self.vlan_id_list.append(0)
                                tmp.append(0)
                            else:
                                tmp=list(self.vlan_id_list)
                                tmp.clear()
                                tmp.append(self.vlan_id)
                            if j == 0: # This is just for prety printing
                                self.resource_array[current_pm] = [i+1, self.number_of_pm, self.number_of_vm,j+1, 0, self.resource_array[current_pm][5] + self.tenant_req, tmp,  self.resource_array[current_pm][7] - self.tenant_req,0]
                            else:
                                self.resource_array[current_pm] = ['', '', '',j+1, 0, self.resource_array[current_pm][5] + self.tenant_req, tmp,  self.resource_array[current_pm][7] - self.tenant_req,0]
                            self.tenant_req = 0
                            self.fragmentation = False
                            break
        message='Allocating resources '
        self.logger.info(message)
        self.consumption= self.consumption + (self.sum_tenant_req / (self.number_of_vm*self.number_of_edegesw*self.number_of_pm)) * 100
        message='Resource consumption level :- {} %'.format(self.consumption)
        self.logger.info(message)
        if self.consumption > self.consumption_full:
            message = 'Resource consumption at full capacity'
            self.logger.info(message)
            self.resource_termination() # Exit framework
        if self.consumption > self.consumption_threshold:
            message = 'Resource consumption at threshold level'
            self.logger.info(message)
            self.depart_vn_request() # Random departure of VN
        time.sleep(1)
        self.tabular_data = (tabulate(self.resource_array, headers=['edge_sw', 'number_of_pm', 'number_of_vm', 'pm', 'allocated_vms',
                                   'allocated_vlanids','available_pm', 'available_vm','tagged_switches','available vlanids' ]))
        print(self.tabular_data)
        time.sleep(1)
        self.get_random_tenant_request() # Random input tenant ewquest
        #self.get_tenant_request() # User input tenant ewquest

    def depart_vn_request(self,):
        message='Random removal of VN'
        self.logger.info(message)
        message='VN 3 departed'
        self.logger.info(message)
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
        command=''.join([self.dbh_internal_url,' ','show usrInputSw',' >> sw_list.txt'])
        message='Getting user input Switch info'
        self.logger.info(message)
        out = subprocess.check_output(command, shell=True)
        fh = open("sw_list.txt", "r+")
        lines = fh.readlines()
        num = 0
        for x in lines:
            if "TYPE" or "STATE" in x:
                lines.pop(num)
            num = num + 1
        fh.close()
        fh = open("sw_list.txt", "w")
        lines = filter(lambda x: not x.isspace(), lines)
        fh.write("".join(lines))
        fh.close()
        fh = open("sw_list.txt", "r+")
        lines = fh.readlines()
        num = 0
        for x in lines:
            if "DBH_SW_ROLE_EDGE" in x:
                # print(lines[num+1])
                edge_sw_ip = lines[num + 1]
                edge_sw_ip = edge_sw_ip.split(" ")
                self.edge_sw.append(edge_sw_ip[-1].rstrip('\n'))
            if "DBH_SW_ROLE_CORE" in x:
                # print(lines[num+1])
                core_sw_ip = lines[num + 1]
                core_sw_ip = core_sw_ip.split(" ")
                self.core_sw.append(core_sw_ip[-1].rstrip('\n'))
            num = num + 1
        message='Core switch list - {} '.format(self.core_sw)
        self.logger.info(message)
        message='Edge switch list - {} '.format(self.edge_sw)
        self.logger.info(message)
        fh.close()
        fh = open("sw_list.txt", "w")
        fh.truncate()
        fh.close()
        return  self.core_sw, self.edge_sw

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
        message='Peregrine bundles initiated in Opendaylight'
        self.logger.info(message)
        bundles="'405[[:blank:]]|406[[:blank:]]|407[[:blank:]]|408[[:blank:]]|409[[:blank:]]|410[[:blank:]]|411[[:blank:]]|412[[:blank:]]|413[[:blank:]]|414[[:blank:]]|415[[:blank:]]|425[[:blank:]]|426[[:blank:]]'"
        command=''.join([self.peregrine_client_url,' bundle:list | egrep ', bundles])
        message='Status of bundles :===>>'
        self.logger.info(message)
        os.system(command)

########################################################################################################################
############### Peregrine controller methods ###############
########################################################################################################################

    def goodbye(self):
        print(colored("[*] You are now leaving VLAN ID reuse framework .....", "green"))
        sys.exit(0)

    def vlanid_termination(self):
        print(colored("[*] No more VLAN space availble .....", "green"))
        #self.goodbye()

    def resource_termination(self):
        print(colored("[*] No more resource space availble .....", "green"))
        # self.goodbye()
        sys.exit(0)


if __name__ == '__main__':
        parser = argparse.ArgumentParser(
            description='Process commandline arguments and override configurations')
        parser.add_argument('--log', metavar='[level]', action='store', type=str,
                            required=False, default='debug',
                            help='set the log level: debug, info , warning, error, critical. default = info')

        parser.add_argument('--topo', metavar='[string]', action='store', type=str,
                            required=False, default='spine-leaf',
                            help='set the topology type : spine-leaf, core-spine-leaf, fat tree. default = spine-leaf')

        parser.add_argument('--ToRsw', metavar='[number]', action='store', type=str,
                            required=False, default='4',
                            help='set the ToR switch number. default = 4')

        parser.add_argument('--edege_sw', metavar='[number]', action='store', type=str,
                            required=False, default='8',
                            help='set the edege switch number. default = 8')

        parser.add_argument('--pm', metavar='[number]', action='store', type=str,
                            required=False, default='5',
                            help='set the PM number per switch. default = 5')

        parser.add_argument('--vm', metavar='[number]', action='store', type=str,
                            required=False, default='10',
                            help='set the VM number per PM. default = 10')
        args = parser.parse_args()

        algo = algo_vlan_reuse(args.log, args.ToRsw, args.edege_sw, args.vm, args.pm )

        #algo.initiate_tree_topology()

        algo.parse_vm_info()
        #algo.enable_peregrine_bundles()
        # algo.greedy_vm_selection()

        # algo.get_tenant_request()
        # algo.greedy_vm_selection()
        # algo.terminate()
        #algo.get_random_tenant_request()
        # core_sw,edge_sw=algo.get_user_input_switch()
        # print("core switches ",core_sw)
        # print("edge switches ",edge_sw)