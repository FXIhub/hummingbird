import os
import time


class MotorPositions(object):
    def __init__(self, filename):
        self._filename = filename
        self._history = []
        #self._modification_time = os.path.getmtime(self._filename)
        self._filesize = None
        self._num_lines = None

    def get(self, timestamp):
        #timestamp += 18590000
        #print("timestamp = {0}".format(time.strftime("%H:%M:%S", time.localtime(float(timestamp)))))
        self.timestamp = timestamp
        filename = self._filename
        if os.path.getsize(self._filename) > self._filesize:
            self._update_file(self._filename)
        
        for index in xrange(len(self._history)-1, 0, -1):
            if self._history[index][0] > timestamp:
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
        parsed_diff_history = [self._parse_line(l) for l in diff_history]
        self._history += parsed_diff_history

    def _parse_time(self, time):
        #return self._date + int(time[:2])*3600 + int(time[3:5])*60 + float(time[7:])
        return float(time)

    def _parse_line(self, line):
        line_data = line.split()
        data_dict = dict(zip(line_data[1::2], [float(p) for p in line_data[2::2]]))
        # expected_keys = ["InjectorX", "InjectorY", "InjectorZ"]
        # for this_expected_key in expected_keys:
        #     if this_expected_key not in data_dict:
        return (self._parse_time(line_data[0]), data_dict)
