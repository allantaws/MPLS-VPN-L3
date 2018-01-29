import ctypes

import serial
import time
import datetime
import paramiko


MAX_BUFFER = 65535
def obtener_FechaYHora():
    info=datetime.datetime.now()
    fecha=str(info.day)+"-"+str(info.month)+"-"+str(info.year)
    if info.minute<10:
        minutos="0"+str(info.minute)
    else:
        minutos=str(info.minute)
    if info.second<10:
        segundos="0"+str(info.second)
    else:
        segundos=str(info.second)
    if info.hour<10:
        horas="0"+str(info.hour)
    else:
        horas=str(info.hour)
    hora=horas+"H"+minutos+"M"+segundos+"S"
    return fecha,hora



def login_ssh(IP, username, password):
    # Crea instancia de un cliente SSH.
    remote_conn_pre = paramiko.SSHClient()
    # Agrega automáticamente hosts no confiables(asegúrese de que esté bien para la política de seguridad en su entorno).
    remote_conn_pre.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    # Inicia conexión SSH.
    remote_conn_pre.connect(IP, username=username, password=password, look_for_keys=False, allow_agent=False)
    # Permite una conexión interactiva con el host.
    remote_conn = remote_conn_pre.invoke_shell()
    # Leer 1000 bytes de la salida actual del host.
    output = remote_conn.recv(MAX_BUFFER)
    return remote_conn_pre, remote_conn

def disable_paging(remote_conn):
    '''Disable paging on a Cisco router'''
    remote_conn.send("terminal length 0\r\n")
    while(not remote_conn.recv_ready()):
        time.sleep(0.5)
    output = (remote_conn.recv(MAX_BUFFER)).decode()

def back_home(remote_conn):
    remote_conn.send("\n")
    while (not remote_conn.recv_ready()):
        time.sleep(0.5)
    output = (remote_conn.recv(MAX_BUFFER)).decode()
    print(output)
    if('config' in output):
        remote_conn.send("end\n")
        remote_conn.send("\n")
        while (not remote_conn.recv_ready()):
            time.sleep(0.5)
        output = (remote_conn.recv(MAX_BUFFER)).decode()
        print("sal")

def sh_usernames(remote_conn):
    list_users = ""
    remote_conn.send("show start | include username\n")
    while (not remote_conn.recv_ready()):
        time.sleep(0.5)
    output = (remote_conn.recv(MAX_BUFFER)).decode()
    output = output.replace('\r\n', '\n').split('\n')
    print(output)
    for i in range(1, len(output) - 1):
        line = output[i].split(" ")
        if ("username" in line[0]):
            list_users += (line[1] + "\n")
    print("\n" + list_users)
    return list_users

def add_import(remote_conn, name_vrf, vlan):
    if(vlan.isnumeric()):
        remote_conn.send("conf t\n")
        remote_conn.send("ip vrf " + name_vrf + "\n")
        remote_conn.send("route-target import " + vlan + ":" + vlan + "\n")
        while (not remote_conn.recv_ready()):
            time.sleep(0.5)
        output = (remote_conn.recv(MAX_BUFFER)).decode()
        output = output.replace('\r\n', '\n')
        print("/////")
        print(output)
        if "please configure" in output:
            ctypes.windll.user32.MessageBoxW(0, "La VRF ingresada no tiene un route distinguisher asignado",
                                         "Error", 0)
        else:
            ctypes.windll.user32.MessageBoxW(0, "Configuración realizada con éxito",
                                             "Done", 0)
        back_home(remote_conn)
    else:
        ctypes.windll.user32.MessageBoxW(0, "VLAN incorrecta",
                                         "Error", 0)

def config_dir(remote_conn,interfaces, IPs, masks):
    remote_conn.send("conf t\n")
    remote_conn.send("int "+interfaces+ "\n")
    remote_conn.send("ip add "+IPs+" "+masks+ "\n")
    remote_conn.send("no sh\n")
    remote_conn.send("do wr\n")
    while (not remote_conn.recv_ready()):
        time.sleep(0.5)
    back_home(remote_conn)

