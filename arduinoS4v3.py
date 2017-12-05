# Import Icons
import os
# Import time for x axis
import time
import qrc_resources
# Import Graphics Library
import pyqtgraph as pg
# TODO pause recording when saving data?
# TODO reset time (x axis) when recording & refresh plot (done but needs code revision)
# TODO bar color restore preferences
# Import for reading Arduino
import serial
# Import device list library
import serial.tools.list_ports
from PyQt4.QtCore import (QThread, QTimer, QMutex, QRegExp, Qt, QSettings, QVariant, QRectF)
from PyQt4.QtGui import (QFileDialog, QGridLayout, QWidget,
                         QMainWindow, QAction, QIcon, QKeySequence,
                         QVBoxLayout, QLabel, QDialog, QDialogButtonBox,
                         QLineEdit, QCheckBox, QRegExpValidator, QFrame,
                         QDoubleSpinBox, QComboBox, QMessageBox, QProgressDialog)
from copy import copy

# Global vars
mutex = QMutex()
time_start = None
x_arr = []
y_arr = []
arduino_connected = False


# Main Windows
class Window(QMainWindow):
    def __init__(self, parent=None):
        super(Window, self).__init__(parent)
        global time_start, x_arr, y_arr, arduino_connected
# Flag variables
        self.filename = ''
        self.array_len = len(x_arr)
        self.clean_recorded_data = True
        self.recording_status = False
        self.file_saved = False
        self.recorded_list = []
        self.record_cell_start = None
        self.record_cell_end = None
        self.follow_plot = True
        self.plot = True
# Window Properties
        self.setWindowTitle("Arduino Plotter")
        self.setWindowIcon(QIcon(":/window_icon.png"))
        self.resize(800, 600)
# Plot Settings and Creation
        self.plot_settings = dict(plotLineWidth=1, horizontalGrid=True, verticalGrid=True, gridOpacity=1, lineColor='b',
                                  arrayPlotSize=25, serialBaud=115200, separator=' ')
        pg.setConfigOption('background', 'w')
        self.load_settings()
        self.createPlot()
# Create Bars
        self.createBars()
# Get list of arduino devices
        self.updateDevicesList()
# Add Widgets to Main Window
        self.addWidgets()
# Add bar to display status messages
        status = self.statusBar()
        self.sizeLabel = QLabel()
        self.sizeLabel.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        status.addPermanentWidget(self.sizeLabel)

        status.setSizeGripEnabled(False)

# Start Thread & program time count(x axis)
        time_start = time.time()
        self.read_serial_thread = ReadSerialThread(self.arduino_combobox.currentText(),
                                                   self.plot_settings['serialBaud'], self)
        self.read_serial_thread.start()
        self.update()

    def load_settings(self):
        settings = QSettings()
        self.plot_settings['horizontalGrid'] = settings.value("horizontalGrid",
                                                              self.plot_settings['horizontalGrid']).toBool()
        self.plot_settings['verticalGrid'] = settings.value("verticalGrid", self.plot_settings['verticalGrid']).toBool()
        self.plot_settings['plotLineWidth'] = settings.value("plotLineWidth",
                                                             self.plot_settings['plotLineWidth']).toInt()[0]
        self.plot_settings['gridOpacity'] = settings.value("gridOpacity",
                                                            self.plot_settings['gridOpacity']).toFloat()[0]
        self.plot_settings['lineColor'] = unicode(settings.value("lineColor",
                                                                 self.plot_settings['lineColor']).toString())
        self.plot_settings['arrayPlotSize'] = settings.value("arrayPlotSize",
                                                             self.plot_settings['arrayPlotSize']).toInt()[0]
        self.plot_settings['serialBaud'] = settings.value("serialBaud",
                                                              self.plot_settings['serialBaud']).toInt()[0]
        self.plot_settings['separator'] = settings.value("separator", self.plot_settings['separator']).toString()

