r'''
 _     _____ _   _ _____   _____ _   _  ____ ___  ____  _____ ____  ____
| |   | ____| \ | |__  /  | ____| \ | |/ ___/ _ \|  _ \| ____|  _ \/ ___|
| |   |  _| |  \| | / /   |  _| |  \| | |  | | | | | | |  _| | |_) \___ \
| |___| |___| |\  |/ /_   | |___| |\  | |__| |_| | |_| | |___|  _ < ___) |
|_____|_____|_| \_/____|  |_____|_| \_|\____\___/|____/|_____|_| \_|____/


Color definition class for stdout and progress bar purposes

Author:
    LENZ ENCODERS, 2020-2026
'''


class TermColors:

    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    GRAY = '\033[90m'

    Bold = "\033[1m"
    Dim = "\033[2m"
    Underlined = "\033[4m"
    Blink = "\033[5m"
    Reverse = "\033[7m"
    Hidden = "\033[8m"

    ResetBold = "\033[21m"
    ResetDim = "\033[22m"
    ResetUnderlined = "\033[24m"
    ResetBlink = "\033[25m"
    ResetReverse = "\033[27m"
    ResetHidden = "\033[28m"

    Default = "\033[39m"
    Black = "\033[30m"
    Red = "\033[31m"
    Green = "\033[32m"
    Yellow = "\033[33m"
    Blue = "\033[34m"
    Magenta = "\033[35m"
    Cyan = "\033[36m"
    LightGray = "\033[37m"
    DarkGray = "\033[90m"
    LightRed = "\033[91m"
    LightGreen = "\033[92m"
    LightYellow = "\033[93m"
    LightBlue = "\033[94m"
    LightMagenta = "\033[95m"
    LightCyan = "\033[96m"
    White = "\033[97m"

    BackgroundDefault = "\033[49m"
    BackgroundBlack = "\033[40m"
    BackgroundRed = "\033[41m"
    BackgroundGreen = "\033[42m"
    BackgroundYellow = "\033[43m"
    BackgroundBlue = "\033[44m"
    BackgroundMagenta = "\033[45m"
    BackgroundCyan = "\033[46m"
    BackgroundLightGray = "\033[47m"
    BackgroundDarkGray = "\033[100m"
    BackgroundLightRed = "\033[101m"
    BackgroundLightGreen = "\033[102m"
    BackgroundLightYellow = "\033[103m"
    BackgroundLightBlue = "\033[104m"
    BackgroundLightMagenta = "\033[105m"
    BackgroundLightCyan = "\033[106m"
    BackgroundWhite = "\033[107m"

    # 256-color pastel foreground palette (38;5;N)
    PastelBabyBlue = "\033[38;5;153m"
    PastelAquamarine = "\033[38;5;116m"
    PastelSage = "\033[38;5;150m"
    PastelSeafoam = "\033[38;5;114m"
    PastelButtercup = "\033[38;5;222m"
    PastelLemon = "\033[38;5;229m"
    PastelCoral = "\033[38;5;216m"
    PastelSalmon = "\033[38;5;210m"
    PastelRose = "\033[38;5;217m"
    PastelPink = "\033[38;5;174m"
    PastelBlush = "\033[38;5;224m"
    PastelLavender = "\033[38;5;139m"
    PastelOrchid = "\033[38;5;182m"
    PastelDustyPink = "\033[38;5;181m"
    PastelSand = "\033[38;5;179m"
    PastelKhaki = "\033[38;5;186m"
    PastelSilver = "\033[38;5;188m"
    PastelGray = "\033[38;5;253m"
    PastelDarkGray = "\033[38;5;245m"
    PastelPowderBlue = "\033[38;5;152m"
    PastelOrange = "\033[38;5;208m"
    PastelPeriwinkle = "\033[38;5;146m"
    PastelDustyRose = "\033[38;5;137m"
