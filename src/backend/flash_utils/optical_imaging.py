from __future__ import print_function # Compatibility with python 2 and 3
import time
import os
import numpy as np
import ast

class OpticalImages(object):
    def __init__(self, filename):
        self._filename = filename
        self.prefix = os.path.dirname(filename) + '/'
        self._history = []
        self._filesize = None
        self._num_lines = None

    def get(self, bunch_id):
        filename = self._filename
        if os.path.getsize(self._filename) > self._filesize:
            self._update_file(self._filename)
        
        for index in xrange(len(self._history)-1, 0, -1):
            if self._history[index][0] > bunch_id:
                continue
            elif self.history[index][0] == bunch_id:
                fp = open(self.history[index][1], 'rb')
                fp.seek(self.history[index][2]*self.num_pix*self.dtype.itemsize)
                return np.fromfile(fp, dtype=self.dtype, count=self.num_pix).reshape(self.sizex, self.sizey)
                fp.close()
            else:
                return None
        try:
            img = self._history[0][1]
            return img
        except IndexError:
            return None

    def _update_file(self, filename):
        with open(filename, "r") as file_handle:
            total_history = file_handle.readlines()
        self._filesize = os.path.getsize(filename)
        if len(total_history) == self._num_lines:
            return
        else:
            self._num_lines = len(total_history)
        diff_history = total_history[len(self._history):]
        parsed_diff_history = []
        for l in diff_history:
            words = l.split()
            if words[0][0] != '#':
                parsed_diff_history.append(self._parse_line(l))
            elif words[2] == 'type:':
                self.dtype = np.dtype(words[3])
            elif words[2] == 'shape:':
                self.sizex, self.sizey = ast.literal_eval(l.split(':')[1].lstrip())
                self.num_pix = self.sizex*self.sizey
        #parsed_diff_history = [self._parse_line(l) for l in diff_history if l.split('.')[0].isdigit()]
        self._history += parsed_diff_history
        self._filename = filename
        print('Parsed header:', self.sizex, self.sizey, self.dtype)

    def _parse_line(self, line):
        '''
        Returns (bunchID, filename, index) tuple
        '''
        line_data = line.split()
        return int(line_data[2], 16), self.prefix+line_data[3], int(line_data[4])

