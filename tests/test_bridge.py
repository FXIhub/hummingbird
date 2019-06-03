'''Quick utility to test Karabo Bridge connection

Edit address in main() to connect to a non-standard sender
'''

import sys
import time
import signal
import warnings

try:
    from karabo_bridge import Client
except ImportError:
    pass


class Tester():
    def __init__(self, address, sigint):
        self.sigint = sigint
        self.client = Client(address)
        self.reset()

    def handler(self, signum, frame):
        signal.signal(signal.SIGINT, self.sigint)
        opt = input('Reset? [y/N/e] ("e" to exit): ').lower()
        if opt.startswith('y'):
            signal.signal(signal.SIGINT, self.handler)
            self.reset()
            self.loop()
        elif opt.startswith('e'):
            print('Exiting')
            sys.exit(0)
        else:
            signal.signal(signal.SIGINT, self.handler)
            self.loop()
    
    def reset(self):
        self.ind = 0
        self.old = 0
        self.stime = time.time()
        print('Train ID    Diff   Frame rate')
    
    def loop(self):
        while True:
            d, md = self.client.next()
            tid = d[list(d)[0]]['image.trainId'][0]
            npulses = d[list(d)[0]]['image.data'].shape[-1]
            self.ind += 1
            tnow = time.time()
            if self.ind > 1:
                print('%-10ld  %-6d %.3f Hz' % (tid, tid-self.old, self.ind*npulses/(tnow-self.stime)))
            else:
                print('-'*30)
            self.old = tid
    
def main():
    orig_sigint = signal.getsignal(signal.SIGINT)
    t = Tester('tcp://10.253.0.51:45000', sigint=orig_sigint)
    signal.signal(signal.SIGINT, t.handler)
    t.loop()
    
if __name__ == '__main__':
    try:
        from karabo_bridge import Client
        main()
    except ImportError:
        warnings.warn(UserWarning("karabo_bridge is not available and therefore not be tested..."))
