# adsb-tracker
# author: Youri Le Cottier

from pushbullet import Pushbullet
from pushbullet.errors import InvalidKeyError
from opensky_api import OpenSkyApi
import time
import math
import sys

home_latitude = 43.543312
home_longitude = 5.389706

# define bounding box (above aix-en-provence, france)
bounding_box_large = (43, 44, 5, 6)
bounding_box_aix = (43.466127, 43.547553, 5.270863, 5.428791)

pushbullet_api_key = ""


class Aircraft:

    def __init__(self, icao_code, callsign, latitude, longitude, geo_altitude, velocity):
        self.icao_code = icao_code  # ICAO unique ID, used as identifier.
        self.callsign = callsign
        self.latitude = latitude
        self.longitude = longitude
        self.geo_altitude = geo_altitude
        self.velocity = velocity

    def get_relative_coordinates(self):
        """
        Returns location (azimuth, altitude_angle, distance) relative to "home" location.
        :return:
        """
        altitude_feet = self.geo_altitude * 3.28084
        c_radius_of_earth = 6371
        c_feet_to_km = 0.0003048

        f1 = math.radians(home_latitude)
        f2 = math.radians(self.latitude)
        delta_f = math.radians(self.latitude - home_latitude)
        delta_g = math.radians(self.longitude - home_longitude)
        a = math.sin(delta_f / 2) * math.sin(delta_f / 2) + math.cos(f1) * math.cos(f2) * math.sin(
            delta_g / 2) * math.sin(
            delta_g / 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        self.distance_km = round(c_radius_of_earth * c)

        bearing_radians = math.atan2(
            math.sin(self.longitude - home_longitude) * math.cos(self.latitude)
            , math.cos(home_latitude) * math.sin(self.latitude) - math.sin(home_latitude) * math.cos(self.latitude)
            * math.cos(self.longitude - home_longitude)
        )

        self.relative_azimuth_degrees = round((360.0 - math.degrees(bearing_radians)) % 360.0)
        self.angle_altitude_degrees = round(
            math.degrees(math.atan(altitude_feet * c_feet_to_km / self.distance_km)))  # returns azimuth.

    def get_2d_coordinates(self):
        """
        Returns x,y coordinates on a 2D plane depending on the aircraft's relative distance and angles.
        :return:
        """

        base_x = 0
        base_y = 0

        # https://stackoverflow.com/questions/9871727/how-to-get-coordinates-of-a-point-in-a-coordinate-system-based-on-angle-and-dist
        pointX = base_x + self.distance_km * math.cos(angle)
        pointY = base_y + self.distance_km * math.sin(angle)


print("Initializing...")

api = OpenSkyApi()

try:
    pb = Pushbullet(pushbullet_api_key)
except InvalidKeyError:
    print("Invalid API key.")
    sys.exit()

print("Waiting for planes...")

tracked_aircraft = []

while True:
    print("================")

    states = api.get_states(bbox=bounding_box_aix)

    for s in states.states:
        aircraft = Aircraft(s.icao24, s.callsign, s.latitude, s.longitude, round(s.geo_altitude), round(s.velocity))
        tracked_aircraft.append(aircraft)
        message = aircraft.callsign + ": " + str(aircraft.geo_altitude) + "ft, " + str(aircraft.velocity) + "kt"
        print(message)
        aircraft.get_relative_coordinates()
        print("Altitude angle: " + str(aircraft.angle_altitude_degrees) + " degrees")
        print("Relative azimuth (counterclockwise): " + str(aircraft.relative_azimuth_degrees) + " degrees")
        print("Distance: " + str(aircraft.distance_km) + "km")
        print("-------------")

        # push using pushbullet
        push = pb.push_note(s.callsign + "Overhead!", message)

    time.sleep(10)  # wait 10 seconds for opensky rate limiting
