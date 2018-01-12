#!/usr/bin/python

import sys

from PyQt4 import QtGui, QtCore
from GUI import Main


if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)

    main = Main()

    sys.exit(app.exec_())

