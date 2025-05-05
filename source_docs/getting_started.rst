Getting Started
===============

The LENZ FlashTool library provides a Python interface for interacting with LENZ BiSS encoders via a serial port FlashTool device. 
It supports operations such as reading encoder data, sending commands, managing device registers, and performing advanced 
signal processing for high-precision encoder systems. 
This documentation covers the installation, basic usage, and core functionality of the library.

What is lenz-flashtool?
-----------------------

The library is designed for developers and engineers working with LENZ BiSS encoders, offering both a programmatic API 
and a command-line interface (CLI) for direct device interaction. 
Key features include:

- Serial communication with LENZ BiSS encoders :mod:`lenz_flashtool.flashtool`
- Support for reading and writing BiSS registers :mod:`lenz_flashtool.biss`
- Predefined BiSS commands for common operations (e.g., reboot, calibration)
- Advanced signal processing for encoder data calibration and harmonic analysis :mod:`lenz_flashtool.encproc`
- CLI for quick device interaction and diagnostics :mod:`lenz_flashtool.biss.cli`
- Utilities for encoder processing and testing

About LENZ Encoders
-------------------

**LENZ Encoders** are non-contact, bearingless absolute angle encoders based on inductive 
position sensing through electromagnetic induction. They are designed for high-precision, 
robust applications, offering resolutions up to 22 bits and operating speeds 
up to 38,000 RPM (e.g., IRS-I34 model). Key characteristics include:

- **Ultra-lightweight and modular design**: Available in sizes from 34 mm to 150 mm (e.g., IRS-I34, IRS-I50, IRS-I150), consisting of two printed circuit boards for easy integration in space-constrained applications.
- **High accuracy and stability**: Provides precise position data with resolutions ranging from 15 to 19 bits, insensitive to electromagnetic fields, permanent magnets, and electrical noise.
- **Simple installation**: Bearingless and non-contact, making them ideal for harsh environments and high-speed operations.
- **BiSS® C interface**: Supports synchronous, bidirectional data transmission for reliable communication.
- **Cost-effective**: Modular solutions start at reasonable price for single units, with discounts for bulk orders.

These encoders are suitable for industrial automation, motion control, and OEM applications. 
For detailed specifications, datasheets, and sample code, visit the LENZ GitHub repository 
(https://github.com/lenzencoders/) or contact info@lenzencoders.com.

Quick Start
-----------

To get started, 

- connect LENZ FlashTool device and an encoder, 
- install XR21V1410 USB-UART driver, 
- install the library 
- and try a simple reading command:

.. code-block:: python

   import logging
   import lenz_flashtool as lenz

   lenz.init_logging('flashtool.log', logging.INFO, logging.DEBUG)
   with lenz.FlashTool(port_description_prefixes=('XR21V')) as ft:
       ft.biss_read_snum()

**Output**:

::

   BiSS received data:
   [  3   3  98  26  84  67  96  72   0   0   0   0  94   0  19  31   0   0
      0   0  14   0   0   0  12  37   6  26   0   0   0   0   0   0   0   0
      0   0   0   0  25   0   0   0   0   1   0   1   0   4   1   1 103 185
    165 192  83  73  66  48  56  48  75  66]
   ======= ENCODER DATA ========
   Bootloader:      00010001
   Serial No :      54436048
   Mfg. Date :      67B9A5C0
   Program   :      00040101
   Dev ID_H  :      53494230
   Dev ID_L  :      3830
   =============================
   DEVID: SIB080, Serial No: TC6048, Mfg date: 2025-02-22 10:24:00 (UTC)
   FlashTool: COM15 closed.

For CLI usage:

.. code-block:: bash

   python -m lenz_flashtool.biss.cli readserial

See :doc:`installation` for setup instructions and :doc:`usage` for more examples.

Next Steps
----------

- Follow the :doc:`installation` guide to set up the library.
- Explore the :doc:`usage` section for detailed examples.
- Refer to the :doc:`api` for complete API documentation.

Contributing
------------

Contributions are welcome! Please:

.. role:: bash(code)
   :language: bash

1. Fork the repository.
2. Create a feature branch :bash:`git checkout -b feature/my-feature`.
3. Commit your changes :bash:`git commit -m "Feature comment"`.
4. Push to the branch :bash:`git push origin feature/my-feature`.
5. Open a pull request.

Report issues at https://github.com/lenzencoders/lenz-flashtool-lib/issues.

License
-------

This project is licensed under the MIT License.

Contact
-------

For support or inquiries, contact LENZ ENCODERS at info@lenzencoders.com or shop@lenzencoders.com. 
For direct assistance, reach out at +7-921-424-9600 (Monday–Friday: 8am–7pm; Weekends: 11am–7pm, UTC+3 time).