# Save settings values
    def closeEvent(self, event):
        settings = QSettings()
        settings.setValue('horizontalGrid', QVariant(self.plot_settings['horizontalGrid']))
        settings.setValue('verticalGrid', QVariant(self.plot_settings['verticalGrid']))
        settings.setValue('plotLineWidth', QVariant(self.plot_settings['plotLineWidth']))
        settings.setValue('gridOpacity', QVariant(self.plot_settings['gridOpacity']))
        settings.setValue('lineColor', QVariant(self.plot_settings['lineColor']))
        settings.setValue('arrayPlotSize', QVariant(self.plot_settings['arrayPlotSize']))
        settings.setValue('serialBaud', QVariant(self.plot_settings['serialBaud']))
        settings.setValue('separator', QVariant(self.plot_settings['separator']))


# Plot Creation
    def createPlot(self):
        self.plot_zone = pg.PlotWidget()
        self.pen = pg.mkPen(width=self.plot_settings['plotLineWidth'], color=self.plot_settings['lineColor'][0])
        self.plot_zone.plotItem.showGrid(self.plot_settings['verticalGrid'], self.plot_settings['horizontalGrid'],
                                        self.plot_settings['gridOpacity'])
        self.plot_zone.plotItem.ctrlMenu = None
        self.plot_zone.setAutoPan(True)
        # self.plot_zone.plotItem.ctrlMenu
        # self.plot_zone.plotItem.enableAutoRange(enable=0.2)
        # self.plot_zone.autoRange()
        self.plot_zone.setXRange(0, 600)
        # self.plot_zone.setLabels(left=('Signal', 'V'), bottom=('Time'))
        self.plot_zone.setYRange(0, 5)
#        self.plot_zone.setMouseEnabled(x=False)
        self.plot_zone.scene().contextMenu = None

# Create Bars
# TODO Add Info button
    def createBars(self):
        # Create Bar1
        controls_toolbar = self.addToolBar("Controls")
        controls_toolbar.setObjectName("ControlsToolBar")
        # Create Bar2
        arduino_toolbar = self.addToolBar("Arduino")
        arduino_toolbar.setObjectName("ArduinoToolBar")
        # Add Elements to Bar1
        # Record & Pause
        self.record_pause = QAction(QIcon(":/rec.png"), "&Rec", self)
        self.record_pause.setShortcut("Ctrl+R")
        self.record_pause.setToolTip('Record')
        self.record_pause.triggered.connect(self.recording)
        # Stop
        self.stop = QAction(QIcon(":/stop.png"), "&Detener", self)
        self.stop.setShortcut("Ctrl+Alt+D")
        self.stop.setToolTip('Stop')
        self.stop.triggered.connect(self.stopRecording)
        # Save
        self.save_file = QAction(QIcon(":/save.png"), "&Save", self)
        self.save_file.setShortcut(QKeySequence.Save)
        self.save_file.setToolTip('Save')
        self.save_file.triggered.connect(self.saveFile)
        # Save As
        self.save_as = QAction(QIcon(":/save_as.png"), "Save As", self)
        self.save_as.setShortcut(QKeySequence.SaveAs)
        self.save_as.setToolTip('Save As')
        self.save_as.triggered.connect(self.saveFileAs)
        # Configurations
        self.configurations = QAction(QIcon(":/configs.png"), "&Configurations", self)
        self.configurations.setShortcut("Ctrl+Alt+S")
        self.configurations.setToolTip('Settings')
        self.configurations.triggered.connect(self.changeSettings)

        # Add buttons to bar
        controls_toolbar.addAction(self.record_pause)
        controls_toolbar.addAction(self.stop)
        controls_toolbar.addAction(self.save_file)
        controls_toolbar.addAction(self.save_as)
        controls_toolbar.addAction(self.configurations)

        # Arduino ComboBox
        self.arduino_combobox = QComboBox()
        self.arduino_combobox.setToolTip('Select Arduino')
        self.arduino_combobox.setFocusPolicy(Qt.NoFocus)
        self.arduino_combobox.activated.connect(self.updateChoosenArduino)

        # Update List of Arduino devices
        self.reload = QAction(QIcon(":/reload.png"), "Reload", self)
        self.reload.setShortcut(QKeySequence.Refresh)
        self.reload.setToolTip('Reload Devices')
        self.reload.triggered.connect(self.updateDevicesList)
        # Timer Label
        self.timer_label = QLabel()
        self.timer_label.setText(' 00:00')

        # Info button for dialog
        self.info = QAction(QIcon(":/info.png"), "Reload", self)
        self.info.setShortcut(QKeySequence.HelpContents)
        self.info.setToolTip('Help')
        self.info.triggered.connect(self.showInfo)

        # Follow checkbox
        self.follow_label = QLabel("Follow Plot")
        self.follow_checkbox = QCheckBox()
        # self.arduino_combobox.setToolTip('Select Arduino')
        self.follow_checkbox.setFocusPolicy(Qt.NoFocus)
        self.follow_checkbox.clicked.connect(self.change_follow_status)
        self.follow_checkbox.setChecked(True)

        arduino_toolbar.addWidget(self.arduino_combobox)
        arduino_toolbar.addAction(self.reload)
        arduino_toolbar.addWidget(self.timer_label)
        arduino_toolbar.addAction(self.info)
        arduino_toolbar.addWidget(self.follow_checkbox)
        arduino_toolbar.addWidget(self.follow_label)

