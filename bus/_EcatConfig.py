
from _EcatUtils import EcatSettings

class EcatConfig:

    MasterEmptyIndex = EcatSettings().value("master/empty.index",99, int)
    MasterEmptyName = EcatSettings().value("master/empty.name",'',str)

    TimerStatusEnabled = EcatSettings().value("timer/status.enabled",0, int)
    TimerStatusDelay = EcatSettings().value("timer/status.delay",4000, int)
    TimerStatusSize = EcatSettings().value("timer/status.size",32, int)
    
    TimerLeakEnabled = EcatSettings().value("timer/leak.enabled",0, int)
    TimerLeakDelay = EcatSettings().value("timer/leak.delay",4000, int)

    DeviceShape = list(map(int,EcatSettings().value("device/shape",[1,1], int)))

    Ed1fVelocityScale: float = EcatSettings().value("ed1f/velocity.scale",255,float)
    Ed1fVelocityFactor: list[float] = list(map(float,EcatSettings().value("ed1f/velocity.factor",[1,2,10,50],list)))        
    
    AnimationSpeed: int = EcatSettings().value("animation/speed",1,int)
    AnimationSize: list[int] = list(map(int,EcatSettings().value("animation/size",(32,32),list)))    
