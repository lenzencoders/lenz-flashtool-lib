Usage
=====

This section provides examples of using **lenz-flashtool** for firmware updates, calibration, and CLI operations.

Firmware Update
---------------

Update firmware on a BiSS C encoder device:

.. code-block:: python

   import logging
   import lenz_flashtool as lenz

   lenz.init_logging('flashtool.log', logging.INFO, logging.DEBUG)
   with lenz.FlashTool(port_description_prefixes=('XR21V')) as ft:
      lenz.biss_send_hex("SAB039_1_1_4.hex", pbar=True)


.. note::
      The function `lenz.biss_send_hex()` from the `lenz_flashtool.operations` module is used here, not the `FlashTool()` class method.


Using the CLI:

.. code-block:: bash

   python -m lenz_flashtool.biss.cli sendhexfile .\SAB039_1_1_4.hex y

Calibration
-----------

The following example performs amplitude calibration on a LENZ encoder. The encoder's rotor must complete one full turn during the process.

.. code-block:: python

   import logging
   import time
   import lenz_flashtool as lenz

   lenz.init_logging('flashtool.log', logging.INFO, logging.DEBUG)
   with lenz.FlashTool(port_description_prefixes=('XR21V')) as ft:
      ft.encoder_power_cycle()
      ft.biss_write_command('unlocksetup')
      ft.biss_write_command('cleardiflut')
      ft.biss_write_command('unlockflash')
      ft.biss_write_command('ampcalibrate')
      logging.info("Waiting Signal Amplitude Calibration...")
      while ((ft.biss_addr_read(0x4A, 2).view('uint16') & 0xC0) != 128):
         time.sleep(0.2)
      logging.info("Signal Amplitude Calibration Finished")


.. Calibrate an encoder using :mod:`lenz_flashtool.encproc`:

.. .. code-block:: python

..    from lenz_flashtool.encproc import EncoderProcessor

..    # Initialize processor
..    processor = EncoderProcessor(device_id="ENC123")

..    # Perform calibration
..    processor.calibrate()

.. See :mod:`lenz_flashtool.encproc` for more details.

.. Testing
.. -------

.. Run tests with :mod:`lenz_flashtool.testing`:

.. .. code-block:: python

..    from lenz_flashtool.testing import run_tests

..    run_tests(device_id="ENC123")

For more examples, explore the :doc:`api` or refer to :doc:`getting_started`.