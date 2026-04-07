import time
import smbus2 as smbus  # Library for I2C communication


# -------------------------------------------------------------------
# Global I2C Bus Object
# -------------------------------------------------------------------

# Open I2C bus number 1 for communication with the LCD module
BUS = smbus.SMBus(1)


def write_word(addr, data):
    """
    Write one byte to the LCD through the I2C interface.

    Parameters
    ----------
    addr : int
        I2C address of the LCD module.

    data : int
        Byte value to send to the LCD.

    Notes
    -----
    This function also controls the LCD backlight by modifying bit 3
    of the transmitted byte according to the global BLEN variable.
    """
    global BLEN

    temp = data

    # Enable or disable backlight by setting/clearing bit 3
    if BLEN == 1:
        temp |= 0x08
    else:
        temp &= 0xF7

    # Send final byte over I2C
    BUS.write_byte(addr, temp)


def send_command(comm):
    """
    Send a command byte to the LCD.

    Parameters
    ----------
    comm : int
        Command byte to send.

    Notes
    -----
    The LCD works in 4-bit mode, so each command is sent in two parts:
    - high nibble
    - low nibble
    """
    # Send high nibble
    buf = comm & 0xF0
    buf |= 0x04  # EN = 1, RS = 0, RW = 0
    write_word(LCD_ADDR, buf)
    time.sleep(0.002)

    buf &= 0xFB  # EN = 0
    write_word(LCD_ADDR, buf)

    # Send low nibble
    buf = (comm & 0x0F) << 4
    buf |= 0x04  # EN = 1, RS = 0, RW = 0
    write_word(LCD_ADDR, buf)
    time.sleep(0.002)

    buf &= 0xFB  # EN = 0
    write_word(LCD_ADDR, buf)


def send_data(data):
    """
    Send one data byte to the LCD for display.

    Parameters
    ----------
    data : int
        Data byte to display as a character.

    Notes
    -----
    Like commands, data is also sent in 4-bit mode:
    - high nibble first
    - low nibble second
    """
    # Send high nibble
    buf = data & 0xF0
    buf |= 0x05  # EN = 1, RS = 1, RW = 0
    write_word(LCD_ADDR, buf)
    time.sleep(0.002)

    buf &= 0xFB  # EN = 0
    write_word(LCD_ADDR, buf)

    # Send low nibble
    buf = (data & 0x0F) << 4
    buf |= 0x05  # EN = 1, RS = 1, RW = 0
    write_word(LCD_ADDR, buf)
    time.sleep(0.002)

    buf &= 0xFB  # EN = 0
    write_word(LCD_ADDR, buf)


def init(addr, bl):
    """
    Initialize the LCD module.

    Parameters
    ----------
    addr : int
        I2C address of the LCD.

    bl : int
        Backlight flag:
        1 = backlight ON
        0 = backlight OFF

    Returns
    -------
    bool
        True if initialization succeeded, False otherwise.

    Notes
    -----
    The initialization sequence sets:
    - 4-bit communication mode
    - 2 display lines
    - display ON
    - cursor OFF
    - screen clear
    """
    global LCD_ADDR
    global BLEN

    LCD_ADDR = addr
    BLEN = bl

    try:
        # Initialize LCD into 4-bit mode
        send_command(0x33)
        time.sleep(0.005)

        send_command(0x32)
        time.sleep(0.005)

        # Set 2-line mode, 5x7 font
        send_command(0x28)
        time.sleep(0.005)

        # Display ON, cursor OFF
        send_command(0x0C)
        time.sleep(0.005)

        # Clear screen
        send_command(0x01)
        time.sleep(0.005)

        # Turn on backlight
        BUS.write_byte(LCD_ADDR, 0x08)

    except Exception:
        return False
    else:
        return True


def clear():
    """
    Clear the LCD screen.
    """
    send_command(0x01)


def openlight():
    """
    Turn on the LCD backlight.

    Notes
    -----
    Uses the default LCD I2C address 0x27.
    """
    BUS.write_byte(0x27, 0x08)


def write(x, y, text):
    """
    Write text to a specific LCD position.

    Parameters
    ----------
    x : int
        Column position, valid range is 0 to 15.

    y : int
        Row position, valid range is 0 to 1.

    text : str
        Text string to display.
    """
    # Keep cursor position within LCD limits
    if x < 0:
        x = 0
    if x > 15:
        x = 15
    if y < 0:
        y = 0
    if y > 1:
        y = 1

    # Compute DDRAM address from row and column
    addr = 0x80 + 0x40 * y + x
    send_command(addr)

    # Send each character one by one
    for ch in text:
        send_data(ord(ch))
