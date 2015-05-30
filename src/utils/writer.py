import time

class Writer:
    def __init__(self, outfolder, maxlen=1000):
        self.outfolder = outfolder
        self.maxlen    = maxlen
        self.counter   = 0

    def timestamp(self):
        t = time.localtime()
        #timestamp = str(t.tm_year) + '%02d' %t.tm_mon + '%02d' %t.tm_mday + \
        #            '_' + '%02d' %t.tm_hour + '%02d' %.tm_min
        #return timestamp
        
    def openfile(self):
        filename = self.outfolder + '/' + self.timestamp() + '.out'
        self.file = open(filename, 'w')
        print "Opened new file: ", filename
