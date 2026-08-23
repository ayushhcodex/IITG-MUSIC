import os
import sys

# Add the plugin directory to the path so modules can be imported
plugin_dir = os.path.dirname(__file__)
if plugin_dir not in sys.path:
    sys.path.append(plugin_dir)

def __init_plugin__(app=None):
    """
    PyMOL plugin entry point.
    """
    from pymol.plugins import addmenuitemqt
    
    # Add a menu item to the PyMOL Plugins menu
    addmenuitemqt('MrFold Music Studio', run_plugin)

def run_plugin():
    from gui import show_gui
    show_gui()
