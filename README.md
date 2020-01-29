# vlanid-reuse

This work is sponsored by ITRI research program

Algorithm design and validation for efficient vlan id allocation. <br/>

As we know vlan bit in packet header are restricted to 12 bits which leads to 2^12 ~ 4096 VLANS only.
To leverage use of VLAN in network slicing, we need efficient policy to allocate and reuse VLAN. <br/>

Current sorce code allows to use greedy way only but one can use to find globally optimal solution.
