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

Zeroing
-----------

The following example performs zeroing on a LENZ encoder. Resets position counter to zero at current mechanical position.

.. code-block:: python

   import logging
   import time
   import lenz_flashtool as lenz

   lenz.init_logging('flashtool.log', logging.INFO, logging.DEBUG)
   with lenz.FlashTool(port_description_prefixes=('XR21V')) as ft:
      ft.encoder_power_cycle()
      ft.biss_write_command('unlocksetup')
      ft.biss_write_command('unlockflash')
      ft.biss_write_command('zeroing')
      ft.biss_write_command('saveflash')
      time.sleep(0.2)
      ft.encoder_power_cycle()

Change the encoder direction sensing
------------------------------------

The following example configure encoder direction sensing for clockwise or counterclockwise rotation.

.. code-block:: python

   import logging
   import time
   import lenz_flashtool as lenz

   lenz.init_logging('flashtool.log', logging.INFO, logging.DEBUG)
   with lenz.FlashTool(port_description_prefixes=('XR21V')) as ft:
      ft.encoder_power_cycle()
      ft.biss_write_command('unlocksetup')
      ft.biss_write_command('unlockflash')
      ft.biss_write_command('set_dir_cw')  
      # ft.biss_write_command('set_dir_ccw')
      ft.biss_write_command('saveflash')
      time.sleep(0.2)
      ft.encoder_power_cycle()

Set the encoder resolution to 24 bits
------------------------------------

The following example configure encoder resolution to 24 bits.

.. code-block:: python

   import logging
   import time
   import lenz_flashtool as lenz

   lenz.init_logging('flashtool.log', logging.INFO, logging.DEBUG)
   with lenz.FlashTool(port_description_prefixes=('XR21V')) as ft:
      ft.encoder_power_cycle()
      ft.biss_write_command('unlocksetup')
      ft.biss_write_command('unlockflash')
      ft.biss_write_word(lenz.BiSSBank.REV_RES_REG_INDEX, 0xE)  # Set resolution to 24 bits
      ft.biss_write_command('saveflash')
      time.sleep(0.2)
      ft.encoder_power_cycle()

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