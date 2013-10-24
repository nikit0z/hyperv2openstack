#!/usr/bin/env python

import sys
import argparse
import re
import xml.etree.ElementTree as ET
import ntpath
import subprocess
import os
import distutils.spawn 

def check_req_tools(req_tools):
    for tool in req_tools:
            if distutils.spawn.find_executable(tool) is None:
                err_msg = tool +  " is not installed or not in PATH"
                sys.exit(err_msg)

def parse_xml():
    xmlpath = args.xml
    xmltree = ET.parse(xmlpath)

    return xmltree


def get_vm_params():
    xmltree = parse_xml()
    xmlroot = xmltree.getroot()
    vhd_name = get_vhd_name(xmlroot)
    vm_os_ver, vm_os_arch = get_vm_os_ver(vhd_name)

    return (get_vm_name(xmlroot), get_vm_cpu_count(xmlroot), get_vm_ram_limit(xmlroot), vhd_name, vm_os_ver, vm_os_arch)


def get_vm_name(xmlroot):
    return xmlroot.find('./properties/name').text


def get_vm_cpu_count(xmlroot):
    return xmlroot.find('./settings/processors/count').text


def get_vm_ram_limit(xmlroot):
    return xmlroot.find('./settings/memory/bank/limit').text


def get_vhd_name(xmlroot):
    vhd_re = re.compile(r".*vhd$")

    # dont like
    for pathname in xmlroot.iter(tag='pathname'):
        if vhd_re.match(pathname.text):
            vhd_name = ntpath.basename(pathname.text)
            if os.path.exists(vhd_name):
                return vhd_name
            else:
                err_msg = "Can't find vhd file vhd_name"
                sys.exit(err_msg)
            break


def get_vm_os_ver(vhd_name):
    try:
        vhd_info = subprocess.check_output(['virt-inspector', vhd_name], stderr=open(os.devnull, 'wb'))
        xmltree = ET.fromstring(vhd_info)
        return (xmltree.find('./operatingsystem/product_name').text, xmltree.find('./operatingsystem/arch').text)
    except:
        raise

def merge_reg_changes(vhd_name):
    reg_changes = '''
[HKEY_LOCAL_MACHINE\SYSTEM\ControlSet001\Services\viostor]
"Group"="SCSI miniport"
"ImagePath"=hex(2):73,00,79,00,73,00,74,00,65,00,6d,00,33,00,32,00,5c,00,64,\
  00,72,00,69,00,76,00,65,00,72,00,73,00,5c,00,76,00,69,00,6f,00,73,00,74,00,6f,\
  00,72,00,2e,00,73,00,79,00,73,00,00,00
"ErrorControl"=dword:00000001
"Start"=dword:00000000
"Type"=dword:00000001
"Tag"=dword:00000040

[HKEY_LOCAL_MACHINE\SYSTEM\ControlSet001\Services\viostor\Parameters]
"BusType"=dword:00000001

[HKEY_LOCAL_MACHINE\SYSTEM\ControlSet001\Services\viostor\Parameters\MaxTransferSize]
"ParamDesc"="Maximum Transfer Size"
"type"="enum"
"default"="0"

[HKEY_LOCAL_MACHINE\SYSTEM\ControlSet001\Services\viostor\Parameters\MaxTransferSize\enum]
"0"="64  KB"
"1"="128 KB"
"2"="256 KB"

[HKEY_LOCAL_MACHINE\SYSTEM\ControlSet001\Services\viostor\Parameters\PnpInterface]
"5"=dword:00000001

[HKEY_LOCAL_MACHINE\SYSTEM\ControlSet001\Services\viostor\Enum]
"0"="PCI\\VEN_1AF4&DEV_1001&SUBSYS_00021AF4&REV_00\\3&13c0b0c5&2&20"
"Count"=dword:00000001
"NextInstance"=dword:00000001

;
; Add viostor to the critical device database
;

[HKEY_LOCAL_MACHINE\SYSTEM\ControlSet001\Control\CriticalDeviceDatabase\PCI#VEN_1AF4&DEV_1001&SUBSYS_00000000]
"ClassGUID"="{4D36E97B-E325-11CE-BFC1-08002BE10318}"
"Service"="viostor"

[HKEY_LOCAL_MACHINE\SYSTEM\ControlSet001\Control\CriticalDeviceDatabase\PCI#VEN_1AF4&DEV_1001&SUBSYS_00020000]
"ClassGUID"="{4D36E97B-E325-11CE-BFC1-08002BE10318}"
"Service"="viostor"

[HKEY_LOCAL_MACHINE\SYSTEM\ControlSet001\Control\CriticalDeviceDatabase\PCI#VEN_1AF4&DEV_1001&SUBSYS_00021AF4]
"ClassGUID"="{4D36E97B-E325-11CE-BFC1-08002BE10318}"
"Service"="viostor"
'''
    regfile_path = '/tmp/regfile'
    regfile = open(regfile_path, 'w')
    regfile.write(reg_changes)
    regfile.close()
    try:
        subprocess.check_call(["virt-win-reg", "--merge", vhd_name, regfile_path], stderr=open(os.devnull, "wb"))
    except:
        os.unlink(regfile_path)
        print "Can't merge registry changes to VM image!"
        raise
    os.unlink(regfile_path)