def conf_plantilla(remote_conn, hostname, domain_name, dns1, dns2):
    remote_conn.send("conf t\n")
    if(len(dns1)>0):
        remote_conn.send("ip name-server "+dns1+"\n")
    if (len(dns2)>0):
        remote_conn.send("ip name-server " + dns2+"\n")
    remote_conn.send("host "+hostname+"\n"+"ip domain-name "+domain_name+"\n"+
                "banner motd # ACCESO SOLO A PERSONAL AUTORIZADO#"+"\n"+
                "line vty 0 4"+"\n"+
                "transport input all"+"\n"+
                "login local"+"\n"+
                "exec-timeout 3 3"+"\n"+
                "logging synchronous"+"\n"+
                "line console 0"+"\n"+
                "transport output all"+"\n"+
                "login local"+"\n"+
                "exec-timeout 3 3"+"\n"+
                "logging synchronous"+"\n"+
                "do wr"+"\n")
    while (not remote_conn.recv_ready()):
        time.sleep(0.5)
    back_home(remote_conn)

def conf_credencial(remote_conn,user,password,privilegio):
    try:
        remote_conn.send("conf t" + "\n"+
                         "username "+user+" privilege "+privilegio+" secret "+password+'\n'+
                         "do wr" + '\n')
        while (not remote_conn.recv_ready()):
            time.sleep(0.5)
        back_home(remote_conn)
    except Exception:
        ctypes.windll.user32.MessageBoxW(0, "Ocurrio un error",
                                         "Error", 1)

def get_dirs_red(remote_conn):
    list_dirs_red = []
    remote_conn.send("sh ip route connected | exclude /32\n")
    while (not remote_conn.recv_ready()):
        time.sleep(0.5)
    time.sleep(3)
    output = (remote_conn.recv(MAX_BUFFER)).decode()
    output = output.replace('\r\n', '\n').split('\n')
    print(output)
    for i in range(8, len(output) - 1):
        if ("connected" in output[i] and "/" in output[i] and not("ip" in output[i])):
            line = output[i].split(" ")
            print(" OSPF")
            for j in range(0, len(line)):
                if ("/" in line[j]):
                    list_dirs_red.append(line[j])
                    break
    back_home(remote_conn)
    return list_dirs_red

def get_wildcard(list_dirs_red):
    list_wildcards = []
    for k in range(0, len(list_dirs_red)):
        line = list_dirs_red[k].split('/')
        mask = 32 - int(line[1])
        wildcard = [0, 0, 0, 0]
        octeto = 3
        while (mask > 8):
            wildcard[octeto] = 2 ** 8 - 1
            octeto -= 1
            mask -= 8
        wildcard[octeto] = 2 ** mask - 1
        list_wildcards.append(
            str(wildcard[0]) + '.' + str(wildcard[1]) + '.' + str(wildcard[2]) + '.' + str(wildcard[3]))
    return list_wildcards

def get_ip_interfaz(remote_conn):
    print("int")
    back_home(remote_conn)
    info_interfaz=[]
    remote_conn.send("sh ip int b\n")
    while (not remote_conn.recv_ready()):
        time.sleep(0.5)
    output = (remote_conn.recv(MAX_BUFFER)).decode()
    output = output.replace('\r\n', '\n').split('\n')
    for i in range(1, len(output)-1):
        line = output[i].split()
        print(line)
        if not("#" in line[0]) and "/" in line[0]:
            if(len(line[0].split("."))==1):
                interfaz = [line[0], line[4], line[1]]
                if line[4]!="up":
                    interfaz[1]="down"
                info_interfaz.append(interfaz)
    back_home(remote_conn)
    return info_interfaz

