#!/usr/bin/env python

import sys
import argparse
import re
import xml.etree.ElementTree as Et
import ntpath
import subprocess
import os
import distutils.spawn


def convert():
    vm_info = {}
    get_vm_params(vm_info)

    print('\nVM Info:')
    print('Name: %s') % vm_info['name']
    print('VHD:  %s') % vm_info['vhd_path']
    print('CPU:  %s') % vm_info['cpu_count']
    print('RAM:  %s') % vm_info['ram_limit']
    print('OS:   %s') % vm_info['os_ver']
    print('Arch: %s\n') % vm_info['os_arch']
    
    if not args.y:
        yes_no()

    merge_reg_changes(vm_info['vhd_path'],
                      vm_info['os_ver'])

    upload_drivers(vm_info['vhd_path'],
                   vm_info['os_ver'],
                   vm_info['os_arch'],
                   args.iso,
                   win_ver[vm_info['os_ver']],
                   win_path[vm_info['os_ver']])

    upload_cert(vm_info['vhd_path'])

    upload_exec(vm_info['os_ver'],
                vm_info['os_arch'],
                vm_info['vhd_path'])

    print('Converted')


def yes_no():
    answer = raw_input('Convert? (y/n)')
    if answer not in ['yes', 'y']:
        sys.exit('Not converted')
    

def check_req_tools():
    req_tools = ['guestfish', 'virt-inspector', 'virt-win-reg', 'hivexget']

    for tool in req_tools:
            if distutils.spawn.find_executable(tool) is None:
                err_msg = tool + ' is not installed or not in PATH'
                sys.exit(err_msg)


def parse_xml():
    xmlpath = args.xml
    xmltree = Et.parse(xmlpath)
    return xmltree


def get_vm_params(vm_info):
    xmltree = parse_xml()
    xmlroot = xmltree.getroot()
    vm_info['name'] = get_vm_name(xmlroot)
    vm_info['cpu_count'] = get_vm_cpu_count(xmlroot)
    vm_info['ram_limit'] = get_vm_ram_limit(xmlroot)
    vm_info['vhd_path'] = get_vhd_path(xmlroot)
    vm_info['os_ver'], vm_info['os_arch'] = get_vm_os_ver(vm_info['vhd_path'])

    return vm_info


def get_vm_name(xmlroot):
    return xmlroot.find('./properties/name').text


def get_vm_cpu_count(xmlroot):
    return xmlroot.find('./settings/processors/count').text


def get_vm_ram_limit(xmlroot):
    return xmlroot.find('./settings/memory/bank/limit').text


def get_vhd_path(xmlroot):
    vhd_re = re.compile(r'.*vhd$')

    # dont like
    for pathname in xmlroot.iter(tag='pathname'):
        if vhd_re.match(pathname.text):
            vhd_path = os.path.join(args.vhd_dir, ntpath.basename(pathname.text))
            if os.path.exists(vhd_path):
                return vhd_path
            else:
                err_msg = 'Can\'t find vhd file at ' + vhd_path
                sys.exit(err_msg)


def get_vm_os_ver(vhd_path):
    try:
        vhd_info = subprocess.check_output(['virt-inspector', vhd_path],
                                           stderr=open(os.devnull, 'wb'))
        xmltree = Et.fromstring(vhd_info)
    except:
        raise

    vm_os_ver = xmltree.find('./operatingsystem/product_name').text
    vm_os_arch = xmltree.find('./operatingsystem/arch').text

    if re.match(r'.*[wW]indows.*2003.*', vm_os_ver):
        vm_os_ver = '2003'
    elif re.match(r'.*[wW]indows.*2008.*', vm_os_ver):
        vm_os_ver = '2008'
    elif re.match(r'.*[wW]indows.*2012.*', vm_os_ver):
        vm_os_ver = '2012'
    else:
        err_msg = 'Can\'t find Windows on this VM or this version (%s) ' \
                  'isn\'t supported by this converter' % vm_os_ver
        sys.exit(err_msg)

    if vm_os_arch == 'x86_64':
        vm_os_arch = 'amd64'
    elif vm_os_arch == 'i386':
        vm_os_arch = 'x86'

    return vm_os_ver, vm_os_arch


