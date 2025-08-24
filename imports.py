import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import threading
import time
import cv2
import numpy as np
import pytesseract
import sqlite3
import requests
import json
import re
from PIL.ExifTags import TAGS, GPSTAGS
import os
import hashlib

from algorithms.exif import exif_reading
from algorithms.haar import haar_detection
from algorithms.shadowcalc import detect_shadow
from algorithms.plate_rec import create_db, plate_recognition