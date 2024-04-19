from mininet.net import Mininet
from mininet.node import Host, OVSSwitch, Controller
from mininet.link import Intf
from mininet.cli import CLI
from mininet.log import setLogLevel, info

def create_network():
    net = Mininet(controller=Controller)

    # Добавляем контроллер
    net.addController('c0')

    # Добавляем свитч
    switch = net.addSwitch('s1')
    Intf('eth0', node=switch)

    # Добавляем хосты h1 и h2
    h1 = net.addHost('h1', ip='192.168.2.3/24')
    h2 = net.addHost('h2', ip='192.168.2.4/24')

    # Подключаем хосты к свитчу
    net.addLink(h1, switch)
    net.addLink(h2, switch)

    # Запускаем сеть
    net.start()

    # Настройка IP-адреса для хостов с помощью ifconfig
    h1.cmd('ifconfig h1-eth0 192.168.2.3 netmask 255.255.255.0')
    h2.cmd('ifconfig h2-eth0 192.168.2.4 netmask 255.255.255.0')

    # Установка шлюза для хоста h1
    h1.cmd('route add default gw 192.168.2.1')

    # Установка шлюза для хоста h2
    h2.cmd('route add default gw 192.168.2.1')

    info('*** Running DHCP script on h1\n')
    h1.cmd('sudo python3 dhcp_server.py &')
    
    info('*** Running DNS script on h1\n')
    h2.cmd('sudo python3 dns_server.py &')
    

    # Запуск интерактивной оболочки Mininet CLI
    CLI(net)

    info('*** Closing DHCP server\n')
    h1.cmd('sudo pkill -SIGINT -f "python3 dhcp_server.py"')

    info('*** Closing DNS server\n')
    h2.cmd('sudo pkill -SIGINT -f "python3 dns_server.py"')

    # Остановка сети Mininet
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    create_network()
