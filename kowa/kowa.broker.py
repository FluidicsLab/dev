
import sys, os
import asyncio
import mqttools
import threading

import logging
logging.basicConfig(
    level=logging.ERROR,
    # format='%(levelname)-8s %(asctime)s %(threadName)-15s %(message)s'
    format='%(message)s'
    )
baumBrokerLogger = logging.getLogger(__name__)
baumBrokerLogger.setLevel(logging.DEBUG)
baumBrokerLogger.name = "__baumBrokerLogger__"
def loggingFilter(record: logging.Filter): return True
baumBrokerLogger.addFilter(loggingFilter)

BROKER = [('localhost',10008)]

class BrokerWorker(threading.Thread):
    
    def __init__(self, addresses):
        super().__init__()
        self._addresses = addresses
        self.daemon = True
        self._loop = asyncio.new_event_loop()
        self._broker_task = self._loop.create_task(self._run())
        self._running = False

    def run(self):
        asyncio.set_event_loop(self._loop)
        self._running = True

        try:
            self._loop.run_until_complete(self._broker_task)
        except Exception as ex:
            baumBrokerLogger.debug(ex)
        finally:
            self._loop.close()

    def stop(self):        
        if not self._running:
            raise mqttools.NotRunningError('broker stopped already')
        self._running = False
        def cancel_broker_task():
            self._broker_task.cancel()
        self._loop.call_soon_threadsafe(cancel_broker_task)
        self.join()

    async def _run(self):

        broker = mqttools.Broker(self._addresses)

        try:

            baumBrokerLogger.debug('start serving at ' + ":".join(list(map(str,self._addresses))))
            await broker.serve_forever()

        except asyncio.CancelledError as ce:
            baumBrokerLogger.debug(ce)
        except Exception as ex:
            baumBrokerLogger.debug(ex)
        finally:
            baumBrokerLogger.debug('stopped')

def main():     

    os.system('cls')
        
    try:

        bb = [BrokerWorker(b) for b in BROKER]

        for b in bb:
            b.start()
    
        input('<Enter>\n')

        for b in bb:
            b.stop()

        for b in bb:
            b.join()

    except Exception as ex:
        baumBrokerLogger.debug(ex)

    finally:
        pass

if __name__ == '__main__':    
    main() 