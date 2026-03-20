import time
from types import SimpleNamespace
from threading import Lock, Event, Thread
import numpy as np
import json


class AM8111PidController(object):

    TIMEOUT_CONTROL = 0.01
    FRACTION = 20
    MODE_DEFAULT = 'p'
    MODES = ['d', 'p']

    _scaler = {
        'input': {
            'p': { "low": 0, "high": 700 },             # bar   (pressure)         
            'd': { "low": 0, "high": 1_306_460_160 }    # cycle (distance)         
        },
        'output': { "low": 0, "high": 24_185_993 }      # inc/s (velocity)
    }

    _limit = {
        'output': { "low": -24_185_993 * 3/4, "high": 24_185_993 * 3/4 }  # inc/s (velocity)
    }

    _lock: Lock = Lock()
    _exit = Event()

    _task: Thread = None

    _processvalue = {}
    _setpoint = {}

    _mode = MODE_DEFAULT              # p, d
    def _get_mode(self):
        return self._mode
    def _set_mode(self, value):
        self.reset()
        self._mode = value
    Mode = property(fget=_get_mode,fset=_set_mode)

    _enabled = False
    def _get_enabled(self):
        return self._enabled
    Enabled = property(fget=_get_enabled)

    _target = 0

    _error = { 'p': 0.0, 'd': 0.0 }
    _demand = { 'p': 0.0, 'd': 0.0 }
    _integral = { 'p': [], 'd': [] }

    # Kp, Ki, Kd, dt
    _params = {
        'p': [0.5, 0.001, 0.0001, 0.1],
        'd': [10.0, 0.001, 0.0001, 0.1]
    }

    _factor = { 'p': +1, 'd': -1 }

    _updatable = True

    _callback = None

    _source = []
    def _set_source(self, values: list):
        self._source = []
        for value in values:
            self._source.append(SimpleNamespace(**value))
            self._scaler['input'][value['key']] = {
                "low": value["low"], 
                "high": value["high"]
            }
            self._processvalue[value['key']] = 0
            self._setpoint[value['key']] = 0
            
    def _get_source(self):
        return self._source
    Source = property(fset=_set_source, fget=_get_source)

    def __init__(self, callback):
        super().__init__()
        self.reset()
        self._callback = callback
        self._task = Thread(target=self.compute)
        self._task.start()

    def release(self):
        self._exit.set()

    def config(self, config):
        self._lock.acquire()
        try:

            if 'mode' in config.keys() and config['mode'] is not None:
                self.Mode = config['mode']

            if 'target' in config.keys() and config['target'] is not None:
                self._target = config['target']

            if 'setpoint' in config.keys() and config['setpoint'] is not None:
                self._setpoint[self.Mode] = config['setpoint']

            if 'params' in config.keys() and config['params'] is not None:
                self._params[self.Mode] = config['params'].copy()

            if 'enabled' in config.keys() and config['enabled'] is not None:
                self._enabled = config['enabled']

            if 'reset' in config.keys():
                self.reset()
                
            if 'updatable' in config.keys() and config['updatable'] is not None:
                self._updatable = config['updatable']

            if 'processvalue' in config.keys() and config['processvalue'] is not None:
                self._processvalue[self.Mode] = config['processvalue']

        finally:
            self._lock.release()

    def update(self, key, value=None):
        self._lock.acquire()
        try:
            if value is not None:
                self._processvalue[key] = value
            else:
                self._enabled = False
        finally:
            self._lock.release()

    def reset(self):
        
        for mode in AM8111PidController.MODES:
            self._processvalue[mode] = 0.0
            self._error[mode] = 0.0
            self._demand[mode] = 0.0
            self._integral[mode] = []
        
        self._mode = AM8111PidController.MODE_DEFAULT
        
        self._history = SimpleNamespace(**{
            'time': [],
            'setpoint': [],
            'processvalue': [],
            'demandvalue': [],
            'error': [],
            'param': [],
            'performance': []
        })
            
    def compute(self):

        def scale(value):
            return (value - self._scaler['input'][self._mode]['low']) / (self._scaler['input'][self._mode]['high'] - self._scaler['input'][self._mode]['low'])
        
        def unscale(value):
            return self._scaler['output']['low'] + (self._scaler['output']['high'] - self._scaler['output']['low']) * value

        def limit(value): 
            return max(self._limit['output']['low'], min(self._limit['output']['high'], value))
        
        enabled = False
        zero = False        # zero quick stop

        t = None

        while not self._exit.is_set():

            if enabled and not self._enabled:
                if self._callback is not None:
                    self._callback(None)

            if self._enabled:

                if t is None:
                    t = time.time_ns()

                self._lock.acquire()
                try:

                    mode = self.Mode

                    sp = scale(self._setpoint[mode])
                    pv = scale(max(0, self._processvalue[mode]))

                    err = (pv - sp) * self._factor[mode]

                    params = self._params[mode]

                    kp = params[0] * err
                    ki = params[1] * err * params[3]
                    kd = params[2] * (err - self._error[mode]) / params[3]

                    self._integral[mode].append(ki)                    
                    while len(self._integral[mode]) > AM8111PidController.FRACTION:
                        self._integral[mode].pop(0)
                    ki = sum(self._integral[mode])
                    self._error[mode] = err

                    dv = kp + ki + kd
                    dv = unscale(dv)
                    dv = limit(dv)

                    self._history.time.append(t)
                    self._history.setpoint.append(sp)
                    self._history.processvalue.append(pv)
                    self._history.demandvalue.append(dv)
                    self._history.error.append(err)
                    self._history.param.append(params)
                
                    if self._callback is not None:
                        if self._demand[mode] != dv:                            
                            self._callback(dv, mode, err, params)
                            self._adjust()
                            zero = False
                        else:
                            if dv == 0.0 and not zero:
                                self._callback(dv, mode, err, params)
                                self._adjust()
                                zero = True

                    self._demand[mode] = dv

                finally:
                    self._lock.release()

            self._exit.wait(AM8111PidController.TIMEOUT_CONTROL)

            t = time.time_ns()

            enabled = self._enabled

    def _adjust(self):
        
        if len(self._history.error) < 5:
            return
        
        adaptation_rate = 0.1
            
        last_error = self._history.error[-1]

        current_error = abs(last_error)
        mean_error = np.mean([abs(e) for e in self._history.error[:-1]])
        error_std = np.std(self._history.error[:-1])
        
        performance = current_error + 0.5 * mean_error + 0.2 * error_std
        self._history.performance.append(performance)

        adjusted = False
        params = self._params[self.Mode]

        if len(self._history.performance) > 10:

            # trend
            recent_performance = np.mean(list(self._history.performance)[-10:])
            older_performance = np.mean(list(self._history.performance)[:10])
            
            # adjust by performance
            if recent_performance > older_performance * 1.1:                
                
                params[0] *= (1 - adaptation_rate)
                params[1] *= (1 - adaptation_rate)
                params[2] *= (1 - adaptation_rate)

                adjusted = True

            elif recent_performance < older_performance * 0.9:
                
                params[0] *= (1 + adaptation_rate * 0.5)
                params[1] *= (1 + adaptation_rate * 0.5)
                params[2] *= (1 + adaptation_rate * 0.5)

                adjusted = True
                        
            params[0] = np.clip(params[0], 0.1, 20.0)
            params[1] = np.clip(params[1], 0.01, 1.0)
            params[2] = np.clip(params[2], 0.001, 1.0)

        if adjusted:
            self._params[self.Mode] = params.copy()


