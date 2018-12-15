#! /usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
# coding: utf-8 

import os
import subprocess
import sys
import hypermatter
from pathlib import Path
from PyQt5 import QtGui, QtCore, QtWidgets

os.environ['TF_CPP_MIN_LOG_LEVEL'] = "3"


# from collections import defaultdict
class HorzTabBarWidget(QtWidgets.QTabBar):
    def __init__(self, parent=None, *args, **kwargs):
        self.tabSize = QtCore.QSize(kwargs.pop('width', 100), kwargs.pop('height', 25))
        QtWidgets.QTabBar.__init__(self, parent, *args, **kwargs)

    def paintEvent(self, event):
        painter = QtWidgets.QStylePainter(self)
        option = QtWidgets.QStyleOptionTab()

        for index in range(self.count()):
            self.initStyleOption(option, index)
            tabRect = self.tabRect(index)
            tabRect.moveLeft(10)
            painter.drawControl(QtWidgets.QStyle.CE_TabBarTabShape, option)
            painter.drawText(tabRect, QtCore.Qt.AlignVCenter |
                             QtCore.Qt.TextDontClip,
                             self.tabText(index))
        painter.end()

    def tabSizeHint(self, index):
        return self.tabSize


class HorzTabWidget(QtWidgets.QTabWidget):
    def __init__(self, parent, *args):
        QtGui.QTabWidget.__init__(self, parent, *args)
        self.setTabBar(HorzTabBarWidget(self))


def capture_help_fn(fn_name):
    proc = subprocess.Popen("hypermatter %s -h" % fn_name, shell=True, stdout=subprocess.PIPE)
    out = proc.communicate()[0]
    out_str = out.decode("utf-8")
    return out_str


modules = ['Conversion', 'Registration', 'Segmentation', 'Pre-Process', 'QC', 'Statistics', 'Workflows']

nested_dict = {

    'Conversion': {
        'functions': {
            0: {
                'name': 'File Type',
                'script': 'filetype',
                'opts': '-t filetype -v img -f out',
                'helpmsg': ''
            },
            1: {
                'name': 'To Standard',
                'opts': 'segment_hfb',
                'helpmsg': ''
            },
        }
    },

    'Registration': {
        'functions': {
            0: {
                'name': 'Affine',
                'script': 'reg_aladin',
                'opts': '-t register_aladin -v ref flo -f out',
                'helpmsg': 'Registers two images with an affine or rigid transform'
            },
        }
    },

    'Segmentation': {
        'functions': {
            0: {
                'name': 'Head from Brain',
                'script': 'seg_hfb',
                'opts': '-t seg_hfb -d subj -v t1w t2w flair -f rmcereb out',
                'helpmsg': 'Brain extraction (skull-striping) using a trained CNN'
            },
            1: {
                'name': 'Hippocampus',
                'script': 'seg_hipp',
                'opts': '-t seg_hipp -v t1w -f out',
                'helpmsg': 'Segments hippocampus using a trained CNN'
            },
            2: {
                'name': 'Stroke',
                'script': 'seg_stroke',
                'opts': '-t seg_stroke -d subj -v t1w t2w flair -f out',
                'helpmsg': 'Segments stroke using a trained CNN'
            },
            3: {
                'name': 'Ventricles',
                'script': 'seg_vent',
                'opts': '-t seg_vent -d subj -v t1w t2w flair -f out',
                'helpmsg': 'Segments ventricles using a trained CNN'
            },
            4: {
                'name': '3-Tissue',
                'script': 'seg_tissue',
                'opts': '-t seg_tissue -v img -f out',
                'helpmsg': 'Segments tissue classes (GM, WM, CSF) using FSL FAST'
            },
        }
    },

    'Pre-Process': {
        'functions': {
            0: {
                'name': 'Bias Correct',
                'script': 'bias_corr',
                'opts': '-t bias_corr -v img -f out',
                'helpmsg': 'Bias correct using N4'
            },
        }
    },

    'QC': {
        'functions': {
            0: {
                'name': 'Registration QC',
                'script': 'reg_qc',
                'opts': '-t reg_qc -v img ref -f out',
                'helpmsg': 'Creates tiled mosaic of moving image from registration overlaid on reference image'
            },
            1: {
                'name': 'Segmentation QC',
                'script': 'seg_qc',
                'opts': '-t seg_qc -v img seg -f out',
                'helpmsg': 'Creates tiled mosaic of segmentation overlaid on structural image'
            }
        }
    },

    'Statistics': {
        'functions': {
            0: {
                'name': 'Model Performance',
                'opts': '',
                'helpmsg': 'Bias field correct, and register multi-contrasts to T1'
            },
            1: {
                'name': 'Subject Deviation',
                'opts': '',
                'helpmsg': 'Bias field correct, register to T1 brain extract and remove cerebellum'
            },
        }
    },

    'Workflows': {
        'functions': {
            0: {
                'name': 'N4 and register to T1',
                'script': 'flow_n4reg',
                'opts': '-t flow_n4reg -d subj',
                'helpmsg': 'Bias field correct, and register multi-contrasts to T1'
            },
            1: {
                'name': 'BrainLab Stage 1',
                'script': 'flow_stg1',
                'opts': '-t flow_stg1 -d subj',
                'helpmsg': 'Bias field correct, register sequences to T1, brain extract and remove cerebellum'
            },
            2: {
                'name': 'BrainLab Stage 2',
                'script': 'flow_stg2',
                'opts': '-t flow_stg2 -d subj',
                'helpmsg': 'Segment tissue classes (GM, WM, CSF), ventricles and hippocampus'
            },
            3: {
                'name': 'Run group',
                'script': 'run_group',
                'opts': '-t run_group -d group -v test',
                # 'opts': '-t run_group -d group -f run_fn fn_opts',
                'helpmsg': 'Runs a specific hypermatter function over a group of subjects'
            },
        }
    },

}


