from serial.tools import list_ports
import serial
from time import sleep
from PIL import Image

NUL, LF, HT, FF, ESC, GS, SP, SO, DC2, DC4 = b"\x00", b"\x0A", b"\x09", b"\x0C", b"\x1B", b"\x1D", b"\x20", b"\x0E", b"\x12", b"\x14"

def byte(n):
    return n.to_bytes(1, byteorder='big')

class Primter:
    """Goochpert!"""
    
    def __init__(self):
        ports = list_ports.comports()
        if 1 <= len(ports):
            self.serial = serial.Serial(ports[0].device)
        else:
            raise Exception("No serial devices found :(")
        
    def write(self, bytes):
        """write a bytestring to the printer"""
        if type(bytes) == str:
            bytes = bytes.encode()
        print(bytes)
        self.serial.write(bytes)
    
    def read(self, n_bytes):
        """read a number of bytes from the printer"""
        string = self.serial.read(n_bytes)
        print(string)
        
    def line_feed(self, n=1):
        """Print buffer and line feed n lines"""
        self.write(LF * n)
        
    def tab(self, n=1):
        """Jump tab n times"""
        self.write(HT * n)
    
    def print_feed_dots(self, n):
        """Print and feed n dots ∈ {0..255} (1dot = ⅛mm)"""
        if n in range(0x100):
            self.write(ESC + b'J' + byte(n))
    
    def print_feed_lines(self, n):
        """Print and feed n lines ∈ {0..255}
        
        Note: line height is determined by [re]set_line_spacing()
        """
        if n in range(0x100):
            self.write(ESC + b'd' + byte(n))
    
    def reset_line_spacing(self):
        """Reset to default line spacing (32 dots, 4mm)"""
        self.write(ESC + b'2')
    
    def set_line_spacing(self, n):
        """Set line spacing in dots ∈ {0..255} (1dot = ⅛mm)"""
        if n in range(0x100):
            self.write(ESC + b'3' + byte(n))
    
    def set_alignment(self, align):
        "Set text alignment ∈ {left, middle, right}"
        symbols = {
            "left":     b"\x00",
            "middle":   b"\x01",
            "right":    b"\x02"
        }
        if align in symbols:
            self.write(ESC + b'a' + symbols[align])
    
    def set_indent_dots(self, n):
        """Set the left blank margin in dots ∈ {0..65535} (1dot = ⅛mm)"""
        if n in range(0x10000):
            nL = n & 0x00FF
            nH = (n & 0xFF00) >> 8
            self.write(ESC + b'$' + byte(nL) + byte(nH))
    
    def set_print_modes(self, *options):
        """Select print mode(s) (defaults to reset)
        
        Options: reverse, updown, emphasis, tall, wide, deleteline
        
        Pass a list of the wanted options as strings.
        """
        
        flags = {
            "reverse":    0b00000010,
            "updown":     0b00000100,
            "emphasis":   0b00001000,
            "tall":       0b00010000,
            "wide":       0b00100000,
            "deleteline": 0b01000000
        }
        n = 0
        for flag in options:
            if flag in flags:
                n += flags[flag]
        self.write(ESC + b'!' + byte(n))
    
    def toggle_large_font(self, is_tall=False, is_wide=False):
        """Set or unset the double width and height (defaults to unset)"""
        n = 0
        if is_tall:
            n += 0b00001111
        if is_wide:
            n += 0b11110000
        self.write(GS + b'!' + byte(n))
    
    def toggle_bold_font(self, is_bold):
        """Set or unset bold font (defaults to unset)"""
        n = 1 if is_bold else 0
        self.write(ESC + b'E' + byte(n))
        
    def set_char_spacing(self, n):
        """Set the space between chars in dots"""
        if n in range(0x100):
            self.write(ESC + SP + byte(n))
    
    def toggle_double_width(self, is_wide):
        """Turn double width on or off"""
        symbol = SO if is_wide else DC4
        self.write(ESC + symbol)
    
    def toggle_upside_down(self, is_upside_down):
        """Turn upside-down printing mode on/off"""
        n = 1 if is_upside_down else 0
        self.write(ESC + b'{' + byte(n))
    
    def toggle_inverted_colors(self, is_inverted):
        """Turn inverted color mode on/off"""
        n = 1 if is_inverted else 0
        self.write(GS + b'B' + byte(n))
    
    def set_underline_height(self, n=0):
        """Set the underline thickness in dots ∈ {0..2} (defaults to 0)"""
        if n in range(3):
            self.write(ESC + b'-' + byte(n))
        
    def set_use_custom_chars(self, is_enabled):
        """Enable/disable custom characters"""
        n = 1 if is_enabled else 0
        self.write(ESC + b'%' + byte(n))
    
    def define_custom_char(self, char_to_replace, image):
        """Define custom characters"""
        s = 3   # character height in bytes
        n = ord(char_to_replace)  # character starting code
        m = ord(char_to_replace)  # character ending code
        w = len(image[0])
        self.write(ESC + b'&' + byte(s) + byte(n) + byte(m) + byte(w))
        x = 0
        for v_block in range(s):
            for col in range(w):
                d = 0
                for row in range(8):
                    if image[v_block*8 + row][col]:
                        d += 1 << (7-row)
                self.write(byte(d))

    def print_short_bitimg(self, image, double_width=False):
        """Print a bit-image that is the height of a row of characters.
        
        image height ∈ {8, 24} (2 different resolutions)
        image width ∈ {0..192} (double width)
                 OR ∈ {0..384} (single width)
        Note: may clear the custom characters
        """
        image = image.convert('1')
        h = image.height
        w = image.width
        if h not in [8, 24]:
            return False
        m = 0
        if double_width:
            if w > 192:
                return False
        else:
            m += 1
            if w > 384:
                return False
        if h == 24:
            m += 32
        nL = w & 0x00FF
        nH = (w & 0xFF00) >> 8
        bytes = ESC + b'*' + byte(m) + byte(nL) + byte(nH)
        for col in range(w):
            for block in range(h//8):
                d = 0
                for row in range(8):
                    if image.getpixel((col, block*8 + row)) == 0:
                        d += 1 << (7-row)
                bytes += byte(d)
        self.write(bytes)
    
    def define_bitimg(self, array):
        """Define loaded bit-image"""
        x = 1
        y = 8
        bytes = b""
        for b in array:
            bytes += byte(b)
        self.write(GS + b'*' + byte(x) + byte(y) + bytes)
    
    def print_defined_bitimg(self):
        """Print loaded bit-image"""
        self.write(GS + b'/' + byte(0))
    
    def print_bitimg(self):
        """"""
        pass
    
    def print_scaled_bitimg(self, array):
        """Print bit-image with width and height"""
        w = 135
        h = 135
        maxChunkHeight = 255
        rowBytes = (w + 7) // 8
        rowBytesClipped = 48 if rowBytes >= 48 else rowBytes
        chunkHeightLimit = 256 // rowBytesClipped;
        if chunkHeightLimit > maxChunkHeight:
            chunkHeightLimit = maxChunkHeight
        elif chunkHeightLimit < 1:
            chunkHeightLimit = 1
        for rowStart in range(0, h, chunkHeightLimit):
            i = rowStart
            chunkHeight = h - rowStart
            if chunkHeight > chunkHeightLimit:
                chunkHeight = chunkHeightLimit
            self.write(DC2 + b'*' + byte(chunkHeight) + byte(rowBytesClipped))
            for y in range(chunkHeight):
                for x in range(rowBytesClipped):
                    self.write(byte(array[i]))
                    i += 1
                i += rowBytes - rowBytesClipped
            sleep(0.01)
        self.line_feed(3)
        
    def print_msb_bitimg(self):
        """Print MSB bit-image"""
        pass
    
    def print_lsb_bitimg(self):
        """Print LSB bit-image"""
        pass
    
    def reset(self):
        """Resets the printer to default modes and clears data"""
        self.write(ESC + b'@')
    
    def get_sensor_feedback(self):
        """Read the paper, voltage, and temperature status from the device"""
        self.write(ESC + b'v')
        return(self.read(8))
    
    def set_automatic_feedback(self):
        """Enable/Disable Automatic Status Back (ASB)"""
        pass
    
    def set_barcode_char_position(self, position):
        """Set where the human-readable characters are printed in barcodes ∈ {none, above, below, both}"""
        positions = {
            "none":  b"\x00",
            "above": b"\x01",
            "below": b"\x02",
            "both":  b"\x03"
        }
        if position in positions:
            self.write(GS + b'H' + positions[position])
    
    def set_barcode_height_dots(self, n):
        """Set bar code height ∈ {1..255}"""
        if n in range(1, 0x100):
            self.write(GS + b'h' + byte(n))
    
    def set_barcode_indent(self, n):
        """Set bar code left indent"""
        if n in range(0x100):
            self.write(GS + b'x' + byte(n))
    
    def set_barcode_width(self, n):
        """Set bar code width ∈ {2, 3}"""
        if n in range(2, 4):
            self.write(GS + b'w' + byte(n))
        
    def print_barcode(self, code, barcode_type):
        """Print bar code with given barcode type.
        
        Type    | length  | character set
        =================================
        UPC-A   | 11,12   | 0-9
        UPC-E   | 11,12   | 0-9
        EAN13   | 12,13   | 0-9
        EAN8    | 7,8     | 0-9
        CODE39  | >1      | 0-9A-Z $%/.+- 
        I25     | even >1 | 0-9
        ---------------------------------
        CODABAR | >1      | 0-9A-D$:/.+-
        CODE93  | >1      | 0x00-0x7F
        CODE128 | >1      | 0x00-0x7F
        CODE11  | >1      | 0-9
        MSI     | >1      | 0-9
        """
        types = {
            "UPC-A":    b"\x00", 
            "UPC-E":    b"\x01",
            "EAN13":    b"\x02",
            "EAN8":     b"\x03",
            "CODE39":   b"\x04",
            "I25":      b"\x05",
            "CODABAR":  b"\x06",
            "CODE93":   b"\x07",
            "CODE128":  b"\x08",
            "CODE11":   b"\x09",
            "MSI":      b"\x0a"
        }
        if barcode_type in types:
            self.write(GS + b'k' + types[barcode_type] + code.encode() + b"\x00")
    
    def set_control_params(self, max_heating_dots=64, heat_time=800, heat_interval=20):
        """Set printing parameters
        
        - The more max heating dots, the more peak current will be drawn
        when printing, and the faster printing speed. ∈ {8..2048} (default 64)
        - The more heating time, the more density, but the slower the printing
        speed. If heating time is too short, a blank page may occur. ∈ {30-2550}µs (default 800μs)
        - The more heating interval, the more clear, but the slower the
        printing speed. ∈ {0-2550}μs (default 20μs)
        """
        if max_heating_dots in range(8, 2049):
            n1 = (max_heating_dots // 8) - 1
            if heat_time in range(30, 2551):
                n2 = heat_time // 10
                if heat_interval in range(2551):
                    n3 = heat_interval // 10
                    self.write(ESC + b'7' + byte(n1) + byte(n2) + byte(n3))
    
    def set_sleep_delay(self, n):
        """Set time for control board to enter sleep mode after finishing printing ∈ {0..255}
        
        Note: When the control board is sleeping, it must be woken up by sending one byte 0xFF, and waiting 50ms before sending any more data.
        """
        if n in range(0x100):
            self.write(ESC + b'8' + byte(n) + byte(n >> 8))
    
    def set_print_settings(self, density, break_time):
        """Set printing density ∈ {50..100}% and break time ∈ {0..3750}μs"""
        n = 0
        if density in range(50, 101):
            n += (density - 50) // 5
            if break_time in range(3751):
                n += (break_time // 250) << 4
                self.write(DC2 + b'#' + byte(n))
    
    def print_test_page(self):
        """Print the built-in test page"""
        self.write(DC2 + b'T')
