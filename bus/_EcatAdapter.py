import pysoem
import ifaddr, psutil
from _EcatUtils import EcatUtils
from _EcatObject import EcatObject, EcatLogger


class EcatAdapter(EcatObject):

    _name = ""
    def _get_name(self): 
        return self._name
    Name = property(fget=_get_name)
    
    _desc = ""
    def _get_desc(self): return self._desc
    Desc = property(fget=_get_desc)

    _address = ""
    def _get_address(self): return self._address
    Address = property(fget=_get_address)

    _mac = ""
    def _get_mac(self): return self._mac
    Mac = property(fget=_get_mac)

    def __init__(self, name, desc, address="", mac="") -> None:        
        super().__init__()        
        self._name = name
        self._desc = desc
        self._address = address
        self._mac = mac

    def __str__(self):
        return f"{self._desc} ({self._address}, {self._name}, {self._mac})"
            
    @staticmethod
    def adapters(exclude:list[str],active=None):        
        items = []
        adapters = pysoem.find_adapters()
        for adapter in adapters: 
            name, desc = adapter.name, adapter.desc
            desc = desc.decode('ascii')                        
            if 0==EcatUtils.exclude_(desc,exclude):                
                item = dict(key=desc, value=EcatAdapter(name=name, desc=desc))
                if active is None or len(active) == 0:
                    items.append(item)
                else:
                    if active == desc or active == name:
                        items.append(item)
                        print(f"using adapter {name} {desc}")
                        break
        return items
    
    @staticmethod
    def list_adapters():
        adapters = pysoem.find_adapters()
        for i,adapter in enumerate(adapters): 
            name, desc = adapter.name, adapter.desc
            desc = desc.decode('ascii')            
            print(f"{i:02d}: {name} {desc}")

    @staticmethod
    def get_mac_address(name):
        for interface in psutil.net_if_addrs():
            mac_address = psutil.net_if_addrs()[interface][0].address
            if mac_address and interface == name:        
                return mac_address.replace("-",":").lower()
        return None
    
    @staticmethod
    def get_ip_address(ips):
        for ip in ips:
            if ip.network_prefix in [16,24]:
                return ip.ip
        return None            

    @staticmethod
    def adapters2(exclude:list[str],active=None,shift:str=''):        
        items = []
        adapters = ifaddr.get_adapters(include_unconfigured=False)
        EcatLogger.debug(f"{shift}searching in {len(adapters)} adapters")
        for i,adapter in enumerate(adapters):
            eth_name = adapter.ips[0].nice_name
            address = EcatAdapter.get_ip_address(adapter.ips)
            name = f"\\Device\\NPF_{adapter.name}"
            desc = adapter.nice_name
            if 0==EcatUtils.exclude_(desc,exclude):
                mac = EcatAdapter.get_mac_address(eth_name)
                if mac != None:
                    item = dict(key=desc, value=EcatAdapter(name=name, desc=desc, mac=mac, address=address))
                    if active is None or len(active) == 0:
                        items.append(item)
                    else:
                        if active == mac:
                            items.append(item)
                            EcatLogger.debug(f"{shift}using no {i:02d} mac {mac} {desc} address {address}")
                            break
                else:
                    if active == desc or active == name:
                        item = dict(key=desc, value=EcatAdapter(name=name, desc=desc, mac=None, address=address))
                        items.append(item)
                        EcatLogger.debug(f"{shift}using no {i:02d} {desc} address {address}")
                        break
        return items
        
    @staticmethod
    def list_adapters2():
        adapters = ifaddr.get_adapters(include_unconfigured=False)
        for i,adapter in enumerate(adapters):
            eth_name = adapter.ips[0].nice_name
            address = EcatAdapter.get_ip_address(adapter.ips)
            name = f"\\Device\\NPF_{adapter.name}"
            desc = adapter.nice_name            
            mac = EcatAdapter.get_mac_address(eth_name)
            print(f"{i:02d}: {name} {mac} {desc:>64} {address}")