def fun_button(nested_dictionary, module, btn_num, hyper_home):
    fun_name = nested_dictionary[module]['functions'][btn_num]['name']
    btn = QtWidgets.QPushButton(fun_name)
    btn.clicked.connect(lambda: run_func(nested_dictionary, module, btn_num, hyper_home))
    btn.setToolTip(nested_dict[module]['functions'][btn_num]['helpmsg'])

    return btn


def run_func(nested_dictionary, module, btnnum, hyper_home):
    opts = nested_dictionary[module]['functions'][btnnum]['opts']
    script_name = nested_dictionary[module]['functions'][btnnum]['script']
    help_str = capture_help_fn(fn_name=script_name)

    subprocess.Popen('%s/utils/gui_options.py %s -hf "%s"' % (hyper_home, opts, help_str), shell=True,
                     stdin=None, stdout=None, stderr=None, close_fds=True)


def main():
    app = QtWidgets.QApplication(sys.argv)

    mainwidget = QtWidgets.QWidget()
    mainwidget.resize(150, 550)

    font = QtGui.QFont('Mono', 10, QtGui.QFont.Light)
    mainwidget.setFont(font)
    mainwidget.move(QtWidgets.QApplication.desktop().screen().rect().center() - mainwidget.rect().center())

    ver = hypermatter.__version__
    mainwidget.setWindowTitle("HyperMatter %s" % ver)

    p = mainwidget.palette()
    # p.setColor(mainwidget.backgroundRole(), QtCore.Qt.black)
    mainwidget.setPalette(p)

    vbox = QtWidgets.QVBoxLayout(mainwidget)

    gui_file = os.path.realpath(__file__)
    hyper_home = Path(gui_file).parents[0]
    hyper_mother = Path(gui_file).parents[1]

    pic = QtWidgets.QLabel()
    pixmap = QtGui.QPixmap("%s/docs/hypericon.png" % hyper_mother)

    pixmaps = pixmap.scaled(270, 150)  # QtCore.Qt.KeepAspectRatio
    pic.setPixmap(pixmaps)
    pic.setAlignment(QtCore.Qt.AlignCenter)

    vbox.addWidget(pic)

    tabs = QtWidgets.QTabWidget()
    tabs.setTabBar(HorzTabBarWidget(width=150, height=50))

    for m, mod in enumerate(modules):

        widget = QtWidgets.QWidget()
        widget.layout = QtWidgets.QVBoxLayout()

        for b in range(len(nested_dict[mod]['functions'])):
            btn = fun_button(nested_dict, mod, b, hyper_home)
            widget.layout.addWidget(btn)

        widget.setLayout(widget.layout)
        tabs.addTab(widget, mod)

    tabs.setTabPosition(QtWidgets.QTabWidget.West)

    vbox.addWidget(tabs)

    mainwidget.setLayout(vbox)
    mainwidget.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