def get_device_path(vhd_path):
    reg_path = 'HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion'
    reg_key = 'DevicePath'
    try:
        return subprocess.check_output(['virt-win-reg',
                                        vhd_path,
                                        reg_path,
                                        reg_key],
                                       stderr=open(os.devnull, 'wb')).rstrip().encode('string-escape')
    except:
        raise


def merge_reg_changes(vhd_path, vm_os_ver):
    # hardcode! should use get_device_path() and than convert
    device_path = 'hex(1):43,00,3a,00,5c,00,57,00,69,00,6e,00,64,00,6f,00,77,00,73,00,5c,\
00,69,00,6e,00,66,00,3b,00,43,00,3a,00,5c,00,56,00,69,00,72,00,74,00,49,00,4f,00,00,00'
    reg_changes = '''
[HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion]
"DevicePath"=%s
    ''' % device_path

    regfile_path = '/tmp/regfile'
    regfile = open(regfile_path, 'w')
    regfile.write(reg_changes)
    regfile.close()

    try:
        subprocess.check_call(['virt-win-reg',
                               '--merge',
                               vhd_path,
                               regfile_path])
                             # stderr=open(os.devnull, 'wb'))
    except:
        print('Can\'t merge registry changes to VM image!')
        raise
    finally:
        os.unlink(regfile_path)

    firstboot_reg = h2o_path + '/regs/firstboot.reg'

    try:
        subprocess.check_call(['virt-win-reg',
                               '--merge',
                               vhd_path,
                               firstboot_reg],
                              stderr=open(os.devnull, 'wb'))
    except:
        print('Can\'t merge registry changes to VM image!')
        raise

    if vm_os_ver == '2012':
        regfile_path = h2o_path + '/regs/viostor_2012.reg'
    elif vm_os_ver == '2008':
        regfile_path = h2o_path + '/regs/viostor_2008.reg'
    else:
        regfile_path = h2o_path + '/regs/viostor.reg'

    try:
        subprocess.check_call(['virt-win-reg',
                               '--merge',
                               vhd_path,
                               regfile_path],
                              stderr=open(os.devnull, 'wb'))
    except:
        print('Can\'t merge registry changes to VM image!')
        raise


def mount_virtio_iso(virtio_iso, mnt_dir):
    os.makedirs(mnt_dir)

    try:
        subprocess.check_call(['mount',
                               '-o',
                               'loop,ro',
                               virtio_iso,
                               mnt_dir])
    except:
        os.rmdir(mnt_dir)
        print('Can\'t mount virtio ISO')
        raise


def umount_virtio_iso(mnt_dir):
    try:
        subprocess.check_call(['umount', mnt_dir])
    except:
        print('Can\'t umount virtio ISO')
        raise
    finally:
        os.rmdir(mnt_dir)


def get_win_driver_ver(vm_os_ver):
    if re.match(r'.*2003.*', vm_os_ver):
        return win_ver['2003'], win_path['2003']
    elif re.match(r'.*2008.*', vm_os_ver):
        return win_ver['2008'], win_path['2008']
    elif re.match(r'.*2012.*', vm_os_ver):
        return win_ver['2012'], win_path['2012']
    else:
        return False


def upload_drivers(vhd_path, vm_os_ver, vm_os_arch,
                   virtio_iso, win_driver_ver, win_driver_path):
    mnt_dir = '/tmp/virtio_iso'
    mount_virtio_iso(virtio_iso, mnt_dir)

    try:
        upload_viostor(vhd_path,
                       mnt_dir,
                       win_driver_ver,
                       vm_os_arch,
                       win_driver_path)

        upload_other_drivers(vhd_path,
                             mnt_dir,
                             win_driver_ver,
                             vm_os_ver,
                             vm_os_arch)
    except:
        raise
    finally:
        umount_virtio_iso(mnt_dir)


