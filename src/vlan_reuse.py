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
        self.core_switch = [] # Best core switch by peregrine
        self.allocated_vlanids = []
        self.tagged_switches = []
        self.total_number_of_vm = 0
        self.allocated_vm = 0
        self.vlan_id = 0
        self.fake_vlan_id = 110
        self.vlan_id_list = []
        self.allocated_VLANID = 0
        self.available_vm_per_subnet = 0
        self.total_available_vm = 0
        self.tenant_req = 0
        self.sum_tenant_req = 0
        self.resource_array = list()
        self.vlanid_map = list()
        self.tenant_map = list()
        self.vm_array=[]
        self.consumption = 0
        self.consumption_full = 100
        self.consumption_threshold = 75
        self.current_rack_number = 0 # Edge switch where current VN is hosting ends
        self.tabular_data = None # This is matrix holding all information
        self.fragmentation = False

        # Enable following features
        self.vlan_id_reuse = False
        self.resource_utilization_full = False
        self.vn_departure = False # If true then tenant will depart randomly at threshold resource utilization
        self.manual_mode_tenant_req = False  # If true then tenant request is user input else randomly generated

        self.total_tenants = 0
        self.vlan_id_threshold = 20
        self.vlan_set_a = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20]
        self.tree_path_url='http://127.0.0.1:8282/controller/nb/v3/peregrinedte/getPrimaryTree/'
        self.dbh_internal_url='/usr/local/peregrine-controller/bin/client -u karaf dbh_internal'
        self.peregrine_client_url='/usr/local/peregrine-controller/bin/client -u karaf'

    def build(self):
        map = ['switch_id', 'used_vlan_id', 'available_vlan_id']
        init = [0,0,0]
        for i in range(0,12,1):
            init = [i+1,0,0]
            self.vlanid_map.append(init)
        self.tabular_vlanid_map_data = (tabulate(self.vlanid_map,
                                      headers=['switch_id', 'used_vlan_id', 'available_vlan_id']))

        for i in range(0,100,1):
            init = [i + 1, 0, 0, 0, 0, 0]
            self.tenant_map.append(init)
        self.tabular_tenant_map_data = (tabulate(self.tenant_map,
                                             headers=['vn_number', 'total_vms', 'edge_sw', 'pm', 'machine_number', 'vlan_ids']))


    def parse_vm_info(self):
        print(colored('[*] Detailed resource info', 'yellow'))
        for j in range(0, self.number_of_edegesw,1):
            for i in range(0, self.number_of_pm,1):
                if i == 0: # This is just for prety printing
                    tmp = [1+j+self.number_of_ToRsw,self.number_of_pm,self.number_of_vm,i+1,0,0,0, self.number_of_vm,0]
                    self.resource_array.append(tmp)
                    self.total_number_of_vm = self.total_number_of_vm + self.number_of_vm
                else: # This is just for prety printing
                    tmp = ['','','',i+1,0,0,0,self.number_of_vm,0]
                    self.resource_array.append(tmp)
                    self.total_number_of_vm = self.total_number_of_vm + self.number_of_vm
            tmp = ['-------', '-------', '-------', '-------', '-------', '-------', '-------', '-------']
            self.resource_array.append(tmp)
        self.tabular_data = (tabulate(self.resource_array, headers=['edge_sw', 'number_of_pm', 'number_of_vm','pm', 'allocated_pm', 'allocated_vms',
                                   'allocated_vlanid', 'available_vm', 'tagged_core_sw']))
        message='Resource info parsed'
        self.logger.info(message)
        print(self.tabular_data)
        time.sleep(3)
        if self.manual_mode_tenant_req == True:
            self.get_tenant_request()
        else:
            self.get_random_tenant_request() # uniform random distribution

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
            self.resource_utilization_full = True
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
        self.vm_array.sort() # sort tenant request in scending order
        num_edge_sw = math.ceil(sum(self.vm_array)/self.number_of_vm)

        message='Tenant request sorted {} , requires {} PMs and {} VMs'.format(self.vm_array, num_edge_sw, self.sum_tenant_req)
        self.logger.info(message)
        ##### VM allocation

        current_pm = 0
        tagged_switches = 0
        tmp = []
        candidate = []
        for k in range (len(self.vm_array)):
            self.tenant_req = self.vm_array[k]

            self.tenant_map[self.total_tenants][1] = self.tenant_req
            self.total_tenants = self.total_tenants + 1

            for i in range (0, self.number_of_edegesw, 1): # Check for every edge switch
                if self.tenant_req == 0:  # Move to next VN request element if no more VM req in VN
                    break
                for j in range(0,self.number_of_pm,1): # Check for every physical machine
                    current_pm = i * self.number_of_pm + j + i # Current physical machine
                    if self.resource_array[current_pm][7] != 0: # Only if VM is available for allocation

                        self.update_vn_map('edge_sw', 1+i+self.number_of_ToRsw)
                        self.update_vn_map('pm',j+1)

                        if (self.tenant_req > self.resource_array[current_pm][7]) or (self.tenant_req == self.resource_array[current_pm][7]):

                            self.update_vn_map('machine_number', self.number_of_vm - self.resource_array[current_pm][7] + 1)

                            tmp_vlan_list = self.resource_array[current_pm][6]
                            if type(tmp_vlan_list) is int:
                                tmp_vlan_list = []

                            ##['edge_sw', 'number_of_pm', 'number_of_vm','pm','allocated_pm', 'allocated_vms','allocated_vlanids', 'available_vm', 'tagged_switches', 'available vlanids']
                            self.tenant_req = self.tenant_req - self.resource_array[current_pm][7]
                            if j == 0:  # This is just for prety printing
                                if type(self.resource_array[current_pm][6]) is list:
                                    #self.resource_array[current_pm] = [1+i+self.number_of_ToRsw, self.number_of_pm, self.number_of_vm, j+1, 1,self.number_of_vm, tmp_vlan_list, 0, self.core_switch,0]
                                    self.resource_array[current_pm] = [1+i+self.number_of_ToRsw, self.number_of_pm, self.number_of_vm, j+1, 1,self.number_of_vm, tmp_vlan_list, 0, tagged_switches, 0]
                                else:
                                    self.resource_array[current_pm] = [1+i+self.number_of_ToRsw, self.number_of_pm, self.number_of_vm, j+1, 1,self.number_of_vm, tmp_vlan_list, 0, tagged_switches, 0]
                            if j != 0: # This is just for prety printing
                                self.resource_array[current_pm] = ['', '', '', j+1, 1,self.number_of_vm, tmp_vlan_list, 0, tagged_switches, 0]
                            # self.tenant_req = self.tenant_req - self.resource_array[i][7]
                            if self.tenant_req !=0: # Means VN is fragmented, so we need to get VLAN id
                                if self.fragmentation == True:
                                    tmp_vlan_list = []
                                else:
                                    self.vlan_id = self.vlan_id + 1
                                    if  self.vlan_id > self.vlan_id_threshold + 1 or self.vlan_id_reuse ==  True:
                                        message = 'vlan id threshould reached, reusing available vlan ids'
                                        self.logger.info(message)
                                        candidate = self.get_reuse_vlanid(1+i+self.number_of_ToRsw)
                                        if type(self.vlanid_map[i+self.number_of_ToRsw][2]) is not int:
                                            candidate = list(set(candidate)-set(self.vlanid_map[i+self.number_of_ToRsw][1]))
                                        # self.vlan_id = random.choice(candidate) # collision hoga idhar
                                        candidate = random.choice(candidate)
                                        self.vlan_id = candidate # collision hoga idhar
                                        self.vlan_id_reuse = True

                                tmp_vlan_list.append(self.vlan_id)
                                self.add_vlan_id_to_map(1+i+self.number_of_ToRsw, self.vlan_id)
                                self.resource_array[current_pm][6] = tmp_vlan_list # refer to similar object, this step may not required or need to be rectified
                                self.fragmentation = True

                                self.update_vn_map('vlan_id', self.vlan_id)

                            if  self.tenant_req == 0: # Means VN is not fragmented
                                if self.fragmentation == False:
                                    tmp_vlan_list.append(0)
                                    self.update_vn_map('vlan_id', 123)
                                else:
                                    self.fragmentation = False
                                    tmp_vlan_list.clear()
                                    tmp_vlan_list.append(self.vlan_id)
                                self.resource_array[current_pm][6] = tmp_vlan_list
                                break

                            if self.fragmentation == True and j==4 and i !=self.number_of_edegesw-1 :
                                message='Here is a fragmentation across multiple edege switches, getting peregrine tree path'
                                self.logger.info(message)
                                self.core_switch=self.get_best_tree_path(1+i+self.number_of_ToRsw,2+i+self.number_of_ToRsw)
                                self.resource_array[current_pm][8] = self.core_switch
                                self.add_vlan_id_to_map(self.core_switch[0], self.vlan_id)

                                # Get peregrine tree path
                        #if self.tenant_req < self.resource_array[current_pm][7]:
                        else:
                            self.update_vn_map('machine_number', self.number_of_vm - self.resource_array[current_pm][7] + 1)


                            if self.fragmentation == False:
                                if type(self.resource_array[current_pm][6]) is list:
                                    tmp=self.resource_array[current_pm][6]
                                tmp.append(0)
                            if self.fragmentation == True:
                                tmp=list(self.vlan_id_list)
                                tmp.clear()
                                tmp.append(self.vlan_id)
                            if j == 0: # This is just for prety printing
                                if self.fragmentation == True:
                                    ##['edge_sw', 'number_of_pm', 'number_of_vm','pm', 'allocated_pm', 'allocated_vms', 'allocated_vlanids', 'available_vm', 'tagged_switches', 'available vlanids']
                                    self.resource_array[current_pm] = [1+i+self.number_of_ToRsw, self.number_of_pm, self.number_of_vm,j+1, 0, self.resource_array[current_pm][5] + self.tenant_req, tmp,  self.resource_array[current_pm][7] - self.tenant_req, self.core_switch, 0]
                                else:
                                   # self.resource_array[current_pm] = [1+i+self.number_of_ToRsw, self.number_of_pm, self.number_of_vm, j+1, 0, self.resource_array[current_pm][5] + self.tenant_req, tmp,  self.resource_array[current_pm][7] - self.tenant_req, self.core_switch, 0]
                                    self.resource_array[current_pm] = [1+i+self.number_of_ToRsw, self.number_of_pm, self.number_of_vm, j+1, 0, self.resource_array[current_pm][5] + self.tenant_req, tmp,  self.resource_array[current_pm][7] - self.tenant_req, 0, 0]
                            else:
                                self.resource_array[current_pm] = ['', '', '',j+1, 0, self.resource_array[current_pm][5] + self.tenant_req, tmp,  self.resource_array[current_pm][7] - self.tenant_req,0,0]

                            self.tenant_req = 0
                            self.fragmentation = False

                            self.update_vn_map('vlan_id', 123)

                            break
        message='Allocating resources '
        self.logger.info(message)

        time.sleep(1)
        self.tabular_data = (tabulate(self.resource_array, headers=['edge_sw', 'number_of_pm', 'number_of_vm', 'pm', 'allocated_pms',
                                   'allocated_vm','allocated_vlanids', 'available_vm','tagged_core_switches','available vlanids' ]))
        print(self.tabular_data)
        time.sleep(1)

        self.consumption= self.consumption + (self.sum_tenant_req / (self.number_of_vm*self.number_of_edegesw*self.number_of_pm)) * 100
        message='Resource consumption level :- {} %'.format(self.consumption)
        self.logger.info(message)
        if self.consumption > self.consumption_full:
            message = 'Resource consumption at full capacity'
            self.logger.info(message)
            self.resource_termination() # Exit framework
        if self.consumption > self.consumption_threshold and self.vn_departure == True:
            message = 'Resource consumption at threshold level'
            self.logger.info(message)
            self.depart_vn_request() # Random departure of VN

        if self.manual_mode_tenant_req == True:
            self.get_tenant_request()
        else:
            self.get_random_tenant_request() # uniform random distribution

    def update_vn_map(self, type, arg):
        if self.resource_utilization_full == False:
            if type == 'edge_sw' and self.tenant_map[self.total_tenants - 1][2] == 0:
                self.tenant_map[self.total_tenants - 1][2] = arg

            elif type == 'pm' and self.tenant_map[self.total_tenants - 1][3] == 0:
                self.tenant_map[self.total_tenants - 1][3] = arg

            elif type == 'machine_number' and self.tenant_map[self.total_tenants - 1][4] == 0:
                self.tenant_map[self.total_tenants - 1][4] = arg

            elif type == 'vlan_id' and self.tenant_map[self.total_tenants - 1][5] == 0:
                self.tenant_map[self.total_tenants - 1][5] = arg



    def get_reuse_vlanid(self, switch_number):
        final_list = self.vlan_set_a
        #for i in range(0,switch_number,1):
        for i in range(0,6,1):
            if type(self.vlanid_map[i][2]) is not list:
                pass
            else:
                final_list = list(set(final_list).intersection(self.vlanid_map[i][2]))
        return final_list

    def add_vlan_id_to_map(self, switch_number, vlan_id):
        if type(self.vlanid_map[switch_number-1][1]) is int:
            self.vlanid_map[switch_number-1][1]=[]
        self.vlanid_map[switch_number-1][1].append(vlan_id)
        data = list(dict.fromkeys(self.vlanid_map[switch_number-1][1]))
        data.sort()
        self.vlanid_map[switch_number-1][1] = data
        self.vlanid_map[switch_number-1][2] = list(set(self.vlan_set_a)-set(data))

    def depart_vn_request(self,):
        random_vn_index = []
        # for i in range(1,6,1):
        for i in range(0,2,1):
            random_vn_index.append(random.randint(1,self.total_tenants))
        # print(self.total_tenants)
        message='Total number of VN served now :- {}'.format(self.total_tenants)
        self.logger.info(message)

        message='Random removal of VN'
        self.logger.info(message)

        tmp_core_sw = 0
        for i in range(0,2,1):
            vn_number = random_vn_index[i]
            total_vm = self.tenant_map[vn_number - 1][1]
            if total_vm == 0:
                break
            edge_sw = self.tenant_map[vn_number-1][2]
            pm = self.tenant_map[vn_number-1][3]
            vm_number = self.tenant_map[vn_number-1][4]
            vlan_id = self.tenant_map[vn_number-1][5]
            resource_array_index = (self.number_of_pm+1) * (edge_sw-self.number_of_pm) + pm-1
            # print(self.resource_array[resource_array_index][6])
            if vlan_id == 123:
                # Step 1 update resource array
                self.resource_array[resource_array_index][5] = self.number_of_vm - total_vm # allocated vm
                self.resource_array[resource_array_index][7] = total_vm # available vm
                list_tmp=self.resource_array[resource_array_index][6]
                list_tmp.remove(0) # refering to same object
                self.resource_array[resource_array_index][6] = list_tmp # vlan id


                # Step 2 update vn map
                self.tenant_map[vn_number-1] = [0,0,0,0,0,0]

                # Step 3 update vlanid map
                # No need to update since its 0 vlan id, which in ignored in the map

                # Step 4 update resource consumption level
                self.consumption = self.consumption - (total_vm / (
                            self.number_of_vm * self.number_of_edegesw * self.number_of_pm)) * 100
                message = 'Resource consumption level after VN {} ({} vms) departure:- {} %'.format(vn_number,total_vm, self.consumption)
                self.logger.info(message)

            else:
                # Step 4 update resource consumption level
                # self.consumption = self.consumption - (total_vm / (
                #             self.number_of_vm * self.number_of_edegesw * self.number_of_pm)) * 100

                for j in range(0,3,1):
                    if total_vm == 0:
                        break
                    # Step 1 update resource array
                    if j==0:
                        self.consumption = self.consumption - (total_vm / (
                                self.number_of_vm * self.number_of_edegesw * self.number_of_pm)) * 100
                        message1 = 'Resource consumption level after VN {} ({} vms) departure:- {} %'.format(vn_number,total_vm, self.consumption)

                        if type(self.resource_array[resource_array_index + j][8]) is list:
                            tmp_core_sw = self.resource_array[resource_array_index + j][8][0]
                        vms = self.number_of_vm - vm_number
                        self.resource_array[resource_array_index + j][5] = self.number_of_vm - vms  # allocated vm
                        list_tmp = self.resource_array[resource_array_index + j][6]
                        list_tmp.remove(vlan_id)
                        self.resource_array[resource_array_index + j][6] = list_tmp
                        self.resource_array[resource_array_index + j][7] = vms  # available vm
                        total_vm = total_vm - vms
                    else:
                        if type(self.resource_array[resource_array_index + j][8]) is list:
                            tmp_core_sw = self.resource_array[resource_array_index + j][8]
                            tmp_core_sw = tmp_core_sw[0]
                        if total_vm == 0:
                            break

                        if total_vm > self.resource_array[resource_array_index + j][5] or total_vm == self.resource_array[resource_array_index + j][5]:
                            self.resource_array[resource_array_index + j][5] = 0 # allocated vm
                            list_tmp = self.resource_array[resource_array_index+j][6]
                            list_tmp.remove(vlan_id)
                            self.resource_array[resource_array_index+j][6] = list_tmp
                            self.resource_array[resource_array_index+j][7] =  self.number_of_vm # available vm
                            total_vm = total_vm - self.number_of_vm
                        else:
                            self.resource_array[resource_array_index + j][5] = self.number_of_vm - total_vm
                            list_tmp = self.resource_array[resource_array_index+j][6]
                            list_tmp.remove(vlan_id)
                            self.resource_array[resource_array_index+j][6] = list_tmp
                            self.resource_array[resource_array_index+j][7] = total_vm # available vm
                            total_vm =0
                # Step 2 update vn map
                self.tenant_map[vn_number] = [0, 0, 0, 0, 0, 0]
                # Step 3 update vlanid map
                tmp1 = self.vlanid_map[edge_sw-1][1]
                tmp1.remove(vlan_id)
                self.vlanid_map[edge_sw - 1][1] = tmp1

                tmp2 = self.vlanid_map[edge_sw-1][2]
                tmp2.append(vlan_id)
                self.vlanid_map[edge_sw - 1][2] = tmp2

                if tmp_core_sw != 0:
                    tmp_list = self.resource_array[resource_array_index + j][6]
                    if len(tmp_list) ==0: # if core switch is tagged with this vlan id
                        tmp1 = self.vlanid_map[tmp_core_sw - 1][1]
                        tmp1.remove(vlan_id)
                        self.vlanid_map[tmp_core_sw - 1][1] = tmp1

                        tmp2 = self.vlanid_map[tmp_core_sw - 1][2]
                        tmp2.append(vlan_id)
                        self.vlanid_map[tmp_core_sw - 1][2] = tmp2

                # Step 4 update resource consumption level
                message = 'VN {} departed'.format(random_vn_index)
                self.logger.info(message)

                # message1 = 'Resource consumption level after VN {} departure:- {} %'.format(vn_number, self.consumption)
                self.logger.info(message1)

        time.sleep(1)
        self.tabular_data = (tabulate(self.resource_array, headers=['edge_sw', 'number_of_pm', 'number_of_vm', 'pm', 'allocated_pms',
                                   'allocated_vm','allocated_vlanids', 'available_vm','tagged_core_switches','available vlanids' ]))
        print(self.tabular_data)
        # print('wait here')


