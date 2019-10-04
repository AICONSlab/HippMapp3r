#! /usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
# coding: utf-8 

import os
import argparse
import sys
import re
import subprocess
from PyQt5 import QtGui, QtCore, QtWidgets

os.environ['TF_CPP_MIN_LOG_LEVEL'] = "3"


def helpmsg():
    return '''gui_options.py -t title -f [ fields separated by space] -v [volumes to open] -d [dirs to open]
    -hf helpfun

Takes list of strings as options for entries for a gui options, and a gui title

example: gui_options.py -t "Reg options" -v clar labels -f orient label resolution

Input options will be printed as output

'''


def parseargs():
    parser = argparse.ArgumentParser(description='Sample argparse py', usage=helpmsg())
    parser.add_argument('-t', '--title', type=str, help="gui title", required=True)
    parser.add_argument('-f', '--fields', type=str, nargs='+', help="fields for options")
    parser.add_argument('-v', '--vols', type=str, nargs='+', help="volumes for reading")
    parser.add_argument('-d', '--dirs', type=str, nargs='+', help="directories for reading")
    parser.add_argument('-hf', '--helpfun', type=str, help="help fun")

    args = parser.parse_args()

    title = args.title
    fields = args.fields
    vols = args.vols
    dirs = args.dirs
    helpfun = args.helpfun

    return title, vols, dirs, fields, helpfun


def OptsMenu(title, vols=None, dirs=None, fields=None, helpfun=None):
    # create GUI
    main = QtWidgets.QMainWindow()

    widget = QtWidgets.QWidget()
    widget.setWindowTitle('%s' % title)

    widget.move(QtWidgets.QApplication.desktop().screen().rect().center() - widget.rect().center())

    layout = QtWidgets.QFormLayout()

    layout.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)

    linedits = {}
    buttons = {}
    labels = {}

    if dirs:

        for d, indir in enumerate(dirs):
            # Create buttons for vols
            labels["%s" % indir] = QtWidgets.QLabel('No Dir selected')
            buttons["%s" % indir] = QtWidgets.QPushButton('Select %s' % indir)

            # Layout for widgets
            layout.addRow(labels["%s" % indir], buttons["%s" % indir])

            buttons["%s" % indir].clicked.connect(lambda ignore, xd=indir: get_dname(main, labels, xd))

    if vols:

        for v, vol in enumerate(vols):
            # Create buttons for vols
            labels["%s" % vol] = QtWidgets.QLabel('No file selected')
            buttons["%s" % vol] = QtWidgets.QPushButton('Select %s' % vol)

            # Layout for widgets
            layout.addRow(labels["%s" % vol], buttons["%s" % vol])

            buttons["%s" % vol].clicked.connect(lambda ignore, xv=vol: get_fname(main, labels, xv))

    if fields:

        for f, field in enumerate(fields):
            # Create inputs (line edts)
            linedits["%s" % field] = QtWidgets.QLineEdit()
            linedits["%s" % field].setAlignment(QtCore.Qt.AlignRight)

            # Layout for widgets        
            layout.addRow("%s" % field, linedits["%s" % field])

    # Create push button
    helpbutton = QtWidgets.QPushButton('Help')
    submit = QtWidgets.QPushButton('Run')

    layout.addRow(helpbutton, submit)

    widget.setLayout(layout)

    helpbutton.clicked.connect(lambda: print_help(main, helpfun))

    fn_name = title.replace(' ', '_').lower()
    submit.clicked.connect(lambda: parse_inputs(fn_name, labels, linedits, vols, dirs, fields))

    return widget, linedits, labels


def get_fname(main, labels, volume):
    vfile = QtWidgets.QFileDialog.getOpenFileName(main, 'Select %s' % volume)
    if vfile:
        vfilestr = "%s : %s" % (volume, str(vfile[0]).lstrip())
        labels["%s" % volume].setText(vfilestr)
        print('%s path: %s' % (volume, vfile[0]))
    else:
        labels["%s" % volume].setText('No file selected')

    return vfile[0]


def get_dname(main, labels, indir):
    dfile = QtWidgets.QFileDialog.getExistingDirectory(main, "Select %s" % indir, ".")
    if dfile:
        dfilestr = "%s : %s" % (indir, str(dfile).lstrip())
        labels["%s" % indir].setText(dfilestr)
        print('%s path: %s' % (indir, dfile))
    else:
        labels["%s" % indir].setText('No Dir selected')

    return dfile


def parse_inputs(fn_name, labels, linedits, vols, dirs, fields):
    cmd = "hippmapper %s" % fn_name

    if vols:
        for v, vol in enumerate(vols):
            try:
                in_vol = str(labels["%s" % vol].text()).split(":")[1].lstrip()
                vols_cmd = " --%s %s" % (vol, in_vol)
                cmd = cmd + "%s" % vols_cmd
            except IndexError:
                continue
    if dirs:
        for d, indir in enumerate(dirs):
            try:
                dfile = str(labels["%s" % indir].text()).split(":")[1].lstrip()
                dirs_cmd = " --%s %s" % (indir, dfile)
                cmd = cmd + "%s" % dirs_cmd
            except IndexError:
                continue
    if fields:
        for f, field in enumerate(fields):
            in_field = str(linedits["%s" % field].text()).lstrip()
            if in_field != "":
                fields_cmd = " --%s %s" % (field, in_field)
                cmd = cmd + "%s" % fields_cmd

    print("\n running HippMapp3r with the following command: \n\n %s \n" % cmd)

    subprocess.Popen("%s" % cmd, shell=True,
                     stdin=None, stdout=None, stderr=None, close_fds=True)

    # QtCore.QCoreApplication.instance().quit
    sys.exit()


def print_help(main, helpfun):
    main.setWindowTitle('Help function')
    scrollarea = QtWidgets.QScrollArea()

    helplbl = QtWidgets.QLabel()
    helplbl.setText(helpfun)
    font = QtGui.QFont('Mono', 9, QtGui.QFont.Light)
    helplbl.setFont(font)
    helplbl.setWordWrap(True)

    scrollarea.setWidget(helplbl)
    #scrollarea.setWidgetResizable(False)
    scrollarea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
    scrollarea.setAttribute(QtCore.Qt.WA_DeleteOnClose)
    main.setCentralWidget(scrollarea)

    main.move(QtWidgets.QApplication.desktop().screen().rect().center() - main.rect().center())
    main.show()

    QtWidgets.QApplication.processEvents()


def main():
    [title, vols, dirs, fields, helpfun] = parseargs()
    helpfunhtml = helpfun.replace('\n','<br>')

    # Create an PyQT5 application object.
    app = QtWidgets.QApplication(sys.argv)
    gui_name = title.replace('_', ' ').upper()
    menu, linedits, labels = OptsMenu(title=gui_name, vols=vols, dirs=dirs, fields=fields, helpfun=helpfunhtml)
    menu.show()
    app.exec_()
    app.processEvents()


if __name__ == "__main__":
    sys.exit(main())
