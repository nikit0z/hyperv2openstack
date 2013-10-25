!!! This software is provided "as is", without warranty of any kind.

!!! Be sure you've backed up your vhd images before running this script.

WTF?
----

This is the tool to convert hyper-v VMs to "openstack ready" VMs. By "converting" I mean installing VirtIO drivers into a vhd image of a VM. Linux supports virtio by default so basically this thing is for Windows VMs

Requirements
------------
General:

* Hyper-V VM xml file
* Hyper-V VM vhd file
* python

For Windows VMs:

* virt-inspector
* guestfish
* virt-win-reg
* hivexget
* virtio drivers iso


Examples
--------
```hyperv2openstack.py --xml /home/hyper-v/xml/vm.xml --vhd_dir /home/hyper-v/vhd/ --iso /home/hyper-v/virtio-win-0.1-65.iso```