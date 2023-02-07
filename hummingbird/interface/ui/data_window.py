# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
"""Base class for all the data display windows"""
import logging

from ..Qt import QtCore, QtGui


class DataWindow(QtGui.QMainWindow):
    """Base class for all the data display windows
    (e.g. PlotWindow, ImageWindow)"""
    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, None)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self._enabled_sources = {}
        self.settings = QtCore.QSettings()
        self.setupUi(self)
        self.alertBlinkTimer = QtCore.QTimer()
        self.alertBlinkTimer.setInterval(500)
        self._setup_connections()
        self._parent = parent
        # If True this DataWindow was restored from saved settings
        self.restored = False
        self.alertBlinking = False
        self.set_sounds_and_volume()

    # This is to fix a resizing bug on Mac
    def resizeEvent(self, event):
        QtGui.QMainWindow.resizeEvent(self, event)
        QtGui.QApplication.processEvents()
        
    def _setup_connections(self):
        """Initialize connections"""
        self.menuData_Sources.aboutToShow.connect(self.on_menu_show)
        self.actionSaveToPNG.triggered.connect(self.on_save_to_png)
        self.actionSaveToPNG.setShortcut(QtGui.QKeySequence("Ctrl+P"))
        self.alertBlinkTimer.timeout.connect(self.blink_alert)
        self.title.installEventFilter(self);
        self.timeLabel.installEventFilter(self);
        self.dateLabel.installEventFilter(self);
        
    def _finish_layout(self):
        """This is called after the derived classes finish settings up so
        that the lower common section of the window can be setup. Kinda ugly."""
        layout = QtGui.QVBoxLayout(self.plotFrame)
        layout.addWidget(self.plot)
        self.plot_title = str(self.title.text())
        self.title.textChanged.connect(self._on_title_change)

    def _on_title_change(self, title):
        """Change the name of the data window"""
        self.plot_title = str(title)

    def on_menu_show(self):
        """Show what data sources are available"""
        # Go through all the available data sources and add them
        def add_menu(title, menu, ds):
            action = QtGui.QAction(title, self)
            action.setData([ds, title])
            action.setCheckable(True)
            if (ds in self._enabled_sources and
                title in self._enabled_sources[ds]):
                action.setChecked(True)
            else:
                action.setChecked(False)
            menu.addAction(action)
            action.triggered.connect(self._source_title_triggered)
            
        self.menuData_Sources.clear()
        for ds in self._parent.data_sources:
            menu = self.menuData_Sources.addMenu(ds.name())
            if ds.titles is not None:
                for name in sorted(ds.group_structure.keys()):
                    item_list = ds.group_structure[name]
                    items_of_right_type = [item for item in item_list if ds.data_type[item] in self.acceptable_data_types]
                    if len(items_of_right_type) == 0:
                        continue
                    if name is None:
                        submenu = menu
                    else:
                        submenu = menu.addMenu(name)
                    for item in sorted(items_of_right_type):
                        add_menu(item, submenu, ds)

    def set_sounds_and_volume(self):
        self.soundsGroup = QtGui.QActionGroup(self.menuSounds)
        self.soundsGroup.setExclusive(True)
        self.actionBeep.setActionGroup(self.soundsGroup)
        self.actionBeep.triggered.connect(self.toggle_sounds)
        self.actionClick.setActionGroup(self.soundsGroup)
        self.actionClick.triggered.connect(self.toggle_sounds)
        self.actionPunch.setActionGroup(self.soundsGroup)
        self.actionPunch.triggered.connect(self.toggle_sounds)
        self.actionWhack.setActionGroup(self.soundsGroup)
        self.actionWhack.triggered.connect(self.toggle_sounds)
        self.actionSharp.setActionGroup(self.soundsGroup)
        self.actionSharp.triggered.connect(self.toggle_sounds)
        self.actionGlass.setActionGroup(self.soundsGroup)
        self.actionGlass.triggered.connect(self.toggle_sounds)
        self.sound = 'beep'
        
        self.volumeGroup = QtGui.QActionGroup(self.menuVolume)
        self.volumeGroup.setExclusive(True)
        self.actionHigh.setActionGroup(self.volumeGroup)
        self.actionHigh.triggered.connect(self.toggle_volume)
        self.actionMedium.setActionGroup(self.volumeGroup)
        self.actionMedium.triggered.connect(self.toggle_volume)
        self.actionLow.setActionGroup(self.volumeGroup)
        self.actionLow.triggered.connect(self.toggle_volume)
        self.volume = 1

    def get_time(self, index=None):
        """Returns the time of the given index, or the time of the last data point"""
        if index is None:
            index = self.current_index
        # Check if we have last_vector
        if(self.last_vector_x is not None):
            dt = datetime.datetime.fromtimestamp(self.last_vector_x[index])
            return dt

        # Check if we have enabled_sources
        source = None
        if(self._enabled_sources):
            for ds in self._enabled_sources.keys():
                if(len(self._enabled_sources[ds])):
                    title = self._enabled_sources[ds][0]
                    source = ds
                    break

        # There might be no data yet, so no plotdata
        if(source is not None and title in source.plotdata and
           source.plotdata[title].x is not None):
            pd = source.plotdata[title]
            dt = datetime.datetime.fromtimestamp(pd.x[index])
            return dt
        else:
            return datetime.datetime.now()

    def on_save_to_png(self):
        """Save a screenshot of the window"""
        dt = self.get_time()
        self.timeLabel.setText('%02d:%02d:%02d.%03d' % (dt.hour, dt.minute, dt.second, dt.microsecond/1000))
        timestamp = '%04d%02d%02d_%02d%02d%02d' %(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)
        print(self.settings.value("outputPath") + '/' + timestamp + '_' + self.plot_title + '.png')
        # QtGui.QPixmap.grabWidget(self).save(self.settings.value("outputPath") + '/' +
        #                                     timestamp + '.png', 'png', quality=100)
        self.grab().save(self.settings.value("outputPath") + '/' +
                         timestamp + '.png', 'png', quality=100)

    def _source_title_triggered(self):
        """Enable/disable a data source"""
        action = self.sender()
        source, title = action.data()
        self.set_source_title(source, title, action.isChecked())

    def set_source_title(self, source, title, enable=True):
        """Enable/disable a given broadcast"""
        if(enable):
            if(self.exclusive_source and self._enabled_sources):
                for s, t in self.source_and_titles():
                    self._enabled_sources[source].remove(t)
                    s.unsubscribe(t, self)
            source.subscribe(title, self)
            if(source in  self._enabled_sources):
                self._enabled_sources[source].append(title)
            else:
                self._enabled_sources[source] = [title]
            self.title.setText(str(title))
        else:
            source.unsubscribe(title, self)
            self._enabled_sources[source].remove(title)

    def closeEvent(self, event):
        """Unsubscribe to any remaining broadcasts before closing"""
        # Unsibscribe all everything
        logging.debug("Closing DataWindow %s" % (self))
        for source in self._enabled_sources.keys():
            for title in self._enabled_sources[source]:
                source.unsubscribe(title, self)
        # Remove myself from the interface plot list
        # otherwise we'll be called also on replot
        self._parent.data_windows.remove(self)
        event.accept()

    def source_and_titles(self):
        """Iterate through all available broadcasts"""
        for source in self._enabled_sources.keys():
            for title in self._enabled_sources[source]:
                yield source, title

    def get_state(self, settings):
        """Returns settings that can be used to restore the widget to the current state"""
        enabled_sources = []
        for source, title in self.source_and_titles():
            enabled_sources.append({'hostname': source.hostname,
                                    'port': source.port,
                                    'tunnel': source.ssh_tunnel,
                                    'title': title})
        settings['geometry'] = self.saveGeometry()
        settings['windowState'] = self.saveState()
        settings['enabled_sources'] = enabled_sources
        settings['window title'] = str(self.title.text())
        settings['title font'] = self.title.font()
        settings['date font'] = self.dateLabel.font()
        settings['time font'] = self.timeLabel.font()
        settings['alert'] = self.actionToggleAlert.isChecked()
        return settings

    def restore_from_state(self, settings, data_sources):
        """Restores the widget to the same state as when the settings were generated"""
        for es in settings['enabled_sources']:
            for ds in data_sources:
                if(ds.hostname == es['hostname'] and
                   ds.port == es['port'] and
                   ds.ssh_tunnel == es['tunnel']):
                    source = ds
                    title = es['title']
                    self.set_source_title(source, title)
        self.restoreGeometry(settings['geometry'])
        self.restoreState(settings['windowState'])
        self.title.setText(settings['window title'])
        self.title.setFont(settings['title font'])
        self.dateLabel.setFont(settings['date font'])
        self.timeLabel.setFont(settings['time font'])
        self.actionToggleAlert.setChecked(settings['alert'])
        self.show()
        self.restored = True
        logging.debug("Loaded %s from settings", type(self).__name__)
        
    def blink_alert(self):
        if self.alertBlinking:
            self.setStyleSheet("");
        else:
            self.setStyleSheet("QMainWindow{background-color: #ef2929;}");
        self.alertBlinking = not self.alertBlinking

    def toggle_sounds(self):
        self.sound = str(self.soundsGroup.checkedAction().text())

    def toggle_volume(self):
        volume = str(self.volumeGroup.checkedAction().text())
        if volume == "High":
            self.volume = 10
        elif volume == "Medium":
            self.volume = 1
        elif volume == "Low":
            self.volume = 0.1

            
    def eventFilter(self, obj, event):
        if obj == self.title:
            if event.type() == QtCore.QEvent.MouseButtonDblClick:
                print(obj.font())
                font, ok = QtGui.QFontDialog.getFont(obj.font())
                if ok:
                    obj.setFont(font)
                return True
        if obj == self.timeLabel or obj == self.dateLabel:
            if event.type() == QtCore.QEvent.MouseButtonDblClick:
                font, ok = QtGui.QFontDialog.getFont(obj.font())
                if ok:
                    obj.setFont(font)
                return True
                
        return False
