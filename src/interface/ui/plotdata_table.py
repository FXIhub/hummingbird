"""A table to show the available PlotData"""

from interface.Qt import QtGui, QtCore

class PlotDataTable(QtGui.QWidget):
    """A table to show the available PlotData"""
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        label = QtGui.QLabel('<center><b>Data Sources</b></center>')
        vbox = QtGui.QVBoxLayout(self)
        vbox.addWidget(label)

        self.table = QtGui.QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(['Backend', 'Title','Buffer Capacity','Subscribed'])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setHighlightSections(False)
        self.table.verticalHeader().hide()
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.table.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        vbox.addWidget(self.table)
        hbox = QtGui.QHBoxLayout()
        hbox.addStretch()
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
        source.unsubscribed.connect(self._on_unsubscribe)
        source.subscribed.connect(self._on_subscribe)
        
    def _on_plotdata_added(self, plotdata):
        source = self.sender()
        self.add_row(source, plotdata)

    def add_row(self, source, plotdata):
        row = self.table.rowCount()
        self.table.insertRow(row)
        item = QtGui.QTableWidgetItem(source.name())
        item.setData(QtCore.Qt.UserRole, source)
        self.table.setItem(row, 0, item)
        item = QtGui.QTableWidgetItem(plotdata.title)
        item.setData(QtCore.Qt.UserRole, plotdata)
        self.table.setItem(row, 1, item)
        bar = QtGui.QProgressBar()        
        self.table.setItem(row, 2, QtGui.QTableWidgetItem())
        self.table.setCellWidget(row, 2, self._center_widget(bar))
        checkbox = QtGui.QCheckBox()
        item = QtGui.QTableWidgetItem()
        self.table.setItem(row, 3, item)
        self.table.setCellWidget(row, 3, self._center_widget(checkbox))
        if(plotdata.title in source.subscribed_titles):
            checkbox.setChecked(True)
        checkbox.toggled.connect(self._on_subscribe_clicked)
        checkbox.item = item

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
                self.table.cellWidget(row,3).findChild(QtGui.QCheckBox).setChecked(value)
                                    
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

    def restore_state(self, settings):
        """Restores the a previous header state"""
        state = settings.value('plotDataTable')
        if(state is not None):
            self.table.horizontalHeader().restoreState(state)

    def _on_subscribe_clicked(self):
        checkbox = self.sender()
        row = checkbox.item.row()
        source = self.table.item(row, 0).data(QtCore.Qt.UserRole)
        title = self.table.item(row, 1).text()
        if(checkbox.isChecked()):
            source._data_socket.subscribe(bytes(title))
        else:
            source._data_socket.unsubscribe(bytes(title))
        
    def _on_selection_changed(self):
        table = self.sender()
        if(len(table.selectedItems())):      
            self.buffer_size.setEnabled(True)
            self.buffer_spin.setEnabled(True)
            row = table.currentRow()
            item = table.item(row, 1)
            plotdata = item.data(QtCore.Qt.UserRole)
            self.buffer_spin.setValue(plotdata.maxlen)
        else:
            self.buffer_size.setEnabled(False)
            self.buffer_spin.setEnabled(False)

    def _on_buffer_size_clicked(self):
        table = self.table
        row = table.currentRow()
        item = table.item(row, 1)
        plotdata = item.data(QtCore.Qt.UserRole)
        plotdata.resize(self.buffer_spin.value())

def _sizeof_fmt(num, suffix='B'):
    for unit in ['','K','M','G','T','P','E','Z']:
        if abs(num) < 1024.0:
            if unit == '':
                return "%d %s%s" % (num, unit, suffix)
            else:
                return "%3.1f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f %s%s" % (num, 'Yi', suffix)
