from __future__ import print_function  # Compatibility with python 2 and 3

import os
import time


class MotorPositions(object):
    def __init__(self, path):
        self._path = path
        self._history = []
        #self._modification_time = os.path.getmtime(self._filename)
        self._filename = None
        self._filesize = None
        self._date = None
        self._num_lines = None

    def get(self, timestamp):
        #timestamp += 18590000
        self.timestamp = timestamp
        filename = self._time_to_filename(timestamp)
        if filename != self._filename:
            tmp_time = time.localtime(timestamp)
            self._date = time.mktime((tmp_time.tm_year, tmp_time.tm_mon, tmp_time.tm_mday, 0, 0, 0, tmp_time.tm_wday, tmp_time.tm_yday, tmp_time.tm_isdst))
            self._history = []
            self._update_file(filename)
        if os.path.getsize(self._filename) > self._filesize:
            print('File size change')
            self._update_file(self._filename)
        
        for index in xrange(len(self._history)-1, 0, -1):
            if self._history[index][0] > timestamp:
                continue
            else:
                return self._history[index][1]
        return self._history[0][1]

    def _time_to_filename(self, timestamp):
        time_info = time.localtime(timestamp)
        return "{0}/stage-server_positions_{1:04}-{2:02}-{3:02}.log".format(self._path, time_info.tm_year, time_info.tm_mon, time_info.tm_mday)

    def _update_file(self, filename):
        print("Motors file:", filename)
        while not os.path.isfile(filename):
            self.timestamp -= self.timestamp%(24.*3600.) + 5.
            filename = self._time_to_filename(self.timestamp)
            print(filename)
        with open(filename, "r") as file_handle:
            total_history = file_handle.readlines()
        self._filesize = os.path.getsize(filename)
        if len(total_history) == self._num_lines:
            return
        else:
            self._num_lines = len(total_history)
        diff_history = total_history[len(self._history):]
        parsed_diff_history = [self._parse_line(l) for l in diff_history if len(l) > 150]
        self._history += parsed_diff_history
        self._filename = filename

    def _parse_time(self, time):
        return self._date + int(time[:2])*3600 + int(time[3:5])*60 + float(time[7:])

    def _parse_line(self, line):
        line_data = line.split()
        data_dict = {"catcher_x": float(line_data[2]),
                     "catcher_y": float(line_data[3]),
                     "catcher_z": float(line_data[4]),
                     "aperture_x": float(line_data[6]),
                     "aperture_y": float(line_data[7]),
                     "aperture_z": float(line_data[8]),
                     "objective_x": float(line_data[10]),
                     "objective_y": float(line_data[11]),
                     "objective_z": float(line_data[12]),
                     "inline_mic": float(line_data[14]),
                     "inline_mirror_x": float(line_data[16]),
                     "inline_mirror_y": float(line_data[17]),
                     "fibre_x": float(line_data[19]),
                     "fibre_y": float(line_data[20]),
                     "fibre_z": float(line_data[21]),
                     "rod_x": float(line_data[23]),
                     "rod_y": float(line_data[24]),
                     "rod_z": float(line_data[25]),
                     "nozzle_x": float(line_data[27]),
                     "nozzle_y": float(line_data[28]),
                     "nozzle_z": float(line_data[29]),
                     "nozzle_rot": float(line_data[31]),
                     "dummy": float(line_data[33])}
        return (self._parse_time(line_data[0]), data_dict)
