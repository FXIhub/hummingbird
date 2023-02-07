# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
"""A table to show the available PlotData"""

from ..Qt import QtCore, QtGui
from . import ImageWindow, PlotWindow

#from .plot_window import PlotWindow

class PlotDataTable(QtGui.QWidget):
    """A table to show the available PlotData"""
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        label = QtGui.QLabel('<center><b>Data Sources</b></center>')
        vbox = QtGui.QVBoxLayout(self)
        vbox.addWidget(label)

        self.table = QtGui.QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(['Backend', 'Title','Buffer Capacity','Save on Exit', 'Record History'])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setHighlightSections(False)
        self.table.verticalHeader().hide()
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.table.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.cellDoubleClicked.connect(self._on_double_click)

        self._groups = {None: [[], None]}
        
        vbox.addWidget(self.table)
        hbox = QtGui.QHBoxLayout()
        hbox.addStretch()
        self.clear_buffer = QtGui.QPushButton('Clear Buffer',self)
        self.clear_buffer.setEnabled(False)
        self.clear_buffer.clicked.connect(self._on_clear_buffer_clicked)
        hbox.addWidget(self.clear_buffer)
        self.buffer_size = QtGui.QPushButton('Set Buffer Capacity',self)
        self.buffer_size.setEnabled(False)
        self.buffer_size.clicked.connect(self._on_buffer_size_clicked)
        hbox.addWidget(self.buffer_size)
        self.buffer_spin = QtGui.QSpinBox(self)
        self.buffer_spin.setEnabled(False)
        self.buffer_spin.setMaximum(1024*1024*1024)
        hbox.addWidget(self.buffer_spin)
        hbox.addStretch()
        vbox.addLayout(hbox)
