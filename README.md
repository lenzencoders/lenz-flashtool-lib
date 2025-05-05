[![PyPI Version](https://img.shields.io/pypi/v/lenz-flashtool)](https://pypi.org/project/lenz-flashtool/)

# lenz-flashtool

FlashTool library for BiSS C Firmware Update and Calibration by LENZ Encoders.

This is the source repository for the `lenz-flashtool` Python package, designed to interface with LENZ BiSS C encoders for firmware updates, calibration, and data reading. It provides a `FlashTool` class and utility functions for working with encoder hardware, including hex file manipulation and color formatting utilities.

## Features

- Control LENZ BiSS C encoders via serial communication.
- Upload firmware and calibration data.
- Read encoder status, serial numbers, and error flags.
- Utilities for CRC calculation, hex data generation, and colored logging output.

## Installation

### From local folder
```bash
pip install .
```

### From PyPI
```bash
pip install lenz-flashtool
```

### From GitHub
```bash
pip install git+https://github.com/lenzencoders/lenz-flashtool-lib.git
```

## Requirements

- Python 3.8 or higher
- `pyserial>=3.5` (for serial communication)
- `numpy>=1.21.0` (for data handling)

## Usage

### Basic Example
```python
from lenz_flashtool import FlashTool, init_logging

# Set up logging
#
# Level	            Integer Value
# logging.CRITICAL	50
# logging.ERROR	    40
# logging.WARNING	  30
# logging.INFO	    20
# logging.DEBUG	    10
# logging.NOTSET	  0
init_logging(logfilename="flashtool.log", stdout_level=20, file_level=10)

# Initialize FlashTool
with FlashTool(port_description_prefixes=('XR21V')) as lenz:
    # Power cycle the encoder
    lenz.encoder_power_cycle()

    # Read serial number
    bootloader_ver, serial_num, mfg_date, program_ver = lenz.biss_read_snum()
    print(f"Encoder Serial Number: {serial_num}")
# The connection is automatically closed when exiting the 'with' block
```
### Note on Naming
The package is installed as `lenz-flashtool` (with a hyphen), but imported in Python as `lenz_flashtool` (with an underscore) due to Python’s naming conventions.

## Documentation

For detailed API documentation, examples, and usage instructions, visit the [LENZ FlashTool Documentation](https://flashtool.lenzencoders.com).

## Development

### Install Locally
```bash
git clone https://github.com/lenzencoders/lenz-flashtool-lib.git
cd lenz-flashtool-lib
pip install .
```

### Run Tests
```bash
pip install pytest
pytest tests/
```

## Contributing

Contributions are welcome! Please:
1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/my-feature`).
3. Commit your changes (`git commit -m "Add my feature"`).
4. Push to the branch (`git push origin feature/my-feature`).
5. Open a pull request.

Report issues at [github.com/lenzencoders/lenz-flashtool-lib/issues](https://github.com/lenzencoders/lenz-flashtool-lib/issues).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

For support or inquiries, contact LENZ ENCODERS at [info@lenzencoders.com](mailto:devs@lenzencoders.com).
```



