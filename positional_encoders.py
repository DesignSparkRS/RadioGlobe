import time
import threading
import spidev

ENCODER_RESOLUTION = 1024


class Positional_Encoders (threading.Thread):

    def __init__(self, threadID, name, latitude_offset=0, longitude_offset=0):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name

        self.latch_stickiness = None
        self.latitude = 0
        self.longitude = 0
        self.latitude_offset = latitude_offset
        self.longitude_offset = longitude_offset

        # Enable SPI
        self.spi = spidev.SpiDev()

    def zero(self):
        # Relative to the centre of the map
        self.latitude_offset = (ENCODER_RESOLUTION // 2) - self.latitude
        self.longitude_offset = (ENCODER_RESOLUTION // 2) - self.longitude

        # Return the offsets so that they can be stored
        return [self.latitude_offset, self.longitude_offset]

    def get_readings(self):
        return [(self.latitude + self.latitude_offset) % ENCODER_RESOLUTION,
                (self.longitude + self.longitude_offset) % ENCODER_RESOLUTION]

    def latch(self, latitude: int, longitude: int, stickiness: int):
        self.latch_stickiness = stickiness

        # Need to convert the latched values to take account of the offset, or it would
        # likely unlatch immediately
        self.latitude = (latitude - self.latitude_offset) % ENCODER_RESOLUTION
        self.longitude = (longitude - self.longitude_offset) % ENCODER_RESOLUTION

    def is_latched(self):
        if self.latch_stickiness is not None:
            return True
        return False

    def check_parity(self, reading: int):
        # The parity bit is bit 0 (note the reading is most-significant-bit first)
        reading_without_parity_bit = reading >> 1
        parity_bit = reading & 0b1

        computed_parity = 0
        while reading_without_parity_bit:
            # XOR with the first bit
            computed_parity ^= (reading_without_parity_bit & 0b1)

            # Shift the bits right
            reading_without_parity_bit >>= 1

        return (parity_bit == computed_parity)

    def read_spi(self):
        BUS = 0
        readings = []

        # Two devices (chip select pins)
        for device in [0, 1]:
            self.spi.open(BUS, device)  # Set SPI speed and mode
            self.spi.max_speed_hz = 5000
            self.spi.mode = 1
            reading = self.spi.readbytes(2)
            self.spi.close()

            # Turn the list of bytes into 16-bit integers
            raw_reading = reading[0] << 8
            raw_reading |= reading[1]

            if self.check_parity(raw_reading):
                # The position reading is in the top 10 bits, so shift the lowest 6 bits out
                readings.append(raw_reading >> 6)
            else:
                return None

        return readings

    def run(self):
        while True:
            readings = self.read_spi()

            if readings:
                # Invert the latitude reading
                readings[0] = ENCODER_RESOLUTION - readings[0]

                if self.latch_stickiness is None:
                    # Not 'stuck', so just update the coords
                    self.latitude = readings[0]
                    self.longitude = readings[1]
                else:
                    # Check to see if the latch should 'come unstuck'
                    lat_difference = abs(self.latitude - readings[0]) % ENCODER_RESOLUTION
                    if lat_difference > self.latch_stickiness:
                        self.latch_stickiness = None
                        continue

                    lon_difference = abs(self.longitude - readings[1]) % ENCODER_RESOLUTION
                    if lon_difference > self.latch_stickiness:
                        self.latch_stickiness = None
                        continue

            time.sleep(0.2)
