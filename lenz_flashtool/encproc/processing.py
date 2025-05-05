r'''
 _     _____ _   _ _____   _____ _   _  ____ ___  ____  _____ ____  ____
| |   | ____| \ | |__  /  | ____| \ | |/ ___/ _ \|  _ \| ____|  _ \/ ___|
| |   |  _| |  \| | / /   |  _| |  \| | |  | | | | | | |  _| | |_) \___ \
| |___| |___| |\  |/ /_   | |___| |\  | |__| |_| | |_| | |___|  _ < ___) |
|_____|_____|_| \_/____|  |_____|_| \_|\____\___/|____/|_____|_| \_|____/


LENZ Encoder Signal Processing Library

This library provides a comprehensive suite of signal processing functions for high-precision
LENZ encoder systems, designed to enhance the accuracy of position measurements in applications
such as motor control, robotics, and industrial automation. It includes advanced algorithms for
differential signal computation, harmonic analysis, noise filtering, and calibration table
generation, with specialized support for motor-driven systems to suppress harmonic errors.

Key Features:
- Differential signal computation between paired encoder signals for error analysis.
- Advanced filtering techniques, including bidirectional moving average and custom smoothing filters.
- Harmonic analysis using Fast Fourier Transform (FFT) to identify and quantify periodic errors.
- Generation of difference compensation tables for systematic error correction.
- Motor harmonic suppression for enhanced accuracy in motor-driven encoder systems.
- Support for 24-bit encoder data with proper handling of wrap-around effects.

Example Usage:
    ```python
    import numpy as np
    from lenz_encoder_processor import LenzEncoderProcessor

    # Example: Calibrate encoder data with motor harmonic suppression
    encoder_data = np.array([1000, 1010, 1005, 1020, 1015], dtype=np.int32)
    coarse_red = 2048
    motor_harm = 2
    comp_table = LenzEncoderProcessor.lenz_cal_motor_harm(encoder_data, coarse_red, motor_harm)
    print(comp_table)  # Compensation table for error correction
    ```

Notes:
- The library assumes 24-bit encoder data (0 to 2^24 - 1) but can be adapted for other resolutions.
- Functions are designed for static use, requiring no instantiation of `LenzEncoderProcessor`.
- Calibration routines (`lenz_cal`, `lenz_cal_motor_harm`) are optimized for high-precision
  applications but may require tuning of parameters like `coarse_red` and `motor_harm` for
  specific use cases.
- The `diff_table_gen_motor_harm` function includes motor harmonic suppression, which is critical
  for motor-driven systems but requires a valid `motor_harm` value.

Author:
    LENZ ENCODERS, 2020-2025
'''

from typing import Tuple
import numpy as np


