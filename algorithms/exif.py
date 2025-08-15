from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import time

def exif_reading(self, image_path):
    """Valódi EXIF adatok kinyerése"""
    try:
        self.log("info", "EXIF", f"EXIF adatok keresése: {image_path}")

        # Kép megnyitása
        img = Image.open(image_path)
        exif_data = img._getexif()

        if not exif_data:
            self.log("warning", "EXIF", "Nincsenek EXIF adatok a képben.")
            return

        gps_info = {}
        for tag, value in exif_data.items():
            tag_name = TAGS.get(tag, tag)
            if tag_name == "GPSInfo":
                for key in value.keys():
                    gps_tag = GPSTAGS.get(key, key)
                    gps_info[gps_tag] = value[key]

        if not gps_info:
            self.log("warning", "EXIF", "Nem található GPS információ.")
            return

        # GPS koordináták konvertálása fokokra
        def convert_to_degrees(value):
            d, m, s = value
            return float(d[0] / d[1] + m[0] / m[1] / 60 + s[0] / s[1] / 3600)

        lat = convert_to_degrees(gps_info['GPSLatitude'])
        if gps_info['GPSLatitudeRef'] != "N":
            lat = -lat

        lon = convert_to_degrees(gps_info['GPSLongitude'])
        if gps_info['GPSLongitudeRef'] != "E":
            lon = -lon

        self.log("success", "EXIF", f"GPS koordináták: {lat:.6f}, {lon:.6f}")

        # Opcionálisan jelölés a képen (ha van vászon)
        if hasattr(self, 'canvas'):
            self.canvas.create_oval(300, 300, 310, 310, fill="red", outline="")

    except Exception as e:
        self.log("error", "EXIF", f"Hiba: {str(e)}")