def get_ospf_neig(remote_conn):
    loopback_rd=""
    back_home(remote_conn)
    remote_conn.send("show ip interface brief | include Loopback\n")
    time.sleep(3)
    while (not remote_conn.recv_ready()):
        time.sleep(0.5)
    output = (remote_conn.recv(MAX_BUFFER)).decode()
    output = output.replace('\r\n', '\n').split('\n')
    for i in range(0, len(output)):
        line = output[i].split()
        if "Loopback" in line[0]:
            print(line[0])
            loopback_rd = (line[1])
    neighbors=[]
    list_neig=[]
    print("---" + loopback_rd)
    remote_conn.send("sh ip ospf database network | include Attached Router\n")
    while (not remote_conn.recv_ready()):
        time.sleep(0.5)
    output = (remote_conn.recv(MAX_BUFFER)).decode()
    output = output.replace('\r\n', '\n').split('\n')
    for i in range(1, len(output)):
        print(output[i])
        if('Attached Router' in output[i]):
            list_neig.append((output[i].split(":"))[1])
    for j in range(0, len(list_neig)):
        dir = list_neig[j][1:]
        if not(dir in neighbors) and dir!=loopback_rd:
            neighbors.append(dir)
    print(neighbors)
    back_home(remote_conn)
    return neighbors

def config_OSPF(remote_conn):
    list_dirs_red = get_dirs_red(remote_conn)
    list_wildcards = get_wildcard(list_dirs_red)
    print(list_dirs_red)
    print(list_wildcards)
    remote_conn.send("conf t\n")
    remote_conn.send("router ospf 1\n")
    for i in range(0,len(list_dirs_red)):
        remote_conn.send("network "+list_dirs_red[i].split('/')[0]+" "+list_wildcards[i]+" area 0"+"\n")
        while (not remote_conn.recv_ready()):
            time.sleep(0.5)
    back_home(remote_conn)

def conf_mpls_interfaces(remote_conn):
    back_home(remote_conn)
    interfaces = get_ip_interfaz(remote_conn)
    print(interfaces)
    remote_conn.send("conf t\n")
    for i in range(0,len(interfaces)):
        if (interfaces[i][1]=="up" and not("Loopback" in interfaces[i][0])):
            print(i)
            remote_conn.send("int "+interfaces[i][0]+"\n")
            remote_conn.send("mpls ip\n")
            remote_conn.send("exit\n")
            while (not remote_conn.recv_ready()):
                time.sleep(0.5)
    time.sleep(5)
    print("out")

def config_cef_mpls_ldp(remote_conn):
    remote_conn.send("conf t\n")
    remote_conn.send("ip cef\n")
    remote_conn.send("mpls label protocol ldp\n")
    remote_conn.send("mpls ldp router-id loopback0\n")
    remote_conn.send("mpls ip\n")
    print("2.0")
    conf_mpls_interfaces(remote_conn)
    back_home(remote_conn)

def config_vrf(remote_conn, name_vrf, AS, vlan):
    remote_conn.send("conf t\n")
    remote_conn.send("ip vrf "+name_vrf+"\n")
    remote_conn.send("rd "+AS+":"+vlan+"\n")
    remote_conn.send("route-target export "+vlan+":"+vlan+"\n")
    remote_conn.send("route-target import " + vlan + ":" + vlan + "\n")
    while (not remote_conn.recv_ready()):
        time.sleep(0.5)

def config_add_interfaz_vrf(remote_conn, name_vrf, vlan, interfaz, ip, mascara):
    remote_conn.send("interface "+interfaz+"\n")
    remote_conn.send("no sh\n")
    remote_conn.send("no mpls ip\n")
    remote_conn.send("interface "+interfaz+"."+vlan+"\n")
    remote_conn.send("encapsulation dot1Q "+ vlan + "\n")
    while (not remote_conn.recv_ready()):
        time.sleep(0.5)
    remote_conn.send("ip vrf forwarding " + name_vrf + "\n")
    remote_conn.send("ip add "+ip+" "+mascara+ "\n")
    while (not remote_conn.recv_ready()):
        time.sleep(0.5)
    back_home(remote_conn)

def config_route_PE_CE(remote_conn, name_vrf, red_CE, mascara_CE, int_salida):
    remote_conn.send("conf t\n")
    remote_conn.send("ip route vrf "+name_vrf+" "+red_CE+" "+mascara_CE+" "+int_salida+"\n")
    while (not remote_conn.recv_ready()):
        time.sleep(0.5)
    back_home(remote_conn)