# Show Info(Help) dialog
    def showInfo(self):
        self.info_dialog = InfoDialog(self)
        self.info_dialog.show()

    def change_follow_status(self):
        if self.follow_checkbox.isChecked():
            self.follow_plot = True
        else:
            self.follow_plot = False



# Update arduino list

    def updateDevicesList(self):
        device_list = serial.tools.list_ports.comports()
        current_arduino = self.arduino_combobox.currentText()
        self.arduino_combobox.clear()
        device_index = 0
        for device in sorted(device_list):
            self.arduino_combobox.addItem(device.device)
            if device.device == current_arduino:
                self.arduino_combobox.setCurrentIndex(device_index)
            device_index = device_index + 1

# Update selected arduino

    def updateChoosenArduino(self):
        self.restart_values()

# Add Widgets
    def addWidgets(self):
        self.widget = QWidget()
        self.setCentralWidget(self.widget)
        vbox_layout = QVBoxLayout()
        vbox_layout.addWidget(self.plot_zone)
        vbox_layout.setContentsMargins(5, 5, 5, 0)
        self.widget.setLayout(vbox_layout)

# Saves indexes of recorded items, thus saves memory
    def recording(self):
        global time_start, x_arr, y_arr, arduino_connected
        status = self.statusBar()
# If recording is "Stopped" clear data and start recording
        if self.clean_recorded_data:
            mutex.lock()
            del self.recorded_list[:]
            del x_arr[:]
            del y_arr[:]
            self.array_len = 0
            self.clean_recorded_data = False
            mutex.unlock()
            width_visible = self.plot_zone.visibleRange().width()
            height_visible = self.plot_zone.visibleRange().height()
            bottom_visible = self.plot_zone.visibleRange().top()
            # self.plot_zone.visibleRange().setRect(0, 0, 150, 10)
            # print self.plot_zone.visibleRange()
            rect_me = QRectF(0, 0, width_visible, 5)
            self.plot_zone.setRange(rect=rect_me, disableAutoRange=True,
                                    xRange=(0, (0 + width_visible)), padding=0,
                                    yRange=(bottom_visible, bottom_visible + height_visible))

# Start Recording
        if not self.recording_status:
            self.record_pause.setIcon(QIcon(':/pause.png'))
            status.showMessage('Recording')
            mutex.lock()
            if x_arr:
                self.record_cell_start = len(x_arr) - 1
            else:
                self.record_cell_start = len(x_arr)
            self.recording_status = True
            mutex.unlock()
        else:
            print "pause"
            # Pause Recording
            self.record_pause.setIcon(QIcon(':/rec.png'))
            status.showMessage('Paused')
            mutex.lock()
            # Check if x_arr has no data
            if x_arr:
                self.record_cell_end = len(x_arr) - 1
            else:
                self.record_cell_end = len(x_arr)

            self.recorded_list.append([self.record_cell_start, self.record_cell_end])
            print self.recorded_list
            self.recording_status = False
            mutex.unlock()