class LenzEncoderProcessor:
    """
    Main class for LENZ encoder signal processing operations.

    Provides static methods for differential signal calculation, compensation table generation,
    harmonic analysis, and calibration routines for LENZ encoders.
    """

    @staticmethod
    def calc_diff(encoder_1: np.int32, encoder_2: np.int32, coarse_red: int) -> np.ndarray:
        """
        Computes the differential signal between two encoder readings with scaling.

        This function calculates the difference between two encoder signals, applies mean centering,
        and scales the result according to the coarse reduction factor. The output represents
        the relative error between the two encoders, normalized.

        Args:
            encoder_1: First encoder readings array (24-bit values)
            encoder_2: Second encoder readings array (24-bit values)
            coarse_red: Scaling factor for coarse reduction (typically 2^11 for 24-bit encoders)

        Returns:
            Differential signal array with mean removed and scaled by coarse_red/2048
        """

        diff = np.double(((encoder_1 << 8) - (encoder_2 << 8)) >> 8)
        diff = diff - np.mean(diff)
        return diff * coarse_red / 2**11

    @staticmethod
    def compute_difftable(
        diff: np.ndarray,
        lenz_fix: np.ndarray,
        coarse_red: int
    ) -> np.ndarray:
        """
        Computes a difference compensation table by averaging error values at each encoder position.

        Args:
            diff: Array of measured error values (difference between reference and raw encoder values)
            lenz_fix: Array of fixed LENZ encoder positions corresponding to the error measurements.
            coarse_red: Coarse reduction factor.

        Returns:
            np.ndarray: Difference compensation table where each index corresponds to an encoder
                    position and contains the average error at that position.
        """
        diff_table = np.zeros(coarse_red * 256, 'double')
        for i in range(len(diff_table)):
            find_diff = np.double(diff[lenz_fix == i])
            if np.size(find_diff) == 0:
                diff_table[i] = diff_table[i - 1]
            else:
                diff_table[i] = np.mean(find_diff)
        return diff_table

    @staticmethod
    def analyze_harmonics(diff_table: np.ndarray) -> Tuple[int, int, np.ndarray]:
        """
        Analyzes frequency components of the difference table using FFT.

        Args:
            diff_table (np.array): Difference table array.

        Returns:
            Tuple containing:
                - Amplitude of first harmonic
                - Angle of first harmonic
                - Full FFT result
        """
        fft_diff = np.fft.fft(diff_table)
        first_harm = fft_diff[1]

        fft_diff[np.abs(fft_diff) < 300] = 0
        fft_diff[0] = 0
        fft_diff[[1, -1]] = 0

        first_harm_amp = np.int32(np.round(np.abs(first_harm/len(fft_diff)) * 16 * 2))
        first_harm_angle = np.int32((np.angle(first_harm) + np.pi / 2)/2/np.pi*2**16) & 0xFFFF

        return first_harm_amp, first_harm_angle, fft_diff

    @staticmethod
    def extrapolate(data: np.ndarray, res: int) -> np.ndarray:
        """
        Extrapolates data to handle discontinuities or wrap-around effects.

        Args:
            data (np.array): Input data to extrapolate.
            res (int): Bit resolution for extrapolation.

        Returns:
            np.array: Extrapolated data.
        """
        max_data = np.int32(2**res)
        low_data = np.int32(max_data/4)
        high_data = np.int32(low_data*3)
        steps = np.zeros(len(data), 'int32')
        steps_ar = np.arange(1, len(data))
        steps_up = steps_ar[(data[:-1] - data[1:]) > high_data]
        steps_down = steps_ar[(data[1:] - data[:-1]) > high_data]
        step = np.int32(0)
        for i in range(1, len(steps_up)):
            step = step+max_data
            steps[steps_up[i-1]:steps_up[i]] = step
        if len(steps_up):
            step = step + max_data
            steps[steps_up[-1]:] = step
        step = 0
        for i in range(1, len(steps_down)):
            step = step-max_data
            steps[steps_down[i-1]:steps_down[i]] = steps[steps_down[i-1]:steps_down[i]] + step
        if len(steps_down):
            step = step - max_data
            steps[steps_down[-1]:] = steps[steps_down[-1]:] + step
        ext_data = data + steps
        return ext_data

    @staticmethod
    def as_filt(data: np.ndarray, depth: int) -> np.ndarray:
        """
        Applies a custom filter to smooth the data.

        Args:
            data (np.array): Input data to filter.
            depth (int): Filter depth parameter

        Returns:
            np.array: Filtered data
        """
        data_filt = np.double(np.zeros(len(data)))
        data_filt[0] = data[0]
        k = np.double(1 / np.double(depth))

        data_der = (np.double(data[depth]) - data_filt[0]) * k

        for i in range(1, depth):
            data_filt[i] = data_filt[i - 1] + data_der
            data_filt[i] = (np.double(data[i]) - data_filt[i]) * k + data_filt[i]

        for i in range(depth, len(data)):
            data_der = (np.double(data[i] - data[i-depth]) * k - data_der) * k + data_der
            data_filt[i] = data_filt[i - 1] + data_der
            data_filt[i] = (np.double(data[i]) - data_filt[i]) * k + data_filt[i]

        return np.int32(data_filt)

    @staticmethod
    def clip_to_int8(data: np.ndarray) -> np.ndarray:
        """
        Clips and converts data to 8-bit integers.

        Args:
            data (np.array): Input data.

        Returns:
            np.array: Clipped and converted data.
        """
        data = np.int16(data)
        data[data > 127] = 127
        data[data < -128] = -128
        data = np.int8(data)
        return data

    @staticmethod
    def ext_gen(data_in: np.ndarray) -> np.ndarray:
        """
        Extends 24-bit encoder data to 32-bit by handling overflow correctly.

        This function processes raw 24-bit encoder data by maintaining proper sign extension
        when converting to 32-bit values, ensuring correct handling of overflow cases.

        Args:
            data_in: Input array of 24-bit encoder values (as int32)

        Returns:
            np.ndarray: Array of extended 32-bit encoder values with proper overflow handling
        """
        ext_out = np.int32(np.zeros(len(data_in)))
        ext_out[0] = data_in[0]
        for data_cou in range(1, len(data_in)):
            ext_out[data_cou] = ext_out[data_cou - 1] + ((np.int32(data_in[data_cou] - ext_out[data_cou - 1]) << 8) >> 8)

        return ext_out

    @staticmethod
    def comp_diff(encoder_in: np.ndarray, diff_table_in: np.ndarray, coarse_red: int) -> np.ndarray:
        """
        Compensates encoder data using a difference table for error correction.

        This function applies a compensation table to raw encoder data to correct
        systematic errors, using linear interpolation between table entries.

        Args:
            encoder_in: Raw encoder input data (24-bit values as int32)
            diff_table_in: Difference compensation table (int16 values)
            coarse_red: Coarse reduction factor (scaling parameter)

        Returns:
            np.ndarray: Compensated encoder data (24-bit values as int32)
        """
        raw = (encoder_in * coarse_red) >> 4
        rem = raw & 0xFFF
        ind = raw >> 12
        temp_out = raw + ((diff_table_in[ind] * (0x1000 - rem) + diff_table_in[ind + 1] * rem) >> 5)
        data_out = np.int32((temp_out << 4) / coarse_red) & 0xFFFFFF
        return data_out

    @staticmethod
    def filt_enc(encoder_in: np.ndarray, window_size: int) -> np.ndarray:
        """
        Applies a bidirectional moving average filter to encoder data.

        The filter processes data both forwards and backwards to minimize phase distortion,
        then averages both results for the final output.

        Args:
            encoder_in: Raw encoder input data (int32 values)
            window_size: Size of the moving average window

        Returns:
            np.ndarray: Filtered encoder data (int32 values)
        """
        encoder_ext = np.int32(LenzEncoderProcessor.ext_gen(np.int32(encoder_in)))
        len_enc = len(encoder_ext)
        vel_filt_1 = np.double(np.zeros(len_enc))
        vel_filt_1[0:window_size] = np.double(np.ones(window_size) * (encoder_ext[window_size] - encoder_ext[0])) / window_size
        for vel_cou in range(window_size, len_enc):
            vel_diff = np.double(encoder_ext[vel_cou] - encoder_ext[vel_cou - window_size])
            vel_filt_1[vel_cou] = vel_filt_1[vel_cou - 1] + (vel_diff / window_size - vel_filt_1[vel_cou - 1]) / window_size
        encoder_filt_1 = np.double(np.zeros(len_enc))
        encoder_filt_1[0] = np.double(encoder_ext[0])
        for filt_cou in range(1, len_enc):
            encoder_filt_1[filt_cou] = encoder_filt_1[filt_cou - 1] + vel_filt_1[filt_cou - 1]
            err = encoder_filt_1[filt_cou] - np.double(encoder_ext[filt_cou])
            encoder_filt_1[filt_cou] -= err / (1 * window_size)
        vel_filt_2 = np.double(np.zeros(len(encoder_ext)))
        fin_vel = encoder_ext[len_enc - 1] - encoder_ext[len_enc - 1 - window_size]
        vel_filt_2[len_enc - window_size:] = np.double(np.ones(window_size) * fin_vel) / window_size
        for vel_cou in range(len_enc - window_size - 1, -1, -1):
            vel_diff = np.double(encoder_ext[vel_cou + window_size] - encoder_ext[vel_cou])
            vel_filt_2[vel_cou] = vel_filt_2[vel_cou + 1] + (vel_diff / window_size - vel_filt_2[vel_cou + 1]) / window_size
        encoder_filt_2 = np.double(np.zeros(len_enc))
        encoder_filt_2[len_enc - 1] = np.double(encoder_ext[len_enc - 1])
        for filt_cou in range(len_enc - 2, -1, -1):
            encoder_filt_2[filt_cou] = encoder_filt_2[filt_cou + 1] - vel_filt_2[filt_cou + 1]
            err = encoder_filt_2[filt_cou] - np.double(encoder_ext[filt_cou])
            encoder_filt_2[filt_cou] -= err / (1 * window_size)
        encoder_filt = (encoder_filt_1 + encoder_filt_2) / 2
        return np.int32(encoder_filt)

    @staticmethod
    def diff_table_gen(diff_in: np.ndarray, enc_fix: np.ndarray, coarse_red: int) -> np.ndarray:
        """
        Generates a difference compensation table from error measurements.

        The table is created by averaging error measurements at each position,
        then applying FFT-based filtering to remove noise.

        Args:
            diff_in: Array of measured errors (double)
            enc_fix: Array of fixed encoder positions corresponding to errors (int32)
            coarse_red: Coarse reduction factor (scaling parameter)

        Returns:
            np.ndarray: Generated difference table (int16 values)
        """
        diff_table_temp = np.zeros(coarse_red * 256, 'double')
        for i in range(len(diff_table_temp)):
            find_diff = np.double(diff_in[enc_fix == i])
            if np.size(find_diff) == 0:
                diff_table_temp[i] = diff_table_temp[i - 1]
            else:
                diff_table_temp[i] = np.mean(find_diff)
        fft_dif = np.fft.fft(diff_table_temp)
        fft_dif[np.abs(fft_dif) < 200] = 0
        fft_dif[[1, -1]] = 0
        out_table = np.int16(np.real(np.fft.ifft(fft_dif)))
        return np.append(out_table, out_table[0])

    @staticmethod
    def diff_table_gen_motor_harm(diff_in: np.ndarray, enc_fix: np.ndarray,
                                  coarse_red: int, motor_harm: int) -> np.ndarray:
        """
        Generates difference table with additional motor harmonic suppression.

        Similar to DifTableGen but specifically removes motor-related harmonics
        from the compensation table.

        Args:
            diff_in: Array of measured errors (double)
            enc_fix: Array of fixed encoder positions (int32)
            coarse_red: Coarse reduction factor
            motor_harm: Motor harmonic frequency to suppress

        Returns:
            np.ndarray: Generated difference table with motor harmonics removed (int16)
        """
        motor_harm = np.int32(motor_harm)
        diff_table_temp = np.zeros(coarse_red * 256, 'double')
        for i in range(len(diff_table_temp)):
            find_diff = np.double(diff_in[enc_fix == i])
            if np.size(find_diff) == 0:
                diff_table_temp[i] = diff_table_temp[i - 1]
            else:
                diff_table_temp[i] = np.mean(find_diff)
        fft_dif = np.fft.fft(diff_table_temp)
        fft_dif[np.abs(fft_dif) < 200] = 0
        fft_dif[[1, -1]] = 0
        if motor_harm > 0:
            fft_dif[[2, -2]] = 0
            if motor_harm % coarse_red != 0:
                fft_dif[[motor_harm, -motor_harm]] = 0
            if (2 * motor_harm) % coarse_red != 0:
                fft_dif[[2 * motor_harm, -2 * motor_harm]] = 0
            if (3 * motor_harm) % coarse_red != 0:
                fft_dif[[3 * motor_harm, -3 * motor_harm]] = 0
            if (4 * motor_harm) % coarse_red != 0:
                fft_dif[[4 * motor_harm, -4 * motor_harm]] = 0
            if (6 * motor_harm) % coarse_red != 0:
                fft_dif[[6 * motor_harm, -6 * motor_harm]] = 0
        out_table = np.int16(np.real(np.fft.ifft(fft_dif)))
        return np.append(out_table, out_table[0])

    @staticmethod
    def diff_gen(enc_filt: np.ndarray, enc_in: np.ndarray, coarse_red: int) -> np.ndarray:
        """
        Generates difference signal between filtered and raw encoder data.

        Args:
            enc_filt: Filtered encoder data
            enc_in: Raw encoder input data
            coarse_red: Coarse reduction factor

        Returns:
            np.ndarray: Difference signal (double)
        """
        return np.double((np.int32(enc_filt - enc_in) * 2**8) / 2**8) * coarse_red / 2**11

    @staticmethod
    def lenz_cal(encoder_in: np.ndarray, coarse_red: int) -> np.ndarray:
        """
        Main calibration routine for LENZ encoder compensation.

        Performs a two-stage calibration process to generate a final compensation table.

        Args:
            encoder_in: Raw encoder input data
            coarse_red: Coarse reduction factor

        Returns:
            np.ndarray: Final compensation table (int8 values)
        """
        enc_data = np.int32(encoder_in)
        filt_window = np.int32(2**23 / coarse_red)
        window_size_calc = np.int32(1)
        while ((np.int32(enc_data[window_size_calc] - enc_data[0]) << 8) >> 8) < filt_window:
            window_size_calc = window_size_calc + 1
        enc_fix = np.int32(((enc_data * coarse_red / 2**15 + 1) / 2))
        enc_filt_1 = LenzEncoderProcessor.filt_enc(enc_data, window_size_calc)
        diff_1 = LenzEncoderProcessor.diff_gen(enc_filt_1, enc_data, coarse_red)
        diff_table_1 = LenzEncoderProcessor.diff_table_gen(diff_1, enc_fix, coarse_red)
        enc_comp = LenzEncoderProcessor.comp_diff(enc_data, diff_table_1, coarse_red)
        window_size_calc = window_size_calc >> 1
        enc_filt_2 = LenzEncoderProcessor.filt_enc(enc_comp, window_size_calc)
        diff_2 = LenzEncoderProcessor.diff_gen(enc_filt_2, enc_data, coarse_red)
        diff_table_2 = LenzEncoderProcessor.diff_table_gen(
            diff_2[2*window_size_calc:-2*window_size_calc],
            enc_fix[2*window_size_calc:-2*window_size_calc], coarse_red)
        diff_table_2 = diff_table_2 - (max(diff_table_2) + min(diff_table_2)) / 2
        diff_table_2[diff_table_2 > 127] = 127
        diff_table_2[diff_table_2 < -128] = 128
        return np.int8(diff_table_2[:-1])

    @staticmethod
    def lenz_cal_motor_harm(encoder_in: np.ndarray, coarse_red: int, motor_harm: int) -> np.ndarray:
        """
        LENZ encoder calibration with additional motor harmonic suppression.

        Similar to lenz_cal method but includes motor harmonic removal in the compensation table.

        Args:
            encoder_in: Raw encoder input data
            coarse_red: Coarse reduction factor
            motor_harm: Motor harmonic frequency to suppress

        Returns:
            np.ndarray: Final compensation table with motor harmonics removed (int8)
        """
        enc_data = np.int32(encoder_in)
        filt_window = np.int32(2**23 / coarse_red)
        window_size_calc = np.int32(1)
        while ((np.int32(enc_data[window_size_calc] - enc_data[0]) << 8) >> 8) < filt_window:
            window_size_calc = window_size_calc + 1
        enc_fix = np.int32(((enc_data * coarse_red / 2**15 + 1) / 2))
        enc_filt_1 = LenzEncoderProcessor.filt_enc(enc_data, window_size_calc)
        diff_1 = LenzEncoderProcessor.diff_gen(enc_filt_1, enc_data, coarse_red)
        diff_table_1 = LenzEncoderProcessor.diff_table_gen_motor_harm(diff_1, enc_fix, coarse_red, motor_harm)
        enc_comp = LenzEncoderProcessor.comp_diff(enc_data, diff_table_1, coarse_red)
        window_size_calc = window_size_calc >> 1
        enc_filt_2 = LenzEncoderProcessor.filt_enc(enc_comp, window_size_calc)
        diff_2 = LenzEncoderProcessor.diff_gen(enc_filt_2, enc_data, coarse_red)
        diff_table_2 = LenzEncoderProcessor.diff_table_gen_motor_harm(
            diff_2[2*window_size_calc:-2*window_size_calc],
            enc_fix[2*window_size_calc:-2*window_size_calc], coarse_red, motor_harm)
        diff_table_2 = diff_table_2 - (max(diff_table_2) + min(diff_table_2)) / 2
        diff_table_2[diff_table_2 > 127] = 127
        diff_table_2[diff_table_2 < -128] = 128
        return np.int8(diff_table_2[:-1])