def upload_viostor(vhd_path, mnt_dir, win_driver_ver,
                   vm_os_arch, win_driver_path):
    virtio_driver_path = os.path.join(mnt_dir,
                                      win_driver_ver,
                                      vm_os_arch,
                                      'viostor.sys')
    # bad stderr processing
    subprocess.check_call(['guestfish',
                           '-a',
                           vhd_path,
                           '-i',
                           'upload',
                           virtio_driver_path,
                           win_driver_path],
                          stderr=open(os.devnull, 'wb'))


def upload_other_drivers(vhd_path, mnt_dir, win_driver_ver,
                         vm_os_ver, vm_os_arch):
    if win_driver_ver in ['wlh', 'wnet']:
        virtio_driver_path = os.path.join(mnt_dir,
                                          'xp',
                                          vm_os_arch,
                                          'netkvm*')
    else:
        virtio_driver_path = os.path.join(mnt_dir,
                                          win_driver_ver,
                                          vm_os_arch,
                                          'netkvm*')

    systemroot = win_path[vm_os_ver].split('/')[1]

    subprocess.call(['guestfish',
                     '-a',
                     vhd_path,
                     '-i',
                     'mkdir',
                     os.path.join('/', systemroot, 'inf/VirtIO')],
                    stderr=open(os.devnull, 'wb'))

    subprocess.call(['guestfish',
                     '-a',
                     vhd_path,
                     '-i',
                     'mkdir',
                     '/VirtIO'],
                    stderr=open(os.devnull, 'wb'))

    upload_command = 'guestfish -a ' + vhd_path + ' -i copy-in ' + \
                     virtio_driver_path + ' /VirtIO'

    subprocess.check_call(upload_command,
                          shell=True,
                          stderr=open(os.devnull, 'wb'))


def upload_cert(vhd_path):
    cert_path = h2o_path + '/execs/redhat.cer'
    try:
        subprocess.check_call(['guestfish',
                               '-a',
                               vhd_path,
                               '-i',
                               'upload',
                               cert_path, '/VirtIO/redhat.cer'],
                              stderr=open(os.devnull, 'wb'))
    except:
        print('Can\'t upload certificate')
        raise


def upload_exec(vm_os_ver, vm_os_arch, vhd_path):
    req_exec = {'srvany.exe': 'srvany.exe'}

    # need this workaround because of weird \
    # win2003 device installation behavior in my env
    if vm_os_ver == '2003':
        devcon = 'devcon_' + vm_os_arch + '.exe'
        req_exec['firstboot_2003.bat'] = 'firstboot.bat'
        req_exec[devcon] = 'devcon.exe'
    else:
        req_exec['firstboot.bat'] = 'firstboot.bat'

    for file in req_exec:
        try:
            file_path = h2o_path + '/execs/' + file
            upload_path = '/VirtIO/' + req_exec[file]
            subprocess.check_call(['guestfish',
                                   '-a',
                                   vhd_path,
                                   '-i',
                                   'upload',
                                   file_path,
                                   upload_path],
                                  stderr=open(os.devnull, 'wb'))
        except:
            raise


if __name__ == '__main__':

    # win ver to virtio driver name mapping (VirtIO iso)
    win_ver = {'XP': 'wxp',
               '2003': 'wnet',
               '2008': 'wlh',
               '2012': 'win7',
               '7': 'win7'
               }

    # win ver to driver path mapping
    win_path = {'XP': '/WINDOWS/System32/drivers/viostor.sys',
                '2003': '/WINDOWS/system32/drivers/viostor.sys',
                '2008': '/Windows/System32/drivers/viostor.sys',
                '2012': '/Windows/System32/drivers/viostor.sys',
                '7': '/Windows/System32/drivers/viostor.sys'}

    parser = argparse.ArgumentParser()
    parser.add_argument('--xml',
                        metavar='XML',
                        help='path to XML file of a VM',
                        required=True)

    parser.add_argument('--vhd_dir',
                        metavar='VHDs dir',
                        help='path to directory with VHD images',
                        required=True)

    parser.add_argument('--iso',
                        metavar='VirtIO ISO',
                        help='path to VirtIO ISO',
                        required=True)

    parser.add_argument('-y', action='store_true')
    args = parser.parse_args()

    h2o_path = os.path.dirname(sys.argv[0])

    check_req_tools()
    convert()