def func_(value, mode='', error=0, params=[]):
    
    vp = value / (24_185_993)

    global pvValue
    pvValue = pvValue - vp * 700

    print(pvValue)

def plot_(data):

    t = data.time

    param = np.array(data.param)

    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(5, 1, figsize=(10, 15))

    ax[0].plot(t, data.setpoint, 'r--', label='sp', linewidth=2)
    ax[0].plot(t, data.demandvalue, 'b-', label='pv', linewidth=1)
    ax[0].plot(t, data.processvalue, 'g-', label='dv', linewidth=1)
    ax[0].set_ylabel('')
    ax[0].set_title('pid')
    ax[0].legend()
    ax[0].grid(True)

    ax[1].plot(t, data.error, 'r-', label='err', linewidth=1)
    ax[1].set_ylabel('')
    ax[1].legend()
    ax[1].grid(True)

    ax[2].plot(t, param[:,0], 'g-', label='kp', linewidth=1)
    ax[2].set_ylabel('')
    ax[2].legend()
    ax[2].grid(True)

    ax[3].plot(t, param[:,1], 'g-', label='ki', linewidth=1)
    ax[3].set_ylabel('')
    ax[3].legend()
    ax[3].grid(True)

    ax[4].plot(t, param[:,2], 'g-', label='kd', linewidth=1)
    ax[4].set_ylabel('')
    ax[4].legend()
    ax[4].grid(True)

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    
    ctrl = AM8111PidController(func_)

    simulation_time = 1
    dt = 0.005    
    steps = range(int(simulation_time / dt))

    print(f"steps {len(steps)}")

    sp = 300
    
    global pvValue
    pvValue = 350
    
    ctrl.config({
        'setpoint': sp, 
        'mode': 'p', 
        'enabled': 1, 
        'params': [0.5, 0.01, 0.001, 0.01]
        })

    for i,t in enumerate(steps):

        if i % 100 == 0:
            pvValue += sp * (np.random.normal(0.0, 1.0) * 2 - 1.0) * 0.7
        ctrl.update('p', pvValue)

        time.sleep(dt)

    history = ctrl._history

    ctrl.release()

    plot_(history)