# Update Arduino status and plot

    def update(self):
        global x_arr, y_arr, arduino_connected
        if arduino_connected:
            self.sizeLabel.setText('Arduino Connected')
            self.sizeLabel.setStyleSheet('color:green')
            mutex.lock()
            x_copy = copy(x_arr)
            y_copy = copy(y_arr)
            mutex.unlock()
            if len(x_copy) - self.array_len >= 50 and len(x_copy) != 0 and self.plot:
                self.array_len = len(x_copy)
                try:
                    self.plot_zone.plot(x_copy[:-(self.plot_settings['arrayPlotSize'] + 1)],
                                        y_copy[:-(self.plot_settings['arrayPlotSize'] + 1)], clear=True, pen=self.pen)
                except Exception:
                    mutex.lock()
                    if len(x_arr) > len(y_arr):
                        trim = len(x_arr) - len(y_arr)
                        del x_arr[-trim:]
                    else:
                        trim = len(y_arr) - len(x_arr)
                        del y_arr[-trim:]
                    mutex.unlock()
                else:
                    if self.follow_plot:
                        if not (self.plot_zone.visibleRange().left() < x_copy[-1:][0] < self.plot_zone.visibleRange().right()):
                            width_visible = self.plot_zone.visibleRange().width()
                            height_visible = self.plot_zone.visibleRange().height()
                            bottom_visible = self.plot_zone.visibleRange().top()
                            rect_me = QRectF(x_copy[-1:][0], 0, width_visible, 5)
                            self.plot_zone.setRange(rect=rect_me, disableAutoRange=True,
                                                    xRange=(x_copy[-1:][0], ( x_copy[-1:][0] + width_visible )), padding=0,
                                                    yRange=(bottom_visible, bottom_visible + height_visible))


        else:
            self.sizeLabel.setText('Arduino Disconnected')
            self.sizeLabel.setStyleSheet('color:red')

        # Updates the GUI timer
        self.updateTimer()
        # Call myself every 100milliseconds
        timer = QTimer()
        timer.singleShot(100, self.update)



    def updateTimer(self):
        time_to_display = int(round(time.time() - time_start, 2))
        if time_to_display >= 60:
            self.timer_label.setText(' ' + str(time_to_display / 60) + ":" + str(time_to_display % 60))
        else:
            if len(str(time_to_display)) == 1:
                self.timer_label.setText(" " + '0' + ':0' + str(time_to_display))
            else:
                self.timer_label.setText(" " + '0' + ':' + str(time_to_display))


# Stops recording
    def stopRecording(self):
        mutex.lock()
        if self.recording_status:
            if x_arr:
                self.record_cell_end = len(x_arr) - 1
            else:
                self.record_cell_end = len(x_arr)
            self.recorded_list.append([self.record_cell_start, self.record_cell_end])
        mutex.unlock()
        self.clean_recorded_data = True
        self.recording_status = False

        self.record_pause.setIcon(QIcon(':/rec.png'))
        status = self.statusBar()
        status.showMessage('Stopped')

# Save file method
    def saveFile(self):
        print self.filename
        if not self.file_saved:
            self.saveFileAs()
        else:
            self.writeDataToFile('w')

# Save as method
    def saveFileAs(self):
        my_home = os.path.expanduser('~')
        self.filename = QFileDialog.getSaveFileName(self, 'Save As', os.path.join(my_home, "new_file.dat"), "", "", QFileDialog.DontUseNativeDialog)
        self.writeDataToFile('w')

# Write data to file
    def writeDataToFile(self, open_mode):
        global x_arr, y_arr
        try:
            list_x = []
            list_y = []
            listx = []
            listy = []
            if self.filename:
                file_obj = open(self.filename, open_mode)
                mutex.lock()
                x__copy = copy(x_arr)
                y__copy = copy(y_arr)
                mutex.unlock()

                for pair in self.recorded_list:
                    list_x.extend(x__copy[pair[0]:pair[1]])
                    list_y.extend(y__copy[pair[0]:pair[1]])


#                        file_obj.write(str(elem[0]) + self.plot_settings['separator'] + str(elem[1]) + '\n')
#                file_obj.close()
                progressDialog = QProgressDialog()
                progressDialog.setModal(True)
                progressDialog.setLabelText('Saving...')
                progressDialog.setMaximum(len(list_x))
                progressDialog.setCancelButton(None)
                #self.save_data = SaveDataThread(listx,
#                                                   listy, self.plot_settings['separator'], self.filename, self)
                #self.save_data.start()
                progressDialog.show()
                count = 0
                concat_string = ''
                mutex.lock()
                self.plot = False
                mutex.unlock()
                #print "%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%"
                for elem in zip(list_x, list_y):
