
from _EcatObject import EcatLogger

import subprocess, socket

import threading
from threading import Event, Lock
from queue import Queue

import asyncio
import mqttools
import json

import numpy as np


class scheduleWorker(threading.Thread):

    _exit = None
    _delay = .5

    _stopOnError = False

    _items = None

    _queue:Queue = None
    _lock: Lock = Lock()

    def _set_running(self, value):
        if not value and self._exit is not None:
            self._exit.set()
        if value and self._exit is None:
            self._exit = Event()
    def _get_running(self):
        return self._exit is not None and not self._exit.is_set()
    running = property(fset=_set_running,fget=_get_running)

    _host = None
    def _get_host(self): 
        return self._host    
    Host = property(fget=_get_host)

    _port = None
    def _get_port(self): 
        return self._port
    Port = property(fget=_get_port)

    def __init__(self, host, port):
       super().__init__()
       self._host = host
       self._port = port
       self._items = []
       self._queue = Queue()       
       self.daemon = True

    def run(self):
        pass

    def register(self, item):
        self._lock.acquire()
        try:
            self._items.append(item)
        finally:
            self._lock.release()

    def unregister(self, item):
        self._lock.acquire()
        try:
            self._items.append(item)
        finally:
            self._lock.release()

    def publish(self, data):

        if data is None or data['value'] is None:
            return False
        
        self._lock.acquire()
        try:
            self._queue.put(data)
        finally:
            self._lock.release()

        return not self._queue.empty()
    
    def exit(self):
        self.running = False

    def wait(self):
        self._exit.wait(self._delay)


class subscribeWorker(scheduleWorker):

    TOPIC = '/hot/ecat/value'

    _lock: Lock = Lock()

    def __init__(self, host, port):
       super().__init__(host, port)
       self._delay = .1

    _event = None
       
    def run(self): 

        self.running = True

        async def subscribeTopic(host, port, topics:list[str], callback):
            
            threading.current_thread().name = self._name
            
            client:mqttools.Client = mqttools.Client(host, port, 
                                                     connect_delays=[],
                                                     subscriptions=topics)
            rc = client.client_id
            
            try:
                await client.start()
                
                while self.running:
                
                    message:mqttools.client.Message = await client.messages.get() 
                
                    if message is not None:                

                        data = json.loads(message.message)
                        self._event = asyncio.Event()
                        callback(data)
                        await self._event.wait()

                    else:
                        break
                   
                    #if client.messages.empty():
                    #    break

                client.messages.task_done()

            except Exception as ex:
                EcatLogger.debug(ex)
                return -1
            finally:
                await client.stop()

            return rc  
        
        while self.running:
            
            try:    
                rc = asyncio.run(
                    subscribeTopic(self.Host, self.Port, [subscribeWorker.TOPIC], self.callback), 
                    debug=False)
                
                if (-1 == rc):
                    if -1 == rc:
                        if self._stopOnError:
                            EcatLogger.critical(f'subscription stop on error at {self.Host}:{self.Port}')                        
                            self.running = False            
            except Exception as ee: 
                EcatLogger.error(ee)

            finally:                
                pass

            self.wait()

        self.running = False

    _dataLock = Lock()

    _data = {}
    def _get_data(self): 
        return self._data
    def _set_data(self,value): 
        self._data = value
    Data = property(fget=_get_data,fset=_set_data)

    def subscribe(self, name, n):
        
        self._dataLock.acquire()        
        try:
            key = (name,n)
            if key in self.Data.keys():
                data = self.Data[key]
                self.Data.pop(key, None)
                return data
        except:
            return None
        finally:
            self._dataLock.release()    
        
        return None
    
    def callback(self, data):

        EcatLogger.debug(f"++ receive subscription")
        EcatLogger.debug(f"   {data}")

        self._dataLock.acquire()        
        
        if not isinstance(data, list):
            data = [data]
        items = data.copy()
        errors = [None] * len(items)

        try:
            
            for i,item in enumerate(items):

                try:
            
                    if "command" in item.keys():
                    
                        if item["command"] == "shutdown":
                            self.running = False

                        elif item["command"] == "severity":

                            name = item['source'].upper()                      
                            index = item['target']
                            value = item['value']
                            
                            self.Data[(name, index)] = value
                    
                    else:
                        
                        name = item['source'].replace("Worker","").upper()                        
                        index = item['target']
                        value = item['value']
                        
                        self.Data[(name, index)] = value
                
                except Exception as ex:            
                    errors[i] = ex
                
        finally:
            self._dataLock.release()    

        if all(error is None for error in errors):
            EcatLogger.debug(f"-- done with {len(items)}")
        else:            
            EcatLogger.debug(f"-- failed")
            for i,error in enumerate(errors):
                if error is not None:
                    EcatLogger.error(f"   {i} {error}")

        asyncio.get_running_loop().call_soon_threadsafe(self._event.set)


