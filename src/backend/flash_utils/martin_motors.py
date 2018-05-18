from __future__ import print_function # Compatibility with python 2 and 3
import time
import os

class MotorPositions(object):
    def __init__(self, filename):
        self._filename = filename
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
            else:
                return self._history[index][1]
        return self._history[0][1]

    def _update_file(self, filename):
        with open(filename, "r") as file_handle:
            total_history = file_handle.readlines()
        self._filesize = os.path.getsize(filename)
        if len(total_history) == self._num_lines:
            return
        else:
            self._num_lines = len(total_history)
        diff_history = total_history[len(self._history):]
        parsed_diff_history = [self._parse_line(l) for l in diff_history if l.split('.')[0].isdigit()]
        self._history += parsed_diff_history
        self._filename = filename

    def _parse_line(self, line):
        '''
        Returns (bunchID, motor_positions_dict) tuple
        '''
        line_data = line.split(',')
        data_dict = {'X-AL': float(line_data[5]),
                     'Y-AL': float(line_data[6]),
                     'Z-AL': float(line_data[7]),
                     'O-AA1': float(line_data[8]),
                     'X-AA1': float(line_data[9]),
                     'Y-AA1': float(line_data[10]),
                     'O-AA': float(line_data[11]),
                     'Z-AA': float(line_data[12]),
                     'X-PSA': float(line_data[13]),
                     'X-AA': float(line_data[14]),
                     'Y-AA': float(line_data[15]),
                     'Y-PSA': float(line_data[16]),
                     'Z-PSA': float(line_data[17]),
                     'Y-LAS': float(line_data[18]),
                     'X-LOLLI': float(line_data[19]),
                     'Y-LOLLI': float(line_data[20]),
                     'X-LAS': float(line_data[21]),
                     'Z-LAS': float(line_data[22]),
                     'X-OBJ': float(line_data[23]),
                     'Z-OBJ': float(line_data[24]),
                     'Y-OBJ': float(line_data[25]),
                     'Z-LOLLI': float(line_data[26]),
                     'X-OBJ+LAS': float(line_data[27]),
                     'Y-OBJ+LAS': float(line_data[28]),
                     'Z-OBJ+LAS': float(line_data[29]),
                     'AA1': float(line_data[30]),
                     'AA': float(line_data[31]),
                     'X-AL-VIRT': float(line_data[32]),
                     'Z-AL-VIRT': float(line_data[33])}
        return (int(line_data[4], 16), data_dict)

