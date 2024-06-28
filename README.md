xmstool_runner
===========

This Python package contains a GUI interface to the tools available in SMS.
It also includes the following example tools:

- UGrid from "fort.14" File: Reads an ADCIRC "fort.14" file and creates a UGrid. A description of how this tool was created is found [here](examples/building_a_tool.md).
- Datasets from "fort.13" File: Reads the datasets contained in an ADCIRC "fort.13" file and adds them to a UGrid.
- Dataset from "fort.63.nc" File: Reads a solution dataset from a "fort.63.nc" file and adds it to a UGrid.
- Transform UGrid points: Transforms the points in a UGrid from one projection to another using the GDAL `gdaltransform` and `gdalsrsinfo` command line utilities. This tool requires a working installation of GDAL. A description of how this tool was created is found [here](examples/building_command_line_tool.md).

# Installation

This Python package requires Python 3.10. You may wish to use a virtual environment when installing this package as described [here](https://docs.python.org/3.10/library/venv.html). Once the virtual environment is activated, and you've changed your current directory to this main folder of this repository, you can install this package as follows:

```pip install . -i https://public.aquapi.aquaveo.com/aquaveo/stable/+simple/```

The `tool_runner` script will be installed to the virtual environment's `Scripts` folder. It can be called with something similar to the following:

```/path/to/venv/Scripts/tool_runner```

You may also wish to install the tools available to SMS by running the following command:

```pip install xmstool -i https://public.aquapi.aquaveo.com/aquaveo/stable/+simple/```

# Running

To run the xmstool_runner from source code, you can use the following command:

```python xms/tool_runner/toolbox_dialog.py```

A web interface to a VNC server in the cloud can be started from macOS or Linux using [noVNC](https://github.com/novnc/noVNC)
by running the following command:

```./utils/novnc_proxy --vnc cloud-ip:cloud-vnc-port```

Where "cloud-ip" is replaced by the IP of the cloud computer and "cloud-vnc-port"
is replaced by the port of the VNC server.


A connection from a web browser can be made using http://noVNC-IP:6080/vnc.html?host=noVNC-IP&port=6080,
where "noVNC-IP" is the IP address of the macOS or Linux computer running noVNC.
