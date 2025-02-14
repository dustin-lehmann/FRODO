from PIL import ImageFont

from bilbo_old.utilities.display.display import Page, DISPLAY_HEIGHT, DISPLAY_WIDTH


class StatusPage(Page):
    def __init__(self):
        """
        Initialize the Status page with dynamic elements.
        """
        super().__init__(width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, name="Status", border=True, show_title=False)
        self.battery_level = "full"  # Options: "empty", "half", "full"
        self.battery_voltage = "16.8V"
        self.internet_connected = False
        self.joystick = False  # Whether the joystick is connected (True = filled, False = crossed out)
        self.user = "user"
        self.hostname = "hostname"
        self.ip_address = "0.0.0.0"
        self.ssid = "SSID"
        self.mode = "Idle"

    def set_battery(self, level, voltage: (int, float)):
        """Set the battery level and voltage."""
        self.battery_level = level
        self.battery_voltage = str(voltage) + ' V'

    def set_internet_status(self, connected):
        """Set the internet connection status."""
        self.internet_connected = connected

    def set_joystick_status(self, connected):
        """Set the joystick connection status."""
        self.joystick = connected

    def set_user_and_hostname(self, user, hostname):
        """Set the user and hostname."""
        self.user = user
        self.hostname = hostname

    def set_ip_address(self, ip):
        """Set the IP address."""
        if ip is not None:
            self.ip_address = ip
        else:
            self.ip_address = ""

    def set_ssid(self, ssid):
        """Set the WiFi SSID."""
        if ssid is not None:
            self.ssid = ssid
        else:
            self.ssid = ''

    def set_mode(self, mode):
        """Set the current mode."""
        if mode is not None:
            self.mode = mode
        else:
            self.mode = ''

    def draw_page(self):
        """Draw the Status page."""
        font = ImageFont.load_default()

        # Header Bar
        self._draw_status_bar(font)

        # Text block starting y-coordinate, shifted up by 3 pixels
        start_y = 15

        # Four lines of information
        self.draw.text((5, start_y), f"{self.user}@{self.hostname}", font=font, fill=255)
        self.draw.text((5, start_y + 12), f"IP: {self.ip_address}", font=font, fill=255)
        self.draw.text((5, start_y + 24), f"SSID: {self.ssid}", font=font, fill=255)
        self.draw.text((5, start_y + 36), f"Mode: {self.mode}", font=font, fill=255)

    def _draw_status_bar(self, font):
        """Draw the header bar with battery, internet, and joystick icons."""
        # Battery Icon
        battery_x = 2
        battery_y = 2
        battery_width = 16
        battery_height = 8
        terminal_width = 2

        # Draw battery outline
        self.draw.rectangle(
            (battery_x, battery_y, battery_x + battery_width, battery_y + battery_height),
            outline=255,
            fill=0,
        )

        # Draw battery terminal
        self.draw.rectangle(
            (
                battery_x + battery_width,
                battery_y + 2,
                battery_x + battery_width + terminal_width,
                battery_y + battery_height - 2,
            ),
            outline=255,
            fill=255,
        )

        # Fill battery based on level
        if self.battery_level == "empty":
            fill_width = 0
        elif self.battery_level == "half":
            fill_width = (battery_width - 2) // 2
        elif self.battery_level == "full":
            fill_width = battery_width - 2

        if fill_width > 0:
            self.draw.rectangle(
                (
                    battery_x + 1,
                    battery_y + 1,
                    battery_x + 1 + fill_width,
                    battery_y + battery_height - 1,
                ),
                outline=255,
                fill=255,
            )

        # Battery voltage text
        self.draw.text((battery_x + battery_width + terminal_width + 4, battery_y - 2), self.battery_voltage, font=font,
                       fill=255)

        # Internet status icon
        internet_x = battery_x + battery_width + terminal_width + 50
        if self.internet_connected:
            self.draw.ellipse((internet_x, battery_y, internet_x + 8, battery_y + 8), outline=255,
                              fill=255)  # Filled circle
        else:
            self.draw.ellipse((internet_x, battery_y, internet_x + 8, battery_y + 8), outline=255,
                              fill=0)  # Empty circle
            self.draw.line((internet_x, battery_y, internet_x + 8, battery_y + 8), fill=255, width=1)  # Cross line

        # Joystick status icon
        joystick_x = internet_x + 20
        joystick_y = battery_y
        if self.joystick:
            self.draw.rectangle(
                (joystick_x, joystick_y, joystick_x + 8, joystick_y + 8), outline=255, fill=255
            )  # Filled rectangle
        else:
            self.draw.rectangle(
                (joystick_x, joystick_y, joystick_x + 8, joystick_y + 8), outline=255, fill=0
            )  # Empty rectangle
            self.draw.line((joystick_x, joystick_y, joystick_x + 8, joystick_y + 8), fill=255)  # Cross line
            self.draw.line((joystick_x + 8, joystick_y, joystick_x, joystick_y + 8), fill=255)  # Cross line

        # Line under the status bar
        self.draw.line((0, battery_y + battery_height + 2, self.width, battery_y + battery_height + 2), fill=255)