def mount_virtio_iso(virtio_iso, mnt_dir):
    os.makedirs(mnt_dir)

    try:
        subprocess.check_call(["mount", "-o", "loop,ro", virtio_iso, mnt_dir])
    except:
        os.rmdir(mnt_dir)
        print "Can't mount virtio ISO"
        raise


def umount_virtio_iso(mnt_dir):
    try:
        subprocess.check_call(["umount", mnt_dir])
    except:
        os.rmdir(mnt_dir)
        print "Can't umount virtio ISO"
        raise

    os.rmdir(mnt_dir)


def get_win_driver_ver(vm_os_ver):
    if re.match(r".*2003.*", vm_os_ver):
        return (win_ver['2003'], win_path['2003'])
    elif re.match(r".*2008.*", vm_os_ver):
        return (win_ver['2008'], win_path['2008'])
    else:
        return false


def upload_viostor(vhd_name, vm_os_ver, vm_os_arch, virtio_iso, win_driver_ver, win_driver_path):
    mnt_dir = '/tmp/virtio_iso'
    mount_virtio_iso(virtio_iso, mnt_dir)
    if vm_os_arch == 'x86_64':
        vm_os_arch = 'amd64'

    virtio_driver_path = mnt_dir + '/' + win_driver_ver + '/' + vm_os_arch + '/viostor.sys'
    # try except here
    # stderr processing
    subprocess.check_call(["guestfish", "-a", vhd_name, "-i", "upload", virtio_driver_path, win_driver_path], stderr=open(os.devnull, "wb"))
    umount_virtio_iso(mnt_dir)
    

if __name__ == '__main__':

    win_ver = {'XP':'wxp', '2003':'wnet', '2008':'wlh', '7':'vista'} # win ver to virtio driver name mapping (VirtIO iso)
    win_path = {'XP':'TBD', '2003':'/WINDOWS/system32/drivers/viostor.sys', '2008':'/Windows/System32/drivers/viostor.sys', '7':'TBD'} # win ver to driver path mapping

    req_tools = ['guestfish', 'virt-inspector', 'virt-win-reg']

    check_req_tools(req_tools)

    parser = argparse.ArgumentParser()
    parser.add_argument('--xml', metavar='XML', help='path to XML file of a VM', required=True)
    parser.add_argument('--iso', metavar='VirtIO ISO', help='path to VirtIO ISO', required=False)
    args = parser.parse_args()

    vm_name, vm_cpu_count, vm_ram_limit, vhd_name, vm_os_ver, vm_os_arch = get_vm_params()
    
    win_re = re.compile(r".*[wW]indows.*")
    if win_re.match(vm_os_ver):
        if args.iso:
            try:
                win_driver_ver, win_driver_path = get_win_driver_ver(vm_os_ver)
            except:
                err_msg = "This OS version (%s) isn't supported by this converter" % vm_os_ver
                sys.exit(err_msg)
            merge_reg_changes(vhd_name)
            upload_viostor(vhd_name, vm_os_ver, vm_os_arch, args.iso, win_driver_ver, win_driver_path)
        else:
            sys.exit("No path to VirtIO ISO! (--iso)")
    else:
        err_msg = "This OS version (%s) isn't supported by this converter" % vm_os_ver
        sys.exit(err_msg)