#                       TODO Check if separator works
                    if count == 0:
                        print (elem[0], elem[1])
                    #print elem[0]
                    concat_string = concat_string + str(elem[0]) + str(self.plot_settings['separator'])\
                                    + str(elem[1]) + '\n'

                    progressDialog.setValue(count)
                    count += 1
                #file_obj.write(str(elem[0]) + self.plot_settings['separator'] + str(elem[1]) + '\n')
                file_obj.write(concat_string)
                count += 1
                self.file_saved = True
                mutex.lock()
                self.plot = True
                mutex.unlock()
        except (IOError, OSError) as error_file:
            message = QMessageBox.critical(self, 'Message', str(error_file), QMessageBox.Ok)
#           message.show()
            self.filename = ''
            self.file_saved = False
        finally:
            mutex.lock()
            self.plot = True
            mutex.unlock()


    def closedialog(self):
        pass

# Create and show settings dialog
    def changeSettings(self):
        self.settings_dialog = SettingsDialog(self.plot_settings, self.refreshSettings, self)
        self.settings_dialog.show()

# Refresh settings
    def refreshSettings(self):
        self.pen = pg.mkPen(width=self.plot_settings['plotLineWidth'], color=self.plot_settings['lineColor'][0])
        self.plot_zone.plotItem.showGrid(self.plot_settings['verticalGrid'], self.plot_settings['horizontalGrid'],
                                    self.plot_settings['gridOpacity'])

# Restart values and kills when new arduino connection is selected
    def restart_values(self):
        global x_arr, y_arr
        print ('killing')
        self.read_serial_thread.__del__()
        mutex.lock()
        self.array_len = 0
        del x_arr[:]
        del y_arr[:]
        #print x_arr
        del self.recorded_list[:]
        #print "clean"
        width_visible = self.plot_zone.visibleRange().width()
        height_visible = self.plot_zone.visibleRange().height()
        bottom_visible = self.plot_zone.visibleRange().top()
        # self.plot_zone.visibleRange().setRect(0, 0, 150, 10)
        #print self.plot_zone.visibleRange()
        rect_me = QRectF(0, 0, width_visible, 5)
        self.plot_zone.setRange(rect=rect_me, disableAutoRange=True,
                                xRange=(0, (0 + width_visible)), padding=0,
                                yRange=(bottom_visible, bottom_visible + height_visible))
        mutex.unlock()
        #print  "clean out"
        self.read_serial_thread = ReadSerialThread(self.arduino_combobox.currentText(),
                                                   self.plot_settings['serialBaud'], self)
        self.read_serial_thread.start()


# Thread class for reading serial input from Arduino
class ReadSerialThread(QThread):
    def __init__(self, current_arduino, serial_baud, parent=None):
        QThread.__init__(self, parent)
        self.current_arduino = current_arduino
        self.serial_baud = serial_baud

# Destroy Thread
    def __del__(self):
        try:
            self.serial_connection.close()
        except AttributeError:
            pass
        self.terminate()

# Call function that reads Arduino serial input
    def run(self):
        while True:
            try:
                try:
                    # Waits input for 1 sec
                    self.serial_connection = serial.Serial(unicode(self.current_arduino), self.serial_baud, timeout=1)
                    self.readSerialData()

                except serial.SerialException:
                    time.sleep(2)
            # Raises if connection couldn't be established
            except AttributeError:
                pass

# Reads arduino data and time of each read
    def readSerialData(self):
        global arduino_connected
        try:
            mutex.lock()
            arduino_connected = True
            mutex.unlock()
            while True:
                # Read arduino data from serial
                serial_data = self.serial_connection.readline()
                mutex.lock()
                try:
#                    print (serial_data)
#                    sec, data =serial_data.split(',')
#                    print x_arr
#                    print serial_data
                    if not x_arr:
                        #x_arr.append(0.5)
                        x_arr.extend([0.1])
                    else:
                        #x_arr.append(x_arr[-1:][0] + 0.5)
                        x_arr.extend([x_arr[-1:][0] + 0.1])
