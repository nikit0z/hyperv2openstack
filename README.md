!!! This software is provided "as is", without warranty of any kind.

!!! Be sure you've backed up your vhd images before running this script.

WTF?
----

This is the tool to convert hyper-v VMs to "openstack ready" VMs. By "converting" I mean installing VirtIO drivers into a vhd image of a VM. Linux supports virtio by default so basically this thing is for Windows VMs.
Ideas was taken from great redhat virt-v2v tool.

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
* virtio drivers iso (0.1.52+)


Examples
--------
Single VM:
```
./h2o.py --xml /home/hyper-v/xml/vm.xml --vhd_dir /home/hyper-v/vhd/ \
--iso /home/hyper-v/virtio-win-0.1-65.iso
```


Many VMs:
```
for i in `find /home/hyper-v/xml/ -name '*.xml'`; \
do ./h2o.py --xml $i --vhd_dir /home/hyper-v/vhd/ \
--iso /home/hyper-v/virtio-win-0.1-65.iso ; done
```