#        vbox.addStretch()

    def add_source(self, source):
        source.plotdata_added.connect(self._on_plotdata_added)
        # Add existing plotdata
        for plotdata in source.plotdata.values():
            self.add_to_group(plotdata.group, source, plotdata)
        source.unsubscribed.connect(self._on_unsubscribe)
        source.subscribed.connect(self._on_subscribe)

    def add_to_group(self, group, source, plotdata):
        if group is None:
            pass
            # no group, add it on top
        if group not in self._groups:
            ref_item = self.add_header(group)
            self._groups[group] = [[plotdata], ref_item]
        else:
            self._groups[group][0].append(plotdata)
        row_index = self.get_group_row(group) + len(self._groups[group][0])
        self.add_row(source, plotdata, row_index)

    def get_group_row(self, group):
        if group is None:
            return -1
        if group not in self._groups:
            return None
        return self.table.indexFromItem(self._groups[group][1]).row()

    def item_is_group_header(self, item):
        return isinstance(item.data(QtCore.Qt.UserRole), type(u""))
    
    def _on_plotdata_added(self, plotdata):
        source = self.sender()
        if plotdata.group is None:
            self.add_to_group(None, source, plotdata)
        else:
            self.add_to_group(plotdata.group, source, plotdata)

    def add_row(self, source, plotdata, row=None):
        if row is None:
            row = self.table.rowCount()
        self.table.insertRow(row)
        item = QtGui.QTableWidgetItem(source.name())
        item.setData(QtCore.Qt.UserRole, source)
        item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
        self.table.setItem(row, 0, item)
        item = QtGui.QTableWidgetItem(plotdata.title)
        item.setData(QtCore.Qt.UserRole, plotdata)
        item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
        self.table.setItem(row, 1, item)
        bar = QtGui.QProgressBar()        
        self.table.setItem(row, 2, QtGui.QTableWidgetItem())
        self.table.setCellWidget(row, 2, self._center_widget(bar))
        checkbox = QtGui.QCheckBox()
        checkbox.setChecked(plotdata.restored)
        self.table.setItem(row, 3, QtGui.QTableWidgetItem())
        self.table.setCellWidget(row, 3, self._center_widget(checkbox))
        checkbox = QtGui.QCheckBox()
        checkbox.setEnabled(plotdata.ishistory)
        checkbox.setChecked(plotdata.recordhistory)
        self.table.setItem(row, 4, QtGui.QTableWidgetItem())
        self.table.setCellWidget(row, 4, self._center_widget(checkbox))

        # Mark existing subscriptions
        if(plotdata.title in source.subscribed_titles):
            self._set_subscription(source, plotdata.title, True)

    def add_header(self, name, row=None):
        if row is None:
            row = self.table.rowCount()
        self.table.insertRow(row)
        named_item = QtGui.QTableWidgetItem(name)
        named_item.setFlags(QtCore.Qt.NoItemFlags)
        header_font = QtGui.QFont()
        header_font.setBold(True)
        named_item.setFont(header_font)
        named_item.setData(QtCore.Qt.UserRole, str(name))
        self.table.setItem(row, 1, named_item)
        separator_text = ""
        item = QtGui.QTableWidgetItem(separator_text)
        item.setFlags(QtCore.Qt.NoItemFlags)
        self.table.setItem(row, 0, item)
        item = QtGui.QTableWidgetItem(separator_text)
        item.setFlags(QtCore.Qt.NoItemFlags)
        self.table.setItem(row, 2, item)
        item = QtGui.QTableWidgetItem(separator_text)
        item.setFlags(QtCore.Qt.NoItemFlags)
        self.table.setItem(row, 3, item)
        item = QtGui.QTableWidgetItem(separator_text)
        item.setFlags(QtCore.Qt.NoItemFlags)
        self.table.setItem(row, 4, item)
        return named_item

    def _on_unsubscribe(self, title):
        source = self.sender()
        self._set_subscription(source, title, False)
    def _on_subscribe(self, title):
        source = self.sender()
        self._set_subscription(source, title, True)

    def _set_subscription(self, source, title, value):
        for row in range(0,self.table.rowCount()):
            if (self.table.item(row,0).text() == source.name() and
                self.table.item(row,1).text() == title):
                if(value):
                    brush = QtGui.QBrush(QtGui.QColor(230,255,230))
                else:
                    brush = QtGui.QBrush()
                for column in range(0,self.table.columnCount()):
                    self.table.item(row, column).setBackground(brush)
                                    
    def _center_widget(self, widget):
        w = QtGui.QWidget(self)
        hbox = QtGui.QHBoxLayout(w)
        hbox.setAlignment(QtCore.Qt.AlignCenter)
        hbox.setContentsMargins(0,0,0,0)
        hbox.addWidget(widget)
        return w

    def update(self):
        """Update the capacity bars"""
        for row in range(0,self.table.rowCount()):
            if self.item_is_group_header(self.table.item(row, 1)):
                continue
            item = self.table.item(row, 1)
            plotdata = item.data(QtCore.Qt.UserRole)
            bar = self.table.cellWidget(row, 2).findChild(QtGui.QProgressBar)
            bar.setMaximum(plotdata.maxlen)
            bar.setValue(len(plotdata))
            bar.setToolTip('%d/%d (%s allocated)' % (len(plotdata), plotdata.maxlen, _sizeof_fmt(plotdata.nbytes)))
            bar.setTextVisible(True)            
            
    def save_state(self, settings):
        """Save the current header state to disk"""
        settings.setValue("plotDataTable", self.table.horizontalHeader().saveState())

    def save_plotdata(self):
        """Save PlotData that are marked for saving"""
        pd_settings = []
        for row in range(0,self.table.rowCount()):
            if self.item_is_group_header(self.table.item(row, 1)):
                continue
            # Check if this row is marked for saving
            checkbox = self.table.cellWidget(row, 3).findChild(QtGui.QCheckBox)
            item = self.table.item(row, 1)
            plotdata = item.data(QtCore.Qt.UserRole)
            pd_settings.append(plotdata.save_state(save_data=checkbox.isChecked()))
        return pd_settings

    def restore_state(self, settings):
        """Restores the a previous header state"""
        state = settings.value('plotDataTable')
        if(state is not None):
            self.table.horizontalHeader().restoreState(state)

    def record_titles(self, is_recording):
        titles = {}
        for row in range(0, self.table.rowCount()):
            if self.item_is_group_header(self.table.item(row, 1)):
                continue
            #Check if this row is marked for recording
            checkbox = self.table.cellWidget(row,4).findChild(QtGui.QCheckBox)
            item = self.table.item(row,0)
            source = item.data(QtCore.Qt.UserRole)
            item = self.table.item(row,1)
            plotdata = item.data(QtCore.Qt.UserRole)
            if plotdata.ishistory:
                checkbox.setDisabled(is_recording)
                checkbox.setChecked(1)
            if(not checkbox.isChecked()):
                continue
            if source.name() not in titles:
                titles[source.name()] = []
            titles[source.name()].append(plotdata._title)
            plotdata.recordhistory = is_recording
        return titles
        
    def _on_selection_changed(self):
        table = self.sender()
        if(len(table.selectedItems())):
            self.buffer_size.setEnabled(True)
            self.buffer_spin.setEnabled(True)
            self.clear_buffer.setEnabled(True)
            row = table.currentRow()
            item = table.item(row, 1)
            if self.item_is_group_header(item):
                return
            plotdata = item.data(QtCore.Qt.UserRole)
            self.buffer_spin.setValue(plotdata.maxlen)
        else:
            self.buffer_size.setEnabled(False)
            self.buffer_spin.setEnabled(False)
            self.clear_buffer.setEnabled(False)

    def _on_double_click(self, row, column):
        item = self.table.item(row, 1)
        if self.item_is_group_header(item):
            return
        plotdata = item.data(QtCore.Qt.UserRole)
        data_type = plotdata._parent.data_type[plotdata.title]
        mwindow = self.window()
        if data_type in ImageWindow.acceptable_data_types:
            w = ImageWindow(mwindow)
        elif data_type in PlotWindow.acceptable_data_types:
            w = PlotWindow(mwindow)
        else:
            print('Unrecognized data_type:', data_type)
            return

        w.show()
        mwindow._data_windows.append(w)
        w.set_source_title(plotdata._parent, plotdata.title)

    def _on_buffer_size_clicked(self):
        table = self.table
        row = table.currentRow()
        item = table.item(row, 1)
        plotdata = item.data(QtCore.Qt.UserRole)
        plotdata.resize(self.buffer_spin.value())

    def _on_clear_buffer_clicked(self):
        table = self.table
        row = table.currentRow()
        item = table.item(row, 1)
        plotdata = item.data(QtCore.Qt.UserRole)
        plotdata.clear()

def _sizeof_fmt(num, suffix='B'):
    for unit in ['','K','M','G','T','P','E','Z']:
        if abs(num) < 1024.0:
            if unit == '':
                return "%d %s%s" % (num, unit, suffix)
            else:
                return "%3.1f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f %s%s" % (num, 'Yi', suffix)