########################################################################################################################
    ############### Peregrine controller methods ###############
########################################################################################################################
    def get_best_tree_path(self,a,b):
        edge_switch_1='172.0.0.'+str(a)
        edge_switch_2='172.0.0.'+str(b)
        switch_list = []
        candidate_sw = []
        self.fake_vlan_id = self.fake_vlan_id +1
        candidate_sw.clear()
        for i in range (1,self.number_of_ToRsw,1):
            self.add_user_input_vlan(edge_switch_1,self.fake_vlan_id)
            self.add_user_input_vlan(edge_switch_2,self.fake_vlan_id)
            self.calPrimaryTree()
            candidate_sw = self.get_tree_path(self.fake_vlan_id)
            candidate_sw.remove(edge_switch_1)
            candidate_sw.remove(edge_switch_2)
            switch_list.append(candidate_sw[0])
            self.fake_vlan_id = self.fake_vlan_id + 1
            candidate_sw.clear()
        final_switch=random.choice(switch_list)
        final_switch=[int((list(final_switch))[-1])]
        message='Candidate core switch from peregrine tree path is '+str(final_switch)
        self.logger.info(message)
        return final_switch

    def calPrimaryTree(self):
        request=self.peregrine_client_url+' dte calPrimaryTree glb'
        os.system(request)

    def get_tree_path(self, vlan_id):
        null = None
        tree_path = []
        candidate_switch_list = []
        req = self.tree_path_url+str(vlan_id)+' | jq .'
        #tree_path_data = requests.get(req, auth=('admin','admin'))
        req1="curl -Ss -X GET -H 'Accept: application/json' --user admin:admin http://127.0.0.1:8282/controller/nb/v3/peregrinedte/getPrimaryTree/"+str(vlan_id)+' | jq .'
        tree_path_data = os.popen(req1).read()
        tree_path_data = json.loads(tree_path_data)
        tree_path.clear()

        for x in range (len(tree_path_data['bulkRequest'])):
          tree_path.append(tree_path_data['bulkRequest'][x]['tailSwIp'])
        candidate_switch_list=list(dict.fromkeys(tree_path))
        message="Peregrin tree path is "+str(candidate_switch_list)
        self.logger.info(message)
        tree_path.clear()
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
        request = 'http://127.0.0.1:8282/controller/nb/v3/peregrinepm/addUsrInputVLanOnEdgeSw'+'/'+str(vlan_id)+'/'+str(vlan_id)+'/'+str(switch_ip)+'/5'
        response = requests.put(request,auth=('admin','admin'))
        message='Fake vlan {} added on edge switch {}'.format(vlan_id, switch_ip)
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

        time.sleep(1)
        message = 'Switch vlan id consumption information'
        self.logger.debug(message)

        self.tabular_vlanid_map_data = (tabulate(self.vlanid_map,
                                      headers=['switch_id', 'used_vlan_id', 'available_vlan_id']))
        print(self.tabular_vlanid_map_data)
        time.sleep(1)
        message = 'All VN hosting information'
        self.logger.debug(message)
        self.tabular_tenant_map_data = (tabulate(self.tenant_map,
                                             headers=['vn_index', 'total_vms', 'edge_sw', 'pm', 'machine_number', 'vlan_ids']))
        print(self.tabular_tenant_map_data)

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
                            required=False, default='15',
                            help='set the ToR switch number. default = 15')

        parser.add_argument('--edege_sw', metavar='[number]', action='store', type=str,
                            required=False, default='20',
                            help='set the edege switch number. default = 20')

        parser.add_argument('--pm', metavar='[number]', action='store', type=str,
                            required=False, default='5',
                            help='set the PM number per switch. default = 5')

        parser.add_argument('--vm', metavar='[number]', action='store', type=str,
                            required=False, default='10',
                            help='set the VM number per PM. default = 10')
        args = parser.parse_args()

        algo = algo_vlan_reuse(args.log, args.ToRsw, args.edege_sw, args.vm, args.pm )
        algo.build()
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
        #print("edge switches ",edge_sw)

        # a='172.0.0.5'
        # b='172.0.0.6'
        # algo.add_user_input_vlan(a,'105')
        # algo.add_user_input_vlan(b,'105')

        # algo.calPrimaryTree()
        # res = algo.get_tree_path(111)
        #
        # print(res)
        # print((set(res)- set(core_sw)))