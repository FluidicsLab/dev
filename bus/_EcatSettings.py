import os, csv
from types import SimpleNamespace
from PyQt5.QtCore import QSettings


class EcatLayout:

    instance = None
    
    class __EcatLayout:

        _name = None

        def _get_name(self): 
            if self._name is None:
                self._name = self.__class__.__name__
            return self._name
        Name = property(fget=_get_name)

        def _get_filename(self): 
            os.chdir(os.path.dirname(os.path.realpath(__file__)))
            return os.path.join(os.getcwd(), f"{self.Name}.csv")
        Filename = property(fget=_get_filename)
        
        def __init__(self, name):
            self._name = name
                    
        def __str__(self):
            return repr(self)
        
        _data = None
        def _get_data(self):
            if self._data is None:
                self._data = []
                with open(self.Filename) as f:                    
                    rows = csv.reader(f, delimiter=";")
                    for row in rows:
                        self._data.append(row)
            return self._data
        Data = property(fget=_get_data)
   
    def __init__(self, name=None):                        
        if not EcatLayout.instance:
            EcatLayout.instance = EcatLayout.__EcatLayout(name)
            
    def __getattr__(self, name):
        return getattr(self.instance, name)
    
    def _get_layout(self):        
        return self.instance
    Layout = property(fget=_get_layout)


class EcatSettings:

    instance = None
    
    class __EcatSettings(QSettings):

        _name = None
        def _get_name(self): 
            if self._name is None:
                self._name = self.__class__.__name__
            return self._name
        Name = property(fget=_get_name)

        def _get_filename(self): 
            os.chdir(os.path.dirname(os.path.realpath(__file__)))
            return os.path.join(os.getcwd(), f"{self.Name}.ini")
        Filename = property(fget=_get_filename)
        
        def __init__(self, name):
            self._name = name
            super().__init__(self.Filename, QSettings.IniFormat)
        
        def __str__(self):
            return repr(self)
   
    def __init__(self, name=None):                        
        if not EcatSettings.instance:
            EcatSettings.instance = EcatSettings.__EcatSettings(name)
            
    def __getattr__(self, name):
        return getattr(self.instance, name)
    
    def _get_settings(self):        
        return self.instance
    Settings = property(fget=_get_settings)


class EcatConfig:    
    
    instance = None
    class __EcatConfig:

        def __init__(self):
            pass
        def __str__(self):
            return repr(self)
        
    def __init__(self, name='_EcatSettings'):
        self._name = name
        if not EcatConfig.instance:
            EcatConfig.instance = EcatConfig.__EcatConfig()
            
    def __getattr__(self, name):
        return getattr(self.instance, name)
    
    _name = ''

    _adapter = None
    def _get_adapter(self):
        if self._adapter is None:
            self._adapter = SimpleNamespace(**dict(
                exclude=list(filter(None,list(map(str,EcatSettings(self._name).value("adapter/exclude",[],list))))),
                active=EcatSettings(self._name).value('adapter/active','',str),
                ))
        return self._adapter
    Adapter = property(fget=_get_adapter)

    _master = None
    def _get_master(self):
        if self._master is None:
            self._master = SimpleNamespace(**dict(
                template=EcatSettings(self._name).value('master/template','_EcatLayout',str),
                topic=EcatSettings(self._name).value('master/topic','ecat',str),
                mandant=EcatSettings(self._name).value('master/mandant','STD',str),
                platform=EcatSettings(self._name).value('master/platform','STD',str),
                ports=list(map(int,filter(None,list(map(str,EcatSettings(self._name).value("master/ports",[],list)))))),
                hosts=list(map(str,filter(None,list(map(str,EcatSettings(self._name).value("master/hosts",[],list)))))),
                ))
        return self._master
    Master = property(fget=_get_master)

    _watchdog = None
    def _get_watchdog(self):
        if self._watchdog is None:
            self._watchdog = SimpleNamespace(**dict(
                mp=EcatSettings(self._name).value('watchdog/mp',2498,int),
                fc=EcatSettings(self._name).value('watchdog/fc',1000.0,float),
                sm=EcatSettings(self._name).value('watchdog/sm',0.0,float),
                pd=EcatSettings(self._name).value('watchdog/pd',0.0,float),
                ))
        return self._watchdog
    Watchdog = property(fget=_get_watchdog)    

    _application = None
    def _get_application(self):
        if self._application is None:
            self._application = SimpleNamespace(**dict(
                name=EcatSettings(self._name).value('application/name','',str),
                display=EcatSettings(self._name).value('application/display','',str),
                icon=EcatSettings(self._name).value('application/icon','',str),
                version=EcatSettings(self._name).value('application/version','',str),
                lang=EcatSettings(self._name).value('application/lang','',str),
                company=EcatSettings(self._name).value('application/company','',str),
                ))
        return self._application
    Application = property(fget=_get_application)    

 