class publishWorker(scheduleWorker):
    
    def __init__(self, host, port):
       super().__init__(host, port)     
       self._delay = .1  

    class ComplexJSONEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, (np.ndarray, np.number)):
                return obj.tolist()
            return json.JSONEncoder.default(self, obj) 
    
    def run(self): 

        self.running = True
        
        async def publishTopic(host, port, topic, message):
            
            threading.current_thread().name = self._name            
            client = mqttools.Client(
                host, 
                port, 
                connect_delays=[], 
                response_timeout=2)            
            rc = client.client_id
            try:
                await client.start()
                client.publish(mqttools.Message(topic, message))            
            except Exception as ex:
                rc = -1             
            finally:
                await client.stop() 
                                    
            return rc   
        
        loop = asyncio.new_event_loop()
        threading.Thread(target=loop.run_forever).start()   
        
        while self.running:

            self._lock.acquire()

            try:
                prefix = '/hot/ecat/'

                while not self._queue.empty():
                    
                    data = self._queue.get_nowait()

                    if isinstance(data, dict):
                        
                        topic = f"{prefix}{data['source']}"
                        message = json.dumps(data, cls=publishWorker.ComplexJSONEncoder).encode('ascii')
                                             
                        asyncio.run_coroutine_threadsafe(publishTopic(self.Host, self.Port, topic, message), loop)
                    
                    self._queue.task_done()
            
            finally:
                self._lock.release()
        
            self.wait()

        topic = subscribeWorker.TOPIC
        message = {
            "command": "shutdown"
        }                                
        asyncio.run_coroutine_threadsafe(publishTopic(self.Host, self.Port, topic, message), loop)
                
        self.running = False


class EcatBrokerController:

    _scheduler = None
    _debug = False    
    _host = 'localhost'
    _ports = []

    _initialized = False
    def _set_initialized(self,value): 
        self._initialized = value
    def _get_initialized(self): 
        return self._initialized
    Initialized = property(fget=_get_initialized,fset=_set_initialized)

    def __init__(self, ports, debug=False) -> None:        
        self._ports = ports
        self._debug = debug

    def startup(self):

        EcatLogger.debug(f"+ start broker controller @ {self._ports}")

        self._scheduler = []
        
        for port in self._ports:
            self._scheduler = self._scheduler + [
                publishWorker(self._host, port), 
                subscribeWorker(self._host, port)
                ]

        for s in self._scheduler:
            s.start()

        EcatLogger.debug("- done")

    def release(self):

        EcatLogger.debug("+ release broker controller")

        for s in self._scheduler:
            # subscribeWorker will be freed 
            # by a published message
            if isinstance(s, publishWorker):
                s.exit()
                s.join()
        
        EcatLogger.debug("- done")

    def push(self, name, n, data, verbose=0):

        data['source'] = f"{data['name'].lower()}Worker"
        
        data['value'] = {
            'index': n,
            'value': data['value']
        }

        for scheduler in self._scheduler:
            if isinstance(scheduler, publishWorker):
                scheduler.publish(data)

    def pop(self, name:str, n):
    
        value = None
        for scheduler in self._scheduler:
            if isinstance(scheduler, subscribeWorker):
                value = scheduler.subscribe(name, n)
                break

        if value is not None:
            data = {
                "name": name,
                "index": n,
                "value": value
            }
            self.push(name, n, data)

        return value
    
    @staticmethod
    def ping(hosts:list[str], ports:list, shift:str='') -> bool:        
        rc = []
        for host,port in list(zip(hosts,ports)):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                try:
                    EcatLogger.debug(f"{shift}open {host} {port}")
                    sock.connect((host, port))
                    rc.append(True)
                except (socket.timeout, socket.error):
                    rc.append(False)
        return np.any(rc)
    
    
class EcatCallbackController:

    _items = {}
    _callbacks = {}

    def __init__(self):
        pass

    def register(self, source, target, callback):
        if source not in self._callbacks.keys():
            self._callbacks[source] = callback
        if source not in self._items.keys():
            self._items[source] = []
        if all([target != t for t in self._items[source]]):
            self._items[source].append(target)

    def unregister(self, source, target=None):
        if source not in self._items.keys():
            return
        if target is not None:
            self._items[source] = list(filter(lambda t: t != target, self._items[source]))
        else:
            del self._items[source]
            del self._callbacks[source]

    def unregisterAll(self):
        self._items = {}
        self._callbacks = {}

    def startup(self):

        EcatLogger.debug("+ start callback controller")
        
        EcatLogger.debug("- done")

    def release(self):

        EcatLogger.debug("+ release callback controller")
        self.unregisterAll()
        EcatLogger.debug("- done")        

    def push(self, name, n, data, verbose=0):  
        target = f"{data['name'].lower()}.{n}"
        for source in self._items.keys():
            for t in self._items[source]:
                if t == target.upper():
                    self._callbacks[source](data)    
    
