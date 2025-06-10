
class BissCmdIrs(bytearray):
    start_bootloader_cmd = bytearray([5, 49, 246, 185])

    ans_start_bootloader_cmd = bytearray([249, 78, 177, 6])

    exit_bootloader_cmd = bytearray([0, 0, 0, 1, 255])

    ans_exit_bootloader_cmd = bytearray([0, 0, 0, 0, 0])
