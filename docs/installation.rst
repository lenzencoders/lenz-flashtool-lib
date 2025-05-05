Installation
============

This guide explains how to install the **lenz-flashtool** library and its dependencies.

Prerequisites
-------------

- Python 3.8 or higher
- pip (Python package manager)
- XR21V1410 system driver for Windows (not required for Linux)
- LENZ FlashTool device
- A BiSS C compatible encoder device (e.g., LENZ Encoders)

Installation Steps
------------------

1. **Install lenz-flashtool**:

   It is strongly recommended to use a virtual environment when installing Python libraries 
   to avoid conflicts with other packages. The installation will remain isolated within the virtual environment.

   .. tab-set::

      .. tab-item:: Windows

         .. code-block:: bash

            # Create a virtual environment
            python -m venv myenv

            # Activate it (Windows)
            myenv\Scripts\activate

            # Install library
            pip install lenz-flashtool

      .. tab-item:: Linux

         .. code-block:: bash

            # Create a virtual environment
            python -m venv myenv

            # Activate it (Linux/Mac)
            source myenv/bin/activate

            # Install library
            pip install lenz-flashtool



   To deactivate the virtual environment when done:
   
   .. code-block:: bash
      
      deactivate

   .. note::
      The package is installed as `lenz-flashtool` (with a hyphen), but imported in Python as `lenz_flashtool` (with an underscore) due to Python’s naming conventions.


2. **Install XR21V1410 USB-UART driver for Windows**:

   Linux users can skip this step.

   Download and install the driver from: https://www.maxlinear.com/product/interface/uarts/usb-uarts/xr21v1410

3. **Verify the library installation**:

   Check that the library is installed:

   .. code-block:: python

      import lenz_flashtool
      print(lenz_flashtool.__version__)

   This should display the version (e.g., ``0.1.0``).

3. **Try CLI (Optional)**:

   A command-line interface is included with the library. You can test it:

   .. code-block:: bash

      python -m lenz_flashtool.biss.cli registers

   If installed using ``pip``, you can also run:

   .. code-block:: bash

      lenz-flashtool-cli readserial

Troubleshooting
---------------

- **ModuleNotFoundError**: Ensure pip installs to the correct Python environment. Use ``pip --version`` to check.
- **FlashToolError: LENZ FlashTool not found!**: Ensure your FlashTool device is connected and the driver is installed (on Windows).

See :doc:`getting_started` for an introduction or :doc:`usage` for usage examples.