#                    print (x_arr[-1:], serial_data)
                except ValueError:
                    pass
                except IOError:
                    pass
                else:
                    try:
                        adc = (float(str(serial_data).replace('\r\n', '')) * 5) / 1023
                        y_arr.extend([adc])
                    # Raised when garbage was present on the data, deletes the last appended item to preserve
                    # arrays of the same size
                    except ValueError:
                        x_arr.pop()
                        #mutex.unlock()
                    except UnboundLocalError:
                        pass
                mutex.unlock()

        # Raised when connection is lost
        except serial.SerialException:
            print "close"
            mutex.lock()
            try:
                self.serial_connection.close()
            except OSError:
                pass
            arduino_connected = False
            mutex.unlock()


# Settings dialog class, settings is dictionary with settings values, callback
# is used to applay settings
class SettingsDialog(QDialog):
    def __init__(self, settings, callback, parent=None):
        super(SettingsDialog, self).__init__(parent)
        # Function to apply changes
        self.callback = callback
        self.settings = settings
        # Dialog properties
        self.resize(320, 190)
        self.setWindowTitle('Settings')
        # Create, connect and add Widgets
        self.createWidgets()
        self.createConnections()
        self.addWidgets()

    def createWidgets(self):
        numeric_reg = QRegExp(r"[0-9]+")
        self.line_width_label = QLabel('Line Width')
        self.line_width_edit = QLineEdit()
        self.line_width_edit.setValidator(QRegExpValidator(numeric_reg, self))
        self.line_width_edit.setText(str(self.settings['plotLineWidth']))

        self.horizontal_grid_label = QLabel('Horizontal Grid')
        self.horizontal_grid_checkbox = QCheckBox()
        self.horizontal_grid_checkbox.setChecked(self.settings['horizontalGrid'])

        self.vertical_grid_label = QLabel('Vertical Grid')
        self.vertical_grid_checkbox = QCheckBox()
        self.vertical_grid_checkbox.setChecked(self.settings['verticalGrid'])

        self.grid_opacity_label = QLabel('Line Opacity')
        self.grid_opacity_spinbox = QDoubleSpinBox()
        self.grid_opacity_spinbox.setRange(0.10, 1.00)
        self.grid_opacity_spinbox.setSingleStep(0.10)
        self.grid_opacity_spinbox.setValue(float(self.settings['gridOpacity']))
        self.grid_opacity_spinbox.setFocusPolicy(Qt.NoFocus)

        self.line_color_label = QLabel('Line Color')
        self.line_color_combo = QComboBox()
        self.line_color_combo.addItem('blue')
        self.line_color_combo.addItem('cyan')
        self.line_color_combo.addItem('green')
        self.line_color_combo.addItem('magenta')
        self.line_color_combo.addItem('white')
        self.line_color_combo.addItem('yellow')
        print self.settings['lineColor']
        self.line_color_combo.setCurrentIndex(self.line_color_combo.findText(self.settings['lineColor']))

        self.serial_baud_label = QLabel('Serial Baud')
        self.serial_baud_edit = QLineEdit()
        self.serial_baud_edit.setText(str(self.settings['serialBaud']))
        self.serial_baud_edit.setValidator(QRegExpValidator(numeric_reg, self))

        self.separator_label = QLabel('Separator')
        self.separator_edit = QLineEdit()
        self.separator_edit.setText(self.settings['separator'])
        self.separator_edit.setInputMask('X')

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Apply|
                                          QDialogButtonBox.Close|QDialogButtonBox.RestoreDefaults)

# Connect elements to their events
    def createConnections(self):
        self.buttonBox.button(QDialogButtonBox.Apply).clicked.connect(self.apply)
        self.buttonBox.button(QDialogButtonBox.Apply).setDefault(True)
        self.buttonBox.button(QDialogButtonBox.Apply).setAutoDefault(True)
        self.buttonBox.rejected.connect(self.reject)
        self.buttonBox.button(QDialogButtonBox.RestoreDefaults).clicked.connect(self.restore_defaults)
        self.buttonBox.button(QDialogButtonBox.RestoreDefaults).setDefault(False)
        self.buttonBox.button(QDialogButtonBox.RestoreDefaults).setAutoDefault(False)

