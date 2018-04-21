import sys
from PyQt4.QtGui import QApplication
# import MainWindow
import arduinoS4v3_1

def main():
    app = QApplication(['Arduino S'])
    app.setOrganizationName("Gatituz PK")
    app.setOrganizationDomain("http://gatituzmes-server.duckdns.org/")
    window = arduinoS4v3_1.Window()
    window.show()
    app.exec_()

if __name__ == "__main__":
    main()