def redistribute_vrf(remote_conn, name_vrf):
    remote_conn.send("conf t\n")
    remote_conn.send("router bgp 1\n")
    remote_conn.send("address-family ipv4 vrf "+name_vrf+"\n")
    remote_conn.send("redistribute static\n")
    remote_conn.send("do wr\n")
    while (not remote_conn.recv_ready()):
        time.sleep(0.5)
    back_home(remote_conn)

def conf_route_CE(remote_conn, ip_salida):
    remote_conn.send("conf t\n")
    remote_conn.send("no router ospf 1\n")
    remote_conn.send("ip route 0.0.0.0 0.0.0.0 "+ip_salida+" \n")
    remote_conn.send("do wr\n")
    while (not remote_conn.recv_ready()):
        time.sleep(0.5)
    back_home(remote_conn)

def config_iBGP(remote_conn):
    bgp_neigh = get_ospf_neig(remote_conn)
    rd_p = read_file()
    remote_conn.send("conf t\n")
    remote_conn.send("router bgp 1\n")
    for i in range (0, len(bgp_neigh)):
        if not(bgp_neigh[i] in rd_p):
            remote_conn.send("neighbor "+bgp_neigh[i]+" remote-as 1\n")
            remote_conn.send("neighbor " + bgp_neigh[i] + " update-source loopback0\n")
            remote_conn.send("neighbor " + bgp_neigh[i] + " next-hop-self\n")
            remote_conn.send("no auto-summary\n")
    while (not remote_conn.recv_ready()):
        time.sleep(0.5)
    back_home(remote_conn)

def config_MP_BGP(remote_conn):
    bgp_neigh = get_ospf_neig(remote_conn)
    rd_p = read_file()
    remote_conn.send("conf t\n")
    remote_conn.send("router bgp 1\n")
    remote_conn.send("address-family vpnv4\n")
    print("en BGP ")
    print(bgp_neigh)
    for i in range(0, len(bgp_neigh)):
        if not (bgp_neigh[i] in rd_p):
            remote_conn.send("neighbor " + bgp_neigh[i] + " activate\n")
            remote_conn.send("neighbor " + bgp_neigh[i] + " send-community extended\n")
            while (not remote_conn.recv_ready()):
                time.sleep(0.5)
    remote_conn.send("exit-address-family\n")
    remote_conn.send("end\n")
    while (not remote_conn.recv_ready()):
        time.sleep(0.5)
    back_home(remote_conn)

def show_res(remote_conn):
    copy = False
    salida = ""
    remote_conn.recv(1000)
    remote_conn.send("show vrf\n")
    while (not remote_conn.recv_ready()):
        time.sleep(0.5)
    time.sleep(1)
    output = (remote_conn.recv(MAX_BUFFER)).decode()
    output = output.split('\r\n')
    for i in range(0, len(output)):
        if("show vrf" in output[i]):
            copy = True
        if (copy == True):
            salida+=(output[i]+"\r\n")
    print("iiii")
    print(output)
    return salida

def save_ID(remote_conn):
    back_home(remote_conn)
    remote_conn.send("show ip interface brief | include Loopback\n")
    while (not remote_conn.recv_ready()):
        time.sleep(0.5)
    output = (remote_conn.recv(MAX_BUFFER)).decode()
    output = output.replace('\r\n', '\n').split('\n')
    for i in range(0,len(output)):
        line = output[i].split()
        if "Loopback" in line[0]:
            write_file(line[1])
    back_home(remote_conn)

def write_file(dir_id):
    archivo = open('rd_P.txt', 'a')
    archivo.write(dir_id+'\n')
    archivo.close()

def read_file():
    rd_p = []
    archivo = open('rd_P.txt', 'r')
    lines = archivo.readlines()
    for i in range (0, len(lines)):
        rd_p.append(lines[i][:-1])
    print(rd_p)
    return rd_p