# Add elements to the GUI
    def addWidgets(self):
        grid = QGridLayout()
        grid.addWidget(self.line_width_label, 0, 0)
        grid.addWidget(self.line_width_edit, 0, 1)
        grid.addWidget(self.horizontal_grid_label, 1, 0)
        grid.addWidget(self.horizontal_grid_checkbox, 1, 1)
        grid.addWidget(self.vertical_grid_label, 2, 0)
        grid.addWidget(self.vertical_grid_checkbox, 2, 1)
        grid.addWidget(self.grid_opacity_label, 3, 0)
        grid.addWidget(self.grid_opacity_spinbox, 3, 1)
        grid.addWidget(self.line_color_label, 4, 0)
        grid.addWidget(self.line_color_combo, 4, 1)
        grid.addWidget(self.serial_baud_label, 5, 0)
        grid.addWidget(self.serial_baud_edit, 5, 1)
        grid.addWidget(self.separator_label, 6, 0)
        grid.addWidget(self.separator_edit, 6, 1)
        grid.addWidget(self.buttonBox, 7, 0, 1, 2)

        self.setLayout(grid)

# Apply new Settings
    def apply(self):
#        dict(plotLineWidth=1, horizontalGrid=True, verticalGrid=True, gridOpacity=1, lineColor='b',
#             arrayPlotSize=25, updatePlotTime=1)
        self.settings['plotLineWidth'] = int(self.line_width_edit.text())
        self.settings['horizontalGrid'] = self.horizontal_grid_checkbox.isChecked()
        self.settings['verticalGrid'] = self.vertical_grid_checkbox.isChecked()
        self.settings['gridOpacity'] = float(self.grid_opacity_spinbox.value())
        self.settings['lineColor'] = unicode(self.line_color_combo.currentText())
        self.settings['serialBaud'] = int(self.serial_baud_edit.text())
        if len(self.separator_edit.text()) != 1:
            self.settings['separator'] = ' '
        else:
            self.settings['separator'] = unicode(self.separator_edit.text())
        self.callback()

# Restores default settings values
    def restore_defaults(self):
        default_values = dict(plotLineWidth=1, horizontalGrid=True, verticalGrid=True, gridOpacity=1, lineColor='b',
             arrayPlotSize=25, serialBaud=115200, separator=' ')
        self.settings.update(default_values)
        self.callback()
        self.line_width_edit.setText(str(self.settings['plotLineWidth']))
        self.horizontal_grid_checkbox.setChecked(self.settings['horizontalGrid'])
        self.vertical_grid_checkbox.setChecked(self.settings['verticalGrid'])
        self.grid_opacity_spinbox.setValue(self.settings['gridOpacity'])
        self.line_color_combo.setCurrentIndex(0)
        self.serial_baud_edit.setText(str(self.settings['serialBaud']))
        self.separator_edit.setText(self.settings['separator'])


class InfoDialog(QDialog):
    def __init__(self, parent=None):
        super(InfoDialog, self).__init__(parent)
        self.createWidgets()
        self.addWidgets()

    def createWidgets(self):
        self.title_label = QLabel('Arduino ARP Plotter, written in Python2.7 and PyQT')
        self.programmer_label = QLabel('Programmer: Francisco Rafael Huesca Morales')
        self.programmer_email_label = QLabel('Email: pacohm94@gmail.com')
        self.rights = QLabel("Copyright 2017")
        self.github = QLabel('<a href="https://github.com/packituz-gttz/ARP-ArduinoPlotter">Github</a>')
        self.github.setOpenExternalLinks(True)

    def addWidgets(self):
        grid = QGridLayout()
        grid.addWidget(self.title_label, 0, 0)
        grid.addWidget(self.programmer_label, 1, 0)
        grid.addWidget(self.programmer_email_label, 2, 0)
        grid.addWidget(self.rights, 3, 0)
        grid.addWidget(self.github, 4, 0)
        self.setLayout(grid)


class SaveDataThread(QThread):
    def __init__(self, listx, listy, separator, filename, parent=None):
        QThread.__init__(self, parent)
        self.listx = listx
        self.listy = listy
        self.separator = separator
        self.filename = filename


# Destroy Thread
    def __del__(self):
        self.terminate()

    def run(self):

        try:
            print self.filename
            file_obj = open(self.filename, 'w')

            complete = len(self.listx)
            for elem in zip(self.listx, self.listy):
                print elem[0]
                print elem[1]
                file_obj.write(str(elem[0]) + self.separator + str(elem[1]) + '\n')
        except (OSError, IOError):
            pass
        finally:
            file_obj.close()
        print "saved"