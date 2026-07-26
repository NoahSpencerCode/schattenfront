"""
World data pipeline.

Real Natural Earth geography (10m countries, 50m rivers) is preprocessed
once into compact numpy arrays (data/cache/vectors_v*.npz).  From those
we build the base globe texture, the land/water mask for movement rules,
the road/bridge network — and render high-detail map regions in realtime
while the camera is zoomed in (see globe.DetailOverlay).
"""

import json
import math
import os
import zlib

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from utils import smooth_polyline, segment_intersection_point, latlon_dist_deg

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
CACHE_DIR = os.path.join(DATA_DIR, "cache")

COUNTRIES_10M = os.path.join(DATA_DIR, "ne_10m_admin_0_countries.geojson")
RIVERS_GEOJSON = os.path.join(DATA_DIR, "ne_50m_rivers_lake_centerlines.geojson")

# Texture / mask resolution (equirectangular)
TEX_W, TEX_H = 6144, 3072
MASK_W, MASK_H = 8192, 4096       # coarse mask: sea grid + refine A*
FINE_W, FINE_H = 32768, 16384     # fine mask (bit-packed): all legality
                                  # checks match the drawn coastline 4x
                                  # closer than the routing raster

# Narrow but historically navigable waters that a raster of this
# resolution would otherwise seal shut; carved into the mask as water.
NAVIGABLE_CHANNELS = [
    ((35.10, 139.65), (35.45, 139.78)),   # Uraga Channel (Tokyo Bay)
    ((55.75, 10.85), (54.75, 10.75)),     # Great Belt
    ((56.15, 12.65), (55.35, 12.90)),     # Oresund
    ((41.35, 29.15), (40.75, 28.20)),     # Bosporus
    ((40.75, 28.20), (40.00, 26.15)),     # Marmara / Dardanelles
    ((30.05, 32.57), (31.30, 32.35)),     # Suez Canal
    ((8.90, -79.56), (9.40, -79.92)),     # Panama Canal
    ((54.36, 10.14), (53.89, 9.13)),      # Kiel Canal
    ((34.70, 135.05), (34.58, 134.96)),   # Akashi Strait (Inland Sea)
    ((34.02, 130.83), (33.90, 131.02)),   # Kanmon Strait (Shimonoseki)
    ((38.28, 15.58), (38.08, 15.65)),     # Strait of Messina
    ((48.20, -122.78), (47.90, -122.42)), # Admiralty Inlet (Puget Sound)
    ((34.55, 134.90), (34.30, 133.60)),   # Seto Inland Sea lane (east)
    ((34.30, 133.60), (34.00, 132.50)),   # Seto Inland Sea lane (west)
    ((34.00, 132.50), (33.95, 131.05)),   # Seto lane to Kanmon
]

CACHE_VERSION = 5   # vectors + land mask
TEXTURE_VERSION = 36  # bump to repaint the base globe texture only

# --- WW2 globe palette -------------------------------------------------------
OCEAN = (44, 58, 79)          # dull navy blue
LAND = (205, 191, 156)        # old paper
BORDER = (110, 99, 82)        # etched border lines
RIVER = (82, 118, 158)        # bright river blue
ROAD_EDGE = (170, 143, 104)   # pale verge either side of a road
ROAD = (122, 96, 62)          # dirt-road brown
CITY_DOT = (58, 46, 34)

# Rivers with scalerank <= this block land movement (and draw thicker).
MAJOR_RIVER_SCALERANK = 6

# ---------------------------------------------------------------------------
# Historical WW2 cities: (name, faction, lat, lon)
# The first city of each faction is its capital.
CITIES = [
    ('London', 'britain', 51.5074, -0.1278),
    ('Manchester', 'britain', 53.4808, -2.2426),
    ('Edinburgh', 'britain', 55.9533, -3.1883),
    ('Liverpool', 'britain', 53.4084, -2.9916),
    ('Birmingham', 'britain', 52.5086, -1.8754),
    ('Portsmouth', 'britain', 50.8158, -1.0880),
    ('Bristol', 'britain', 51.4545, -2.5879),
    ('Plymouth', 'britain', 50.3755, -4.1427),
    ('Glasgow', 'britain', 55.8642, -4.2518),
    ('Belfast', 'britain', 54.5973, -5.9301),

    ('Berlin', 'germany', 52.5200, 13.4050),
    ('Munich', 'germany', 48.1351, 11.5820),
    ('Hamburg', 'germany', 53.5511, 9.9937),
    ('Cologne', 'germany', 50.9375, 6.9603),
    ('Frankfurt', 'germany', 50.1109, 8.6821),
    ('Stuttgart', 'germany', 48.7758, 9.1829),
    ('Vienna', 'germany', 48.2082, 16.3738),
    ('Prague', 'germany', 50.0755, 14.4378),
    ('Warsaw', 'germany', 52.2297, 21.0122),
    ('Dresden', 'germany', 51.0504, 13.7373),

    ('Washington DC', 'usa', 38.9072, -77.0369),
    ('New York', 'usa', 40.7128, -74.0060),
    ('Los Angeles', 'usa', 34.0522, -118.2437),
    ('Chicago', 'usa', 41.8781, -87.6298),
    ('San Francisco', 'usa', 37.7749, -122.4194),
    ('Boston', 'usa', 42.3601, -71.0589),
    ('Philadelphia', 'usa', 39.9526, -75.1652),
    ('Houston', 'usa', 29.7604, -95.3698),
    ('Detroit', 'usa', 42.3314, -83.0458),
    ('Seattle', 'usa', 47.6062, -122.3321),
    # interior and southern towns so the national territory spans the
    # whole continental USA (border reach is ~700 km per city)
    ('Pittsburgh', 'usa', 40.4406, -79.9959),
    ('Cleveland', 'usa', 41.4993, -81.6944),
    ('Buffalo', 'usa', 42.8864, -78.8784),
    ('Baltimore', 'usa', 39.2904, -76.6122),
    ('Atlanta', 'usa', 33.7490, -84.3880),
    ('Miami', 'usa', 25.7617, -80.1918),
    ('New Orleans', 'usa', 29.9511, -90.0715),
    ('Memphis', 'usa', 35.1495, -90.0490),
    ('St. Louis', 'usa', 38.6270, -90.1994),
    ('Kansas City', 'usa', 39.0997, -94.5786),
    ('Minneapolis', 'usa', 44.9778, -93.2650),
    ('Omaha', 'usa', 41.2565, -95.9345),
    ('Oklahoma City', 'usa', 35.4676, -97.5164),
    ('Dallas', 'usa', 32.7767, -96.7970),
    ('San Antonio', 'usa', 29.4241, -98.4936),
    ('El Paso', 'usa', 31.7619, -106.4850),
    ('Denver', 'usa', 39.7392, -104.9903),
    ('Salt Lake City', 'usa', 40.7608, -111.8910),
    ('Phoenix', 'usa', 33.4484, -112.0740),
    ('Las Vegas', 'usa', 36.1699, -115.1398),
    ('Portland', 'usa', 45.5152, -122.6784),
    ('Boise', 'usa', 43.6150, -116.2023),
    ('Billings', 'usa', 45.7833, -108.5007),

    ('Tokyo', 'japan', 35.6762, 139.6503),
    ('Osaka', 'japan', 34.6937, 135.5023),
    ('Yokohama', 'japan', 35.4437, 139.6380),
    ('Kyoto', 'japan', 35.0116, 135.7681),
    ('Kobe', 'japan', 34.6901, 135.1955),
    ('Nagoya', 'japan', 35.1815, 136.9066),
    ('Sapporo', 'japan', 43.0642, 141.3469),
    ('Fukuoka', 'japan', 33.5904, 130.4017),
    ('Hiroshima', 'japan', 34.3853, 132.4553),
    ('Nagasaki', 'japan', 32.7503, 129.8711),

    ('Moscow', 'soviet', 55.7558, 37.6173),
    ('Leningrad', 'soviet', 59.9311, 30.3609),
    ('Kiev', 'soviet', 50.4501, 30.5234),
    ('Kharkov', 'soviet', 49.9935, 36.2304),
    ('Minsk', 'soviet', 53.9006, 27.5590),
    ('Smolensk', 'soviet', 54.7818, 32.0401),
    ('Gorky', 'soviet', 56.2965, 43.9361),
    ('Stalingrad', 'soviet', 48.7080, 44.5133),
    ('Rostov', 'soviet', 47.2357, 39.7015),
    ('Kuybyshev', 'soviet', 53.1959, 50.1002),

    # ---- the wider war: every town the five powers fought over.
    # Owners are as of 1 Sep 1939; everything not then held by one of
    # the five powers is NEUTRAL (annexable, but fields no armies).
    # Britain and her Empire
    ('Coventry', 'britain', 52.4068, -1.5197),
    ('Hull', 'britain', 53.7676, -0.3274),
    ('Southampton', 'britain', 50.9097, -1.4044),
    ('Dover', 'britain', 51.1279, 1.3134),
    # the Empire beyond the isles starts NEUTRAL: only cities in the
    # British Isles begin under London's direct command
    ('Gibraltar', 'brit_med', 36.1408, -5.3536),
    ('Valletta', 'brit_med', 35.8989, 14.5146),
    ('Cairo', 'brit_med', 30.0444, 31.2357),
    ('Alexandria', 'brit_med', 31.2001, 29.9187),
    ('Suez', 'brit_med', 29.9668, 32.5498),
    ('Jerusalem', 'brit_med', 31.7683, 35.2137),
    ('Haifa', 'brit_med', 32.7940, 34.9896),
    ('Singapore', 'fareast', 1.3521, 103.8198),
    ('Hong Kong', 'fareast', 22.3193, 114.1694),
    ('Kuala Lumpur', 'fareast', 3.1390, 101.6869),
    ('Rangoon', 'fareast', 16.8409, 96.1735),
    ('Mandalay', 'fareast', 21.9588, 96.0891),
    ('Calcutta', 'raj', 22.5726, 88.3639),
    ('Bombay', 'raj', 19.0760, 72.8777),
    ('Delhi', 'raj', 28.7041, 77.1025),
    ('Madras', 'raj', 13.0827, 80.2707),
    ('Colombo', 'raj', 6.9271, 79.8612),
    ('Sydney', 'australia', -33.8688, 151.2093),
    ('Darwin', 'australia', -12.4634, 130.8456),
    ('Port Moresby', 'australia', -9.4438, 147.1803),
    ('Rabaul', 'australia', -4.1998, 152.1631),
    ('Guadalcanal', 'australia', -9.4280, 160.0330),
    # Greater Germany
    ('Konigsberg', 'germany', 54.7104, 20.4522),
    ('Danzig', 'germany', 54.3520, 18.6466),
    ('Essen', 'germany', 51.4556, 7.0116),
    ('Leipzig', 'germany', 51.3397, 12.3731),
    ('Nuremberg', 'germany', 49.4521, 11.0767),
    ('Kiel', 'germany', 54.3233, 10.1228),
    # United States and possessions
    ('Honolulu', 'usa', 21.3069, -157.8583),
    ('Manila', 'usa', 14.5995, 120.9842),
    ('Guam', 'usa', 13.4757, 144.7489),
    # Empire of Japan and possessions
    ('Seoul', 'japan', 37.5665, 126.9780),
    ('Pusan', 'japan', 35.1796, 129.0756),
    ('Pyongyang', 'japan', 39.0392, 125.7625),
    ('Taipei', 'japan', 25.0330, 121.5654),
    ('Harbin', 'japan', 45.8038, 126.5350),
    ('Mukden', 'japan', 41.8057, 123.4315),
    ('Dairen', 'japan', 38.9140, 121.6147),
    ('Naha', 'japan', 26.2124, 127.6809),
    ('Saipan', 'japan', 15.1850, 145.7467),
    ('Truk', 'japan', 7.4458, 151.8500),
    # Soviet Union
    ('Sevastopol', 'soviet', 44.6166, 33.5254),
    ('Odessa', 'soviet', 46.4825, 30.7233),
    ('Murmansk', 'soviet', 68.9585, 33.0827),
    ('Archangelsk', 'soviet', 64.5401, 40.5433),
    ('Kursk', 'soviet', 51.7304, 36.1926),
    ('Voronezh', 'soviet', 51.6720, 39.1843),
    ('Novorossiysk', 'soviet', 44.7239, 37.7708),
    ('Vladivostok', 'soviet', 43.1332, 131.9113),
    # France
    ('Paris', 'france', 48.8566, 2.3522),
    ('Marseille', 'france', 43.2965, 5.3698),
    ('Lyon', 'france', 45.7640, 4.8357),
    ('Bordeaux', 'france', 44.8378, -0.5792),
    ('Toulon', 'france', 43.1242, 5.9280),
    ('Calais', 'france', 50.9513, 1.8587),
    ('Dunkirk', 'france', 51.0344, 2.3768),
    ('Dieppe', 'france', 49.9229, 1.0777),
    ('Cherbourg', 'france', 49.6337, -1.6221),
    ('Caen', 'france', 49.1829, -0.3707),
    ('Brest', 'france', 48.3904, -4.4861),
    # Low Countries
    ('Amsterdam', 'netherlands', 52.3676, 4.9041),
    ('Rotterdam', 'netherlands', 51.9244, 4.4777),
    ('Arnhem', 'netherlands', 51.9851, 5.8987),
    ('Eindhoven', 'netherlands', 51.4416, 5.4697),
    ('Brussels', 'belgium', 50.8503, 4.3517),
    ('Antwerp', 'belgium', 51.2194, 4.4025),
    ('Liege', 'belgium', 50.6326, 5.5797),
    ('Bastogne', 'belgium', 50.0039, 5.7215),
    # Scandinavia
    ('Oslo', 'norway', 59.9139, 10.7522),
    ('Narvik', 'norway', 68.4385, 17.4272),
    ('Trondheim', 'norway', 63.4305, 10.3951),
    ('Bergen', 'norway', 60.3913, 5.3221),
    ('Copenhagen', 'denmark', 55.6761, 12.5683),
    ('Helsinki', 'finland', 60.1699, 24.9384),
    ('Viipuri', 'finland', 60.7090, 28.7550),
    # Italy and her empire
    ('Rome', 'italy', 41.9028, 12.4964),
    ('Milan', 'italy', 45.4642, 9.1900),
    ('Turin', 'italy', 45.0703, 7.6869),
    ('Genoa', 'italy', 44.4056, 8.9463),
    ('Bologna', 'italy', 44.4949, 11.3426),
    ('Naples', 'italy', 40.8518, 14.2681),
    ('Foggia', 'italy', 41.4622, 15.5446),
    ('Salerno', 'italy', 40.6824, 14.7681),
    ('Anzio', 'italy', 41.4489, 12.6283),
    ('Cassino', 'italy', 41.4926, 13.8300),
    ('Palermo', 'italy', 38.1157, 13.3615),
    ('Messina', 'italy', 38.1938, 15.5540),
    ('Tripoli', 'italy', 32.8872, 13.1913),
    ('Benghazi', 'italy', 32.1167, 20.0667),
    ('Tobruk', 'italy', 32.0836, 23.9764),
    ('Addis Ababa', 'italy', 9.0300, 38.7400),
    ('Asmara', 'italy', 15.3229, 38.9251),
    # Balkans and Eastern Europe
    ('Athens', 'greece', 37.9838, 23.7275),
    ('Thessaloniki', 'greece', 40.6401, 22.9444),
    ('Heraklion', 'greece', 35.3387, 25.1442),
    ('Belgrade', 'yugoslavia', 44.7866, 20.4489),
    ('Zagreb', 'yugoslavia', 45.8150, 15.9819),
    ('Sarajevo', 'yugoslavia', 43.8563, 18.4131),
    ('Bucharest', 'romania', 44.4268, 26.1025),
    ('Ploiesti', 'romania', 44.9414, 26.0225),
    ('Budapest', 'hungary', 47.4979, 19.0402),
    ('Sofia', 'bulgaria', 42.6977, 23.3219),
    ('Krakow', 'poland', 50.0647, 19.9450),
    ('Lodz', 'poland', 51.7592, 19.4560),
    # Middle East
    ('Baghdad', 'iraq', 33.3152, 44.3661),
    ('Tehran', 'iran', 35.6892, 51.3890),
    ('Damascus', 'france', 33.5138, 36.2765),
    ('Beirut', 'france', 33.8938, 35.5018),
    # French and Italian Africa, Atlantic
    ('Casablanca', 'france', 33.5731, -7.5898),
    ('Oran', 'france', 35.6969, -0.6331),
    ('Algiers', 'france', 36.7538, 3.0588),
    ('Tunis', 'france', 36.8065, 10.1815),
    ('Dakar', 'france', 14.7167, -17.4677),
    # China and South-East Asia
    ('Shanghai', 'china', 31.2304, 121.4737),
    ('Nanking', 'china', 32.0603, 118.7969),
    ('Peking', 'china', 39.9042, 116.4074),
    ('Tientsin', 'china', 39.3434, 117.3616),
    ('Canton', 'china', 23.1291, 113.2644),
    ('Chungking', 'china', 29.4316, 106.9123),
    ('Wuhan', 'china', 30.5928, 114.3055),
    ('Changsha', 'china', 28.2282, 112.9388),
    ('Bangkok', 'siam', 13.7563, 100.5018),
    ('Saigon', 'france', 10.8231, 106.6297),
    ('Hanoi', 'france', 21.0278, 105.8342),
    ('Batavia', 'netherlands', -6.2088, 106.8456),
    ('Surabaya', 'netherlands', -7.2575, 112.7521),
    ('Palembang', 'netherlands', -2.9761, 104.7754),
]

# The five capitals (everything else, including neutral towns, is not)
CAPITALS = {'London', 'Berlin', 'Washington DC', 'Tokyo', 'Moscow',
            # NPC nation seats of government (1939)
            'Paris', 'Rome', 'Chungking', 'Krakow', 'Amsterdam',
            'Brussels', 'Oslo', 'Copenhagen', 'Helsinki', 'Athens',
            'Belgrade', 'Bucharest', 'Budapest', 'Sofia', 'Baghdad',
            'Tehran', 'Bangkok', 'Cairo', 'Delhi', 'Singapore',
            'Sydney'}

# Approximate WW2-era metropolitan populations, in THOUSANDS. Drives each
# city's drawn size and building count, and is reported in the city stats.
CITY_POPULATION = {
    # Britain
    'London': 8600, 'Manchester': 700, 'Edinburgh': 470, 'Liverpool': 850,
    'Birmingham': 1000, 'Portsmouth': 250, 'Bristol': 415, 'Plymouth': 210,
    'Glasgow': 1100, 'Belfast': 440,
    # Germany (Reich, incl. annexed capitals)
    'Berlin': 4340, 'Munich': 830, 'Hamburg': 1680, 'Cologne': 770,
    'Frankfurt': 550, 'Stuttgart': 460, 'Vienna': 1900, 'Prague': 950,
    'Warsaw': 1300, 'Dresden': 630,
    # United States
    'Washington DC': 660, 'New York': 7450, 'Los Angeles': 1500,
    'Chicago': 3400, 'San Francisco': 635, 'Boston': 770,
    'Philadelphia': 1930, 'Houston': 385, 'Detroit': 1620, 'Seattle': 370,
    'Pittsburgh': 670, 'Cleveland': 880, 'Buffalo': 575, 'Baltimore': 860,
    'Atlanta': 300, 'Miami': 170, 'New Orleans': 495, 'Memphis': 295,
    'St. Louis': 815, 'Kansas City': 400, 'Minneapolis': 490,
    'Omaha': 225, 'Oklahoma City': 205, 'Dallas': 295,
    'San Antonio': 255, 'El Paso': 97, 'Denver': 320,
    'Salt Lake City': 150, 'Phoenix': 65, 'Las Vegas': 8,
    'Portland': 305, 'Boise': 26, 'Billings': 32,
    # Japan
    'Tokyo': 6780, 'Osaka': 3250, 'Yokohama': 970, 'Kyoto': 1090,
    'Kobe': 970, 'Nagoya': 1330, 'Sapporo': 210, 'Fukuoka': 320,
    'Hiroshima': 340, 'Nagasaki': 250,
    # Soviet Union
    'Moscow': 4130, 'Leningrad': 3190, 'Kiev': 850, 'Kharkov': 830,
    'Minsk': 240, 'Smolensk': 160, 'Gorky': 640, 'Stalingrad': 445,
    'Rostov': 510, 'Kuybyshev': 390,
    # British Empire
    'Coventry': 220, 'Hull': 320, 'Southampton': 180, 'Dover': 40,
    'Gibraltar': 20, 'Valletta': 70, 'Cairo': 1300, 'Alexandria': 680,
    'Suez': 110, 'Jerusalem': 130, 'Haifa': 100, 'Singapore': 750,
    'Hong Kong': 1050, 'Kuala Lumpur': 110, 'Rangoon': 500,
    'Mandalay': 150, 'Calcutta': 2100, 'Bombay': 1500, 'Delhi': 700,
    'Madras': 780, 'Colombo': 360, 'Sydney': 1300, 'Darwin': 6,
    'Port Moresby': 3, 'Rabaul': 5, 'Guadalcanal': 3,
    # Greater Germany
    'Konigsberg': 370, 'Danzig': 250, 'Essen': 660, 'Leipzig': 700,
    'Nuremberg': 420, 'Kiel': 270,
    # United States possessions
    'Honolulu': 180, 'Manila': 630, 'Guam': 10,
    # Empire of Japan
    'Seoul': 930, 'Pusan': 250, 'Pyongyang': 290, 'Taipei': 350,
    'Harbin': 500, 'Mukden': 850, 'Dairen': 550, 'Naha': 65,
    'Saipan': 5, 'Truk': 3,
    # Soviet Union additions
    'Sevastopol': 110, 'Odessa': 600, 'Murmansk': 120,
    'Archangelsk': 280, 'Kursk': 120, 'Voronezh': 340,
    'Novorossiysk': 95, 'Vladivostok': 210,
    # France
    'Paris': 2850, 'Marseille': 630, 'Lyon': 570, 'Bordeaux': 260,
    'Toulon': 150, 'Calais': 70, 'Dunkirk': 30, 'Dieppe': 25,
    'Cherbourg': 40, 'Caen': 60, 'Brest': 80,
    # Low Countries
    'Amsterdam': 800, 'Rotterdam': 620, 'Arnhem': 90, 'Eindhoven': 110,
    'Brussels': 900, 'Antwerp': 270, 'Liege': 160, 'Bastogne': 5,
    # Scandinavia
    'Oslo': 280, 'Narvik': 10, 'Trondheim': 55, 'Bergen': 100,
    'Copenhagen': 700, 'Helsinki': 260, 'Viipuri': 75,
    # Italy and empire
    'Rome': 1300, 'Milan': 1100, 'Turin': 630, 'Genoa': 630,
    'Bologna': 320, 'Naples': 950, 'Foggia': 60, 'Salerno': 80,
    'Anzio': 10, 'Cassino': 20, 'Palermo': 400, 'Messina': 190,
    'Tripoli': 130, 'Benghazi': 65, 'Tobruk': 15, 'Addis Ababa': 150,
    'Asmara': 100,
    # Balkans and Eastern Europe
    'Athens': 1100, 'Thessaloniki': 240, 'Heraklion': 45,
    'Belgrade': 320, 'Zagreb': 190, 'Sarajevo': 80, 'Bucharest': 870,
    'Ploiesti': 80, 'Budapest': 1160, 'Sofia': 300, 'Krakow': 260,
    'Lodz': 660,
    # Middle East
    'Baghdad': 400, 'Tehran': 700, 'Damascus': 300, 'Beirut': 230,
    # Africa and Atlantic
    'Casablanca': 350, 'Oran': 220, 'Algiers': 300, 'Tunis': 220,
    'Dakar': 130,
    # China and South-East Asia
    'Shanghai': 3800, 'Nanking': 1000, 'Peking': 1550, 'Tientsin': 1200,
    'Canton': 1100, 'Chungking': 640, 'Wuhan': 800, 'Changsha': 500,
    'Bangkok': 680, 'Saigon': 250, 'Hanoi': 150, 'Batavia': 530,
    'Surabaya': 340, 'Palembang': 110,
}

HARBOR_CITIES = {
    'Portsmouth', 'Liverpool', 'Plymouth', 'Glasgow', 'Belfast',
    'Hamburg',
    'New York', 'San Francisco', 'Boston', 'Seattle', 'Houston',
    'Tokyo', 'Yokohama', 'Osaka', 'Kobe', 'Nagasaki', 'Hiroshima',
    'Leningrad',
}


def lonlat_to_px(lon, lat, w, h):
    x = (lon + 180.0) / 360.0 * w
    y = (90.0 - lat) / 180.0 * h
    return x, y


class WorldData:
    """Loads / builds all static world data. Construct once at game start."""

    def __init__(self, log=print):
        self.log = log
        os.makedirs(CACHE_DIR, exist_ok=True)

        self.cities = CITIES
        self.rivers = []            # [(lon,lat), ...] lists, gameplay rivers
        self.country_labels = []    # (name, lat, lon)
        self.roads = []             # (city_index_a, city_index_b)
        self.rail_paths = []        # national main lines, lat/lon curves
        self.bridges = []           # dicts {lat, lon, road}
        self.land_mask = None       # np.bool_ [MASK_H, MASK_W], True = land

        self._load_vectors()
        self._build_gameplay_rivers()
        self._build_land_mask()          # coarse: routing grids
        self._build_fine_mask()          # fine: coastline-true legality
        self._smooth_rivers()            # one smooth curve everywhere
        from terrain import Terrain
        self.terrain = Terrain(self.log)     # real ETOPO1 relief
        self._build_roads_and_bridges()
        self._build_rails()
        self._build_city_plans()         # one fixed layout per city
        self._build_sites()              # airfield/harbor sites + spurs
        self.texture_path = self._build_texture()

    # ================================================ vector preprocessing
    def _vectors_cache(self):
        return os.path.join(CACHE_DIR, "vectors_v%d.npz" % CACHE_VERSION)

    def _load_vectors(self):
        path = self._vectors_cache()
        if not os.path.exists(path):
            self._preprocess_vectors(path)
        z = np.load(path, allow_pickle=False)
        self.poly_pts = z['poly_pts']          # float32 [N,2] lon,lat
        self.poly_off = z['poly_off']          # int64 [R+1]
        self.poly_hole = z['poly_hole']        # bool [R]
        self.poly_bbox = z['poly_bbox']        # float32 [R,4]
        self.river_pts = z['river_pts']
        self.river_off = z['river_off']
        self.river_major = z['river_major']
        self.river_bbox = z['river_bbox']
        label_pos = z['label_pos']
        names = [n for n in z['label_names']]
        self.country_labels = [(str(names[i]), float(label_pos[i][0]),
                                float(label_pos[i][1]))
                               for i in range(len(names))]
        self.log("Vector store: %d polygon rings, %d river lines, %d labels"
                 % (len(self.poly_hole), len(self.river_major),
                    len(self.country_labels)))

    @staticmethod
    def _iter_polygons(feature):
        geom = feature['geometry']
        if geom['type'] == 'Polygon':
            yield geom['coordinates']
        elif geom['type'] == 'MultiPolygon':
            for poly in geom['coordinates']:
                yield poly

    def _preprocess_vectors(self, path):
        """One-time: parse GeoJSON into flat numpy arrays (draw order)."""
        self.log("Preprocessing geographic data (first run only)...")
        with open(COUNTRIES_10M) as f:
            feats = json.load(f)['features']

        def ring_area(ring):
            a = 0.0
            for i in range(len(ring) - 1):
                a += (ring[i][0] * ring[i + 1][1] -
                      ring[i + 1][0] * ring[i][1])
            return abs(a) / 2.0

        # order features big -> small so enclaves overwrite their hosts
        sized = []
        for feat in feats:
            area = sum(ring_area(p[0]) for p in self._iter_polygons(feat))
            sized.append((area, feat))
        sized.sort(key=lambda t: -t[0])

        pts_chunks, offs, holes, bboxes = [], [0], [], []
        labels, label_names = [], []
        total = 0
        for area, feat in sized:
            best_ring, best_area = None, 0.0
            for poly in self._iter_polygons(feat):
                for k, ring in enumerate(poly):
                    if len(ring) < 4:
                        continue
                    arr = np.asarray(ring, dtype=np.float32)
                    pts_chunks.append(arr)
                    total += len(arr)
                    offs.append(total)
                    holes.append(k > 0)
                    bboxes.append((arr[:, 0].min(), arr[:, 1].min(),
                                   arr[:, 0].max(), arr[:, 1].max()))
                    if k == 0:
                        a = ring_area(ring)
                        if a > best_area:
                            best_area, best_ring = a, arr
            if best_ring is not None and best_area >= 25.0:
                name = feat['properties'].get('NAME', '')
                labels.append((float(best_ring[:, 1].mean()),
                               float(best_ring[:, 0].mean())))
                label_names.append(name.upper())

        with open(RIVERS_GEOJSON) as f:
            rfeats = json.load(f)['features']
        r_chunks, r_offs, r_major, r_bbox = [], [0], [], []
        rtotal = 0
        for feat in rfeats:
            props = feat['properties']
            geom = feat['geometry']
            lines = ([geom['coordinates']] if geom['type'] == 'LineString'
                     else geom['coordinates'])
            major = (props.get('scalerank', 99) <= MAJOR_RIVER_SCALERANK and
                     'lake' not in (props.get('featurecla') or '').lower())
            for line in lines:
                if len(line) < 2:
                    continue
                arr = np.asarray([(p[0], p[1]) for p in line],
                                 dtype=np.float32)
                r_chunks.append(arr)
                rtotal += len(arr)
                r_offs.append(rtotal)
                r_major.append(major)
                r_bbox.append((arr[:, 0].min(), arr[:, 1].min(),
                               arr[:, 0].max(), arr[:, 1].max()))

        np.savez_compressed(
            path,
            poly_pts=np.concatenate(pts_chunks).astype(np.float32),
            poly_off=np.asarray(offs, dtype=np.int64),
            poly_hole=np.asarray(holes, dtype=bool),
            poly_bbox=np.asarray(bboxes, dtype=np.float32),
            river_pts=np.concatenate(r_chunks).astype(np.float32),
            river_off=np.asarray(r_offs, dtype=np.int64),
            river_major=np.asarray(r_major, dtype=bool),
            river_bbox=np.asarray(r_bbox, dtype=np.float32),
            label_pos=np.asarray(labels, dtype=np.float32),
            label_names=np.asarray(label_names, dtype='U64'))

    def poly_ring(self, i):
        return self.poly_pts[self.poly_off[i]:self.poly_off[i + 1]]

    def river_line(self, i):
        return self.river_pts[self.river_off[i]:self.river_off[i + 1]]

    def _smooth_rivers(self):
        """Every river becomes a Catmull-Rom ribbon: the drawn water,
        the bridge siting and the crossing checks all share this ONE
        smooth geometry, so what blocks a column is what is inked."""
        pts, offs = [], [0]
        for i in range(len(self.river_off) - 1):
            sm = smooth_polyline(self.river_line(i), max_seg_deg=0.01)
            pts.append(sm)
            offs.append(offs[-1] + len(sm))
        self.river_pts = np.vstack(pts).astype(np.float32)
        self.river_off = np.array(offs, dtype=np.int64)

    # ================================================== gameplay rivers
    def _build_gameplay_rivers(self):
        self.rivers = []
        for i in range(len(self.river_major)):
            if self.river_major[i]:
                self.rivers.append([tuple(p) for p in self.river_line(i)])
        self.river_buckets = {}
        for pts in self.rivers:
            for i in range(len(pts) - 1):
                seg = (pts[i], pts[i + 1])
                for key in self._bucket_keys_for_segment(seg):
                    self.river_buckets.setdefault(key, []).append(seg)
        self.log("Gameplay rivers: %d" % len(self.rivers))

    @staticmethod
    def _bucket_keys_for_segment(seg, size=2.0):
        (x1, y1), (x2, y2) = seg
        keys = set()
        for bx in range(int(min(x1, x2) // size), int(max(x1, x2) // size) + 1):
            for by in range(int(min(y1, y2) // size), int(max(y1, y2) // size) + 1):
                keys.add((bx, by))
        return keys

    def river_segments_near(self, lon, lat, size=2.0):
        out = []
        bx, by = int(lon // size), int(lat // size)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                out.extend(self.river_buckets.get((bx + dx, by + dy), ()))
        return out

    # ================================================== roads / bridges
    def segment_on_land(self, lat1, lon1, lat2, lon2, step_deg=0.1):
        """True if the great-circle between two points stays on land."""
        a = np.array([math.cos(math.radians(lat1)) * math.cos(math.radians(lon1)),
                      math.cos(math.radians(lat1)) * math.sin(math.radians(lon1)),
                      math.sin(math.radians(lat1))])
        b = np.array([math.cos(math.radians(lat2)) * math.cos(math.radians(lon2)),
                      math.cos(math.radians(lat2)) * math.sin(math.radians(lon2)),
                      math.sin(math.radians(lat2))])
        ang = math.acos(max(-1.0, min(1.0, float(a.dot(b)))))
        n = max(2, int(math.degrees(ang) / step_deg) + 1)
        t = np.linspace(0.0, 1.0, n + 1)
        so = math.sin(ang) if ang > 1e-9 else 1.0
        pts = (np.sin((1.0 - t) * ang) / so)[:, None] * a + \
              (np.sin(t * ang) / so)[:, None] * b
        lat = np.degrees(np.arcsin(np.clip(pts[:, 2], -1.0, 1.0)))
        lon = np.degrees(np.arctan2(pts[:, 1], pts[:, 0]))
        return bool(self.fine_flags(lat, lon).all())

    def _build_roads_and_bridges(self):
        by_country = {}
        for idx, (name, country, lat, lon) in enumerate(self.cities):
            by_country.setdefault(country, []).append(idx)

        def dist(i, j):
            a, b = self.cities[i], self.cities[j]
            return latlon_dist_deg((a[3], a[2]), (b[3], b[2]))

        def on_land(i, j):
            a, b = self.cities[i], self.cities[j]
            return self.segment_on_land(a[2], a[3], b[2], b[3])

        edges = set()
        for country, idxs in by_country.items():
            # the five powers get a national trunk network (MST over
            # land-connected pairs; the sea is served by transports).
            # Neutral towns get no world-spanning tree -- only the local
            # neighbour links below tie them into the road web.
            if country == 'neutral' or len(idxs) < 2:
                continue
            in_tree = {idxs[0]}
            while len(in_tree) < len(idxs):
                best = None
                for i in in_tree:
                    for j in idxs:
                        if j in in_tree:
                            continue
                        d = dist(i, j)
                        if best is None or d < best[0]:
                            best = (d, i, j)
                if best[0] <= 18.0 and on_land(best[1], best[2]):
                    edges.add((min(best[1], best[2]), max(best[1], best[2])))
                in_tree.add(best[2])
        # every city (any owner) ties into its two nearest neighbours
        # within reach -- the continental road web crosses frontiers
        n_all = len(self.cities)
        for i in range(n_all):
            near = sorted((dist(i, j), j) for j in range(n_all) if j != i)
            linked = 0
            for d, j in near:
                if linked >= 2 or d > 10.0:
                    break
                if on_land(i, j):
                    edges.add((min(i, j), max(i, j)))
                    linked += 1
        self.roads = sorted(edges)

        # Give every road a snaking, organic centre-line instead of a
        # pin-straight great-circle. Deterministic per city pair; displaced
        # midpoints are nudged back onto land so a road never runs to sea.
        self.road_paths = {}
        road_coarse = {}
        for (i, j) in self.roads:
            a, b = self.cities[i], self.cities[j]
            coarse = self._curved_road_points(
                a[2], a[3], b[2], b[3],
                zlib.crc32(("road:%d-%d" % (i, j)).encode()),
                smooth=False)
            road_coarse[(i, j)] = coarse
            self.road_paths[(i, j)] = [
                tuple(p) for p in smooth_polyline(np.array(coarse))]

        # Bridges sit wherever a road's centre-line actually crosses a
        # gameplay river -- scanned segment by segment along the curve.
        self.bridges = []
        for (i, j) in self.roads:
            path = road_coarse[(i, j)]
            dense = np.array(self.road_paths[(i, j)])
            lons = [p[1] for p in path]
            lats = [p[0] for p in path]
            rbb = (min(lons) - 0.5, min(lats) - 0.5,
                   max(lons) + 0.5, max(lats) + 0.5)
            for pts in self.rivers:
                rl = [q[0] for q in pts]
                rt = [q[1] for q in pts]
                if (max(rl) < rbb[0] or min(rl) > rbb[2] or
                        max(rt) < rbb[1] or min(rt) > rbb[3]):
                    continue
                for si in range(len(path) - 1):
                    pa = (path[si][1], path[si][0])
                    pb = (path[si + 1][1], path[si + 1][0])
                    for k in range(len(pts) - 1):
                        hit = segment_intersection_point(
                            pa, pb, pts[k], pts[k + 1])
                        if hit:
                            # snap the bridge onto the smooth ribbon so
                            # it sits exactly on the drawn road
                            d2 = ((dense[:, 0] - hit[1]) ** 2
                                  + (dense[:, 1] - hit[0]) ** 2)
                            sk = min(int(np.argmin(d2)), len(dense) - 2)
                            self.bridges.append({
                                'lon': float(dense[sk][1]),
                                'lat': float(dense[sk][0]),
                                'road': (i, j),
                                'seg': (dense[sk][0], dense[sk][1],
                                        dense[sk + 1][0],
                                        dense[sk + 1][1]),
                            })
        self.log("Road network: %d roads, %d bridges" %
                 (len(self.roads), len(self.bridges)))

    def _curved_road_points(self, lat1, lon1, lat2, lon2, seed, passes=5,
                            smooth=True, amp=0.16):
        """A gently snaking centre-line between two cities: recursive
        midpoint displacement, each displaced point pulled back onto land
        if it strays over water. Returns [(lat, lon), ...] incl. endpoints."""
        rng = np.random.RandomState(seed & 0xffffffff)
        pts = [(lat1, lon1), (lat2, lon2)]
        for _ in range(passes):          # 5 passes -> up to 33 vertices
            out = [pts[0]]
            for k in range(len(pts) - 1):
                la1, lo1 = pts[k]
                la2, lo2 = pts[k + 1]
                mla = (la1 + la2) * 0.5
                mlo = (lo1 + lo2) * 0.5
                dla = la2 - la1
                dlo = lo2 - lo1
                seglen = math.hypot(dla, dlo)
                nrm = seglen or 1e-6
                pla = -dlo / nrm         # unit perpendicular in lat/lon
                plo = dla / nrm
                # the road SEEKS THE VALLEY: several candidate bends are
                # drawn and the one with the least height and climb wins
                # (deterministic: the rng draw count is fixed)
                cands = [seglen * amp * float(rng.uniform(-1.0, 1.0))
                         for _ in range(4)] + [0.0]
                run_m = max(1.0, 0.5 * seglen * 111120.0)
                e_ends = 0.5 * (self.terrain.elev_at(la1, lo1)
                                + self.terrain.elev_at(la2, lo2))
                best, best_cost = (mla, mlo), None
                for d in cands:
                    cla = mla + pla * d
                    clo = mlo + plo * d
                    tries = 0
                    while not self.is_land(cla, clo) and tries < 4:
                        d *= 0.4
                        cla = mla + pla * d
                        clo = mlo + plo * d
                        tries += 1
                    if not self.is_land(cla, clo):
                        continue
                    ec = self.terrain.elev_at(cla, clo)
                    grade = abs(ec - e_ends) / run_m
                    cost = ec + 120000.0 * grade
                    if best_cost is None or cost < best_cost:
                        best, best_cost = (cla, clo), cost
                cla, clo = best
                out.append((cla, clo))
                out.append((la2, lo2))
            pts = out
            amp *= 0.55
        if smooth:
            # the control points become a Catmull-Rom ribbon: perfectly
            # smooth on screen, and the SAME dense curve feeds the route
            # graph so movement matches rendering exactly
            return [tuple(p) for p in smooth_polyline(np.array(pts))]
        return pts

    # ================================================== land mask
    def _mask_cache(self):
        return os.path.join(CACHE_DIR, "land_mask_v%d_%d.npy"
                            % (CACHE_VERSION, MASK_W))

    def _build_land_mask(self):
        path = self._mask_cache()
        if os.path.exists(path):
            self.land_mask = np.load(path)
            return
        self.log("Rasterizing land mask (first run only)...")
        img = Image.new('L', (MASK_W, MASK_H), 0)
        draw = ImageDraw.Draw(img)
        sx = MASK_W / 360.0
        sy = MASK_H / 180.0
        for i in range(len(self.poly_hole)):
            ring = self.poly_ring(i)
            xy = np.empty_like(ring)
            xy[:, 0] = (ring[:, 0] + 180.0) * sx
            xy[:, 1] = (90.0 - ring[:, 1]) * sy
            draw.polygon(xy.ravel().tolist(),
                         fill=0 if self.poly_hole[i] else 255)
        # keep the narrow straits and canals of the world open
        for ((la1, lo1), (la2, lo2)) in NAVIGABLE_CHANNELS:
            draw.line([((lo1 + 180.0) * sx, (90.0 - la1) * sy),
                       ((lo2 + 180.0) * sx, (90.0 - la2) * sy)],
                      fill=0, width=3)
        self.land_mask = np.asarray(img) > 127
        np.save(path, self.land_mask)

    # ------------------------------------------------ fine coastline mask
    def _fine_cache(self):
        return os.path.join(CACHE_DIR, "land_bits_v%d_%d.npy"
                            % (CACHE_VERSION, FINE_W))

    def _build_fine_mask(self):
        """A 4x-finer land mask, bit-packed (64MB), rasterized from the
        same vector polygons the map draws. Every point/segment legality
        check samples this, so units and routes follow the DRAWN
        coastline instead of the coarse routing raster. Built in
        horizontal bands to bound memory."""
        path = self._fine_cache()
        if os.path.exists(path):
            self.land_bits = np.load(path)
            return
        self.log("Rasterizing fine coastline mask (first run only)...")
        bands = 8
        bh = FINE_H // bands
        sx = FINE_W / 360.0
        sy = FINE_H / 180.0
        packed = []
        for b in range(bands):
            y_off = b * bh
            lat_top = 90.0 - y_off / sy
            lat_bot = 90.0 - (y_off + bh) / sy
            img = Image.new('L', (FINE_W, bh), 0)
            draw = ImageDraw.Draw(img)
            for i in range(len(self.poly_hole)):
                bb = self.poly_bbox[i]
                if bb[1] > lat_top or bb[3] < lat_bot:
                    continue
                ring = self.poly_ring(i)
                xy = np.empty_like(ring)
                xy[:, 0] = (ring[:, 0] + 180.0) * sx
                xy[:, 1] = (90.0 - ring[:, 1]) * sy - y_off
                draw.polygon(xy.ravel().tolist(),
                             fill=0 if self.poly_hole[i] else 255)
            for ((la1, lo1), (la2, lo2)) in NAVIGABLE_CHANNELS:
                draw.line([((lo1 + 180.0) * sx, (90.0 - la1) * sy - y_off),
                           ((lo2 + 180.0) * sx, (90.0 - la2) * sy - y_off)],
                          fill=0, width=12)
            packed.append(np.packbits(np.asarray(img) > 127, axis=1))
        self.land_bits = np.vstack(packed)
        np.save(path, self.land_bits)

    def fine_flags(self, lat, lon):
        """Vector-grade land flags for arrays of degrees."""
        x = ((lon + 180.0) / 360.0 * FINE_W).astype(np.int64) % FINE_W
        y = np.clip(((90.0 - lat) / 180.0 * FINE_H).astype(np.int64),
                    0, FINE_H - 1)
        return ((self.land_bits[y, x >> 3] >> (7 - (x & 7))) & 1) \
            .astype(bool)

    def is_land(self, lat, lon):
        x = int((lon + 180.0) / 360.0 * FINE_W) % FINE_W
        y = max(0, min(FINE_H - 1, int((90.0 - lat) / 180.0 * FINE_H)))
        return bool((self.land_bits[y, x >> 3] >> (7 - (x & 7))) & 1)

    def is_water(self, lat, lon):
        return not self.is_land(lat, lon)

    def _nearest_terrain(self, lat, lon, want_land, max_deg=6.0):
        check = self.is_land if want_land else self.is_water
        if check(lat, lon):
            return lat, lon
        # fine rings near the point (snap tight to the drawn coastline),
        # coarsening with distance
        r = 0.04
        while r <= max_deg:
            n = max(12, int(r * 90))
            for k in range(n):
                ang = 2 * math.pi * k / n
                la = lat + r * math.sin(ang)
                lo = lon + r * math.cos(ang)
                if check(la, lo):
                    return la, lo
            r += max(0.04, r * 0.35)
        return lat, lon

    def _is_open_water(self, lat, lon, spread=0.07):
        """Water with water all around — not a sealed pond or basin."""
        if not self.is_water(lat, lon):
            return False
        for dla, dlo in ((spread, 0), (-spread, 0), (0, spread),
                         (0, -spread), (spread, spread),
                         (-spread, -spread)):
            if not self.is_water(lat + dla, lon + dlo):
                return False
        return True

    def nearest_water(self, lat, lon, max_deg=6.0):
        """Nearest OPEN water (ships must be able to leave it); falls
        back to any water pixel if nothing open is in range."""
        if self._is_open_water(lat, lon):
            return lat, lon
        fallback = None
        r = 0.04
        while r <= max_deg:
            n = max(12, int(r * 90))
            for k in range(n):
                ang = 2 * math.pi * k / n
                la = lat + r * math.sin(ang)
                lo = lon + r * math.cos(ang)
                if self._is_open_water(la, lo):
                    return la, lo
                if fallback is None and self.is_water(la, lo):
                    fallback = (la, lo)
            r += max(0.04, r * 0.35)
        if fallback is not None:
            return fallback
        return self._nearest_terrain(lat, lon, False, max_deg)

    def nearest_land(self, lat, lon, max_deg=6.0):
        return self._nearest_terrain(lat, lon, True, max_deg)

    # ============================================ airfield/harbor sites
    def _build_sites(self):
        """Deterministic airfield and harbor sites (the server and every
        client must agree on the map), plus the spur roads that tie them
        to town. Air and sea infrastructure is CONCENTRATED: each power
        operates THREE airfields (the capital and its largest cities)
        and THREE harbors (its largest coastal cities); neutral towns
        only rate either if they hold a million souls or more. Harbors
        go where open water is near; the quay sits ON the drawn water,
        which is also where new hulls take to the sea."""
        self.airfield_sites = {}
        self.harbor_sites = {}
        self.armypost_sites = {}
        self.airfield_spurs = {}        # name -> the DRAWN polyline; the
        self.harbor_spurs = {}          # route graph follows it exactly
        self.spur_paths = []

        def popk(name):
            return CITY_POPULATION.get(name, 120)

        # which cities can host a quay at all (open water within reach)
        coastal = {}
        for (name, country, lat, lon) in self.cities:
            wl, wo = self.nearest_water(lat, lon, max_deg=1.6)
            if (self.is_water(wl, wo)
                    and latlon_dist_deg((lon, lat), (wo, wl)) <= 1.6):
                coastal[name] = (float(wl), float(wo))

        by_country = {}
        for entry in self.cities:
            by_country.setdefault(entry[1], []).append(entry)
        air_ok, harbor_ok, post_ok = set(), set(), set()
        from config import PLAYABLE
        for country, group in by_country.items():
            ranked = sorted(group, key=lambda g: -popk(g[0]))
            if country in PLAYABLE:
                # the great powers: TWO of everything, at the biggest
                # towns (harbors at the biggest COASTAL towns)
                for g in ranked[:2]:
                    air_ok.add(g[0])
                    post_ok.add(g[0])
                sea = [g for g in ranked if g[0] in coastal]
                for g in sea[:2]:
                    harbor_ok.add(g[0])
            else:
                # NPC nations: one field at the seat of government and
                # one quay at the biggest coastal town
                cap = next((g for g in ranked if g[0] in CAPITALS),
                           ranked[0])
                air_ok.add(cap[0])
                sea = [g for g in ranked if g[0] in coastal]
                if sea:
                    harbor_ok.add(sea[0][0])

        for (name, country, lat, lon) in self.cities:
            if name in air_ok:
                rng = np.random.RandomState(
                    zlib.crc32(('airfield:' + name).encode()) & 0xffffffff)
                site = None
                for b in rng.permutation(range(0, 360, 30)):
                    la = lat + 0.7 * math.sin(math.radians(b))
                    lo = lon + 0.7 * math.cos(math.radians(b)) / \
                        max(0.2, math.cos(math.radians(lat)))
                    if (self.is_land(la, lo) and self.is_land(la + 0.08, lo)
                            and self.is_land(la - 0.08, lo)):
                        site = (float(la), float(lo))
                        break
                if site is None:
                    site = self.nearest_land(lat, lon + 0.75)
                self.airfield_sites[name] = site
                spur = self._curved_road_points(
                    lat, lon, site[0], site[1],
                    zlib.crc32(('spur:af:' + name).encode()), passes=3)
                self.airfield_spurs[name] = spur
                self.spur_paths.append(spur)
            if name in harbor_ok:
                wl, wo = coastal[name]
                self.harbor_sites[name] = (wl, wo)
                spur = self._curved_road_points(
                    lat, lon, wl, wo,
                    zlib.crc32(('spur:hb:' + name).encode()), passes=3)
                self.harbor_spurs[name] = spur
                self.spur_paths.append(spur)
            if name in post_ok:
                rng = np.random.RandomState(
                    zlib.crc32(('armypost:' + name).encode())
                    & 0xffffffff)
                site = None
                for b in rng.permutation(range(0, 360, 30)):
                    la = lat + 0.55 * math.sin(math.radians(b))
                    lo = lon + 0.55 * math.cos(math.radians(b)) / \
                        max(0.2, math.cos(math.radians(lat)))
                    if self.is_land(la, lo):
                        site = (float(la), float(lo))
                        break
                if site is None:
                    site = self.nearest_land(lat, lon - 0.6)
                self.armypost_sites[name] = site
                spur = self._curved_road_points(
                    lat, lon, site[0], site[1],
                    zlib.crc32(('spur:ap:' + name).encode()), passes=3)
                self.spur_paths.append(spur)

    # ================================================== base texture
    def _texture_cache(self):
        return os.path.join(CACHE_DIR, "globe_map_v%d.png" % TEXTURE_VERSION)

    def _build_texture(self):
        path = self._texture_cache()
        if os.path.exists(path):
            return path
        self.log("Painting the WW2 globe map (first run only)...")
        # NO roads in the static sheet: every road (map-born and
        # engineer-laid alike) is drawn by the live overlay and the
        # detail tiles, so a demolished road can actually disappear
        img = self.render_region(-180.0, -90.0, 180.0, 90.0,
                                 TEX_W, TEX_H, border_w=2, road_w=3,
                                 city_r=8, mottle=True, roads=False)
        img.save(path)
        self.log("Map texture saved: %s" % path)
        return path

    # ================================================== region rendering
    def render_region(self, lon0, lat0, lon1, lat1, w, h,
                      border_w=2, road_w=3, city_r=8, mottle=False,
                      land_only=False, ss=1, roads=True):
        """Draw a lon/lat window of the map at any resolution.

        Used both for the base globe texture and, in realtime, for the
        high-detail overlay while zoomed in.  Pure PIL/numpy — safe to
        call from a worker thread.  land_only stops after the land fill
        and rivers: the exact water shape the map displays, used to keep
        city buildings and streets off the water.  ss > 1 supersamples:
        everything is painted at ss times the resolution (stroke widths
        scaled to match) and LANCZOS-downsampled at the end, so lines
        and edges come out anti-aliased instead of stair-stepped.
        """
        out_w, out_h = w, h
        w, h = w * ss, h * ss
        border_w *= ss
        road_w *= ss
        img = Image.new('RGB', (w, h), OCEAN)
        draw = ImageDraw.Draw(img)
        sx = w / (lon1 - lon0)
        sy = h / (lat1 - lat0)
        # decimation margin: full detail near the window, sparse far away
        margin = max(2.0, 0.25 * (lat1 - lat0))
        full_window = (lon1 - lon0) >= 359.0

        def ring_pts(arr, s):
            """Transformed point list; far-from-window points decimated
            so a single huge polygon (Eurasia!) can't stall a frame."""
            if not full_window and len(arr) > 3000:
                lon = arr[:, 0] + s
                near = ((lon >= lon0 - margin) & (lon <= lon1 + margin) &
                        (arr[:, 1] >= lat0 - margin) &
                        (arr[:, 1] <= lat1 + margin))
                keep = near | (np.arange(len(arr)) % 40 == 0)
                keep[0] = keep[-1] = True
                arr = arr[keep]
            xy = np.empty_like(arr)
            xy[:, 0] = (arr[:, 0] + s - lon0) * sx
            xy[:, 1] = (lat1 - arr[:, 1]) * sy
            return xy.ravel().tolist()

        def index_shifts(bbox_arr):
            """(shift, indices) pairs of features intersecting the window,
            computed vectorized; index order (== draw order) preserved."""
            out = []
            for s in (0.0, -360.0, 360.0):
                m = ((bbox_arr[:, 0] + s <= lon1) &
                     (bbox_arr[:, 2] + s >= lon0) &
                     (bbox_arr[:, 1] <= lat1) & (bbox_arr[:, 3] >= lat0))
                # drop sub-pixel specks
                m &= (((bbox_arr[:, 2] - bbox_arr[:, 0]) * sx > 0.7) |
                      ((bbox_arr[:, 3] - bbox_arr[:, 1]) * sy > 0.7))
                idx = np.nonzero(m)[0]
                if len(idx):
                    out.append((s, idx))
            return out

        # land fill (rings pre-ordered big->small, holes flagged)
        poly_hits = index_shifts(self.poly_bbox)
        poly_cache = {}
        for s, idx in poly_hits:
            for i in idx:
                pts = ring_pts(self.poly_ring(i), s)
                poly_cache[(s, i)] = pts
                draw.polygon(pts,
                             fill=OCEAN if self.poly_hole[i] else LAND)

        if mottle:
            # the parchment grain is anchored to the GLOBE, not to the
            # window: every zoom level samples the same world-fixed
            # noise, so the paper never slides underfoot
            noise_img = self._global_noise().crop(
                self._noise_box(lon0, lat0, lon1, lat1)).resize(
                (w, h), Image.BILINEAR)
            arr = np.asarray(img).astype(np.int16)
            nz = (np.asarray(noise_img).astype(np.int16) - 128) // 10
            land_px = np.all(arr == np.array(LAND, dtype=np.int16), axis=2)
            for c in range(3):
                ch = arr[:, :, c]
                ch[land_px] = np.clip(ch[land_px] + nz[land_px], 0, 255)
            img = Image.fromarray(arr.astype(np.uint8))
            draw = ImageDraw.Draw(img)

        # rivers
        for s, idx in index_shifts(self.river_bbox):
            for i in idx:
                pts = ring_pts(self.river_line(i), s)
                draw.line(pts, fill=RIVER,
                          width=int(4.5 * ss) if self.river_major[i]
                          else max(1, int(1.5 * ss)))

        if land_only:
            if ss > 1:
                img = img.resize((out_w, out_h), Image.LANCZOS)
            return img

        # borders / coastlines (reuse the fill pass transforms)
        for s, idx in poly_hits:
            for i in idx:
                pts = poly_cache.get((s, i))
                if pts:
                    draw.line(pts, fill=BORDER, width=border_w)

        def window_shifts(bb):
            out = []
            for s in (0.0, -360.0, 360.0):
                if (bb[0] + s <= lon1 and bb[2] + s >= lon0 and
                        bb[1] <= lat1 and bb[3] >= lat0):
                    out.append(s)
            return out

        # roads: snaking centre-lines between the cities they link.
        # TWO passes -- a pale verge first, then every core stroke on
        # top -- so the light border never overpaints a junction
        road_lines = []
        road_paths = getattr(self, 'road_paths', {}) if roads else {}
        for (i, j) in (self.roads if roads else ()):
            path = road_paths.get((i, j))
            if not path:
                a, b = self.cities[i], self.cities[j]
                path = [(a[2], a[3]), (b[2], b[3])]
            lons = [p[1] for p in path]
            lats = [p[0] for p in path]
            bb = (min(lons), min(lats), max(lons), max(lats))
            for s in window_shifts(bb):
                line = [((lo + s - lon0) * sx, (lat1 - la) * sy)
                        for (la, lo) in path]
                road_lines.append((line, road_w))
        for path in (getattr(self, 'spur_paths', []) if roads else []):
            lons = [p[1] for p in path]
            lats = [p[0] for p in path]
            bb = (min(lons), min(lats), max(lons), max(lats))
            for s in window_shifts(bb):
                line = [((lo + s - lon0) * sx, (lat1 - la) * sy)
                        for (la, lo) in path]
                road_lines.append((line, max(2, road_w - 1)))
        for path in (getattr(self, 'custom_road_paths', [])
                     if roads else []):
            lons = [p[1] for p in path]
            lats = [p[0] for p in path]
            bb = (min(lons), min(lats), max(lons), max(lats))
            for s in window_shifts(bb):
                line = [((lo + s - lon0) * sx, (lat1 - la) * sy)
                        for (la, lo) in path]
                road_lines.append((line, road_w))
        verge = max(2, 2 * ss)
        for line, w in road_lines:
            draw.line(line, fill=ROAD_EDGE, width=w + verge,
                      joint='curve')
        for line, w in road_lines:
            draw.line(line, fill=ROAD, width=w, joint='curve')

        # cities: aerial-sketch street plan and rooftops, drawn straight
        # onto the map; size and building count scale with population
        capitals = {(c[0], c[1]) for c in self.cities
                    if c[0] in CAPITALS}
        for (name, country, lat, lon) in self.cities:
            pop_k = CITY_POPULATION.get(name, 120)
            margin = (0.055 + 0.0028 * math.sqrt(pop_k)) * 1.5
            bb = (lon - margin, lat - margin, lon + margin, lat + margin)
            for s in window_shifts(bb):
                x = (lon + s - lon0) * sx
                y = (lat1 - lat) * sy
                self._draw_city_sketch(draw, x, y, sx, sy, name,
                                       (name, country) in capitals, pop_k)
        if ss > 1:
            img = img.resize((out_w, out_h), Image.LANCZOS)
        if mottle:
            img = self._apply_relief(img, lon0, lat0, lon1, lat1)
        return img

    def _apply_relief(self, img, lon0, lat0, lon1, lat1):
        """Hillshade, high-country stone tint and contour lines,
        applied to the FINISHED sheet at output resolution. The fields
        are pure functions of absolute position (seamless across the
        tile mosaic), and the elevation is sampled ONE PIXEL beyond
        every edge so a contour crossing the tile border is inked
        right up to it -- lines continue across tiles without a gap.
        Contours come from the GAMEPLAY elevation field, so a vision
        field's warp is predictable straight off the printed lines."""
        w, h = img.size
        pxx = (lon1 - lon0) / w
        pxy = (lat1 - lat0) / h
        shade, high, e_pad = self.terrain.shade_window(
            lon0 - pxx, lat0 - pxy, lon1 + pxx, lat1 + pxy,
            w + 2, h + 2)
        shade = shade[1:-1, 1:-1]
        high = high[1:-1, 1:-1]
        b = np.asarray(img)
        bi = b.astype(np.int16)
        land = ((np.abs(bi - np.array(OCEAN, np.int16)).sum(2) > 20)
                & (np.abs(bi - np.array(RIVER, np.int16)).sum(2) > 20))
        fa = b.astype(np.float32)
        STONE = np.array((151, 140, 120), dtype=np.float32)
        hi3 = (0.55 * high)[:, :, None]
        fa = fa * (1.0 - hi3) + STONE[None, None, :] * hi3
        fa *= shade[:, :, None]
        CONTOUR = np.array((74, 64, 50), dtype=np.float32)
        band = np.floor_divide(e_pad, 100.0).astype(np.int32)

        def _edges(bnd):
            ed = np.zeros(bnd.shape, dtype=bool)
            ed[1:, :] |= bnd[1:, :] != bnd[:-1, :]
            ed[:, 1:] |= bnd[:, 1:] != bnd[:, :-1]
            return ed[1:-1, 1:-1] & land

        edge_ix = _edges(band // 5)         # every 500 m, firmer
        edge_mn = _edges(band) & ~edge_ix   # every 100 m, faded
        fa[edge_mn] = fa[edge_mn] * 0.70 + CONTOUR[None, :] * 0.30
        fa[edge_ix] = fa[edge_ix] * 0.45 + CONTOUR[None, :] * 0.55
        np.clip(fa, 0, 255, out=fa)
        fa[~land] = b[~land]            # water keeps its exact inks
        return Image.fromarray(fa.astype(np.uint8))

    _noise_cache = None

    def _global_noise(self):
        if WorldData._noise_cache is None:
            rng = np.random.RandomState(1944)
            small = rng.rand(512, 1024)
            img = Image.fromarray((small * 255).astype(np.uint8), 'L')
            img = img.resize((4096, 2048), Image.BILINEAR)
            img = img.filter(ImageFilter.GaussianBlur(1.5))
            WorldData._noise_cache = img
        return WorldData._noise_cache

    @staticmethod
    def _noise_box(lon0, lat0, lon1, lat1):
        nw, nh = 4096, 2048
        x0 = int((lon0 + 180.0) / 360.0 * nw)
        x1 = max(x0 + 2, int((lon1 + 180.0) / 360.0 * nw))
        y0 = int((90.0 - lat1) / 180.0 * nh)
        y1 = max(y0 + 2, int((90.0 - lat0) / 180.0 * nh))
        return (max(0, x0), max(0, y0), min(nw, x1), min(nh, y1))

    # ================================================== city plans
    # Each city's aerial layout is generated ONCE, in a normalized frame
    # (distances in units of the city's nominal radius). Rendering merely
    # scales the stored plan, so the same rooftops appear at every zoom
    # level -- nothing pops or reshuffles while the camera moves.

    def _build_rails(self):
        """Each great power opens with a RAILROAD binding its three
        biggest cities: the two shortest legs of the triangle, curved
        gently (rails are surveyed straighter than roads). Trains --
        any column running a rail leg -- burn no stores."""
        from config import PLAYABLE
        popk = lambda n: CITY_POPULATION.get(n, 120)
        by_country = {}
        for (name, country, lat, lon) in self.cities:
            by_country.setdefault(country, []).append(
                (name, country, lat, lon))
        for country in PLAYABLE:
            group = sorted(by_country.get(country, []),
                           key=lambda g: -popk(g[0]))[:3]
            if len(group) < 2:
                continue
            legs = []
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    a, b = group[i], group[j]
                    d = latlon_dist_deg((a[3], a[2]), (b[3], b[2]))
                    legs.append((d, a, b))
            legs.sort(key=lambda x: x[0])
            for d, a, b in legs[:2]:
                if d > 40.0:
                    continue        # no ocean-spanning main lines
                seed = zlib.crc32(("rail:%s:%s" % (a[0], b[0])).encode())
                curve = self._curved_road_points(
                    a[2], a[3], b[2], b[3], seed, passes=2, amp=0.02)
                self.rail_paths.append(curve)

    def _build_city_plans(self):
        self.city_plans = {}
        for (name, country, lat, lon) in self.cities:
            pop_k = CITY_POPULATION.get(name, 120)
            capital = name in CAPITALS
            self.city_plans[name] = self._build_city_plan(
                name, pop_k, capital, lat, lon)

    def _build_city_plan(self, name, pop_k, capital, lat, lon):
        """The town plan: a splattered multi-lobe built-up area, a street
        web (snaking arterials + connecting cross-links) over a downtown
        grid, and densely packed non-overlapping rooftops filling the
        blocks. All coordinates normalized to the city radius. Nothing
        is built over water: arms stop at the shore, rooftops only stand
        on land, and streets are clipped at the waterline."""
        rng = np.random.RandomState(zlib.crc32(name.encode()) & 0xffffff)
        radius_deg = 0.065 + 0.0042 * math.sqrt(max(1.0, pop_k))
        coslat = max(0.15, math.cos(math.radians(lat)))

        # A local land/water gate mask rendered from the SAME vector
        # polygons (and rivers) the map displays -- the coarse movement
        # mask disagrees with the drawn coastline by enough to strand
        # buildings in the sea. Frame matches the plan mapping exactly:
        # x follows longitude, y is latitude compressed by coslat.
        gw = 512
        gx = radius_deg * 1.9
        gy = radius_deg * coslat * 1.9
        gimg = self.render_region(lon - gx, lat - gy, lon + gx, lat + gy,
                                  gw, gw, land_only=True)
        gate = np.all(np.asarray(gimg) ==
                      np.array(LAND, dtype=np.uint8), axis=2)
        # erode one pixel so nothing sits half-off the drawn coastline
        gate = (gate & np.roll(gate, 1, 0) & np.roll(gate, -1, 0)
                & np.roll(gate, 1, 1) & np.roll(gate, -1, 1))

        def on_land(x, y):
            px = int((x * radius_deg + gx) / (2 * gx) * gw)
            py = int((y * radius_deg * coslat + gy) / (2 * gy) * gw)
            if px < 0 or py < 0 or px >= gw or py >= gw:
                return False
            return bool(gate[py, px])

        # ---- branching built-up shape: a compact core with arms of
        # shrinking lobes reaching out along the growth axes ----
        core_r = 0.50
        lobes = [(0.0, 0.0, core_r)]
        arms = []                       # lobe-centre chains, per arm
        n_arms = 4 + int(min(4, pop_k / 1000.0))
        arm_len = 2 + int(min(3, pop_k / 800.0))
        base_a = float(rng.uniform(0, 2 * math.pi))
        for a in range(n_arms):
            ang = base_a + 2 * math.pi * a / n_arms + \
                float(rng.uniform(-0.5, 0.5))
            drift = float(rng.uniform(-0.7, 0.7))
            chain = [(0.0, 0.0)]
            d = 0.46
            rad = 0.34 * float(rng.uniform(0.75, 1.15))
            # unequal arms: some spike far out, some stay stubby
            n_l = max(1, arm_len - (2 if rng.rand() < 0.3 else
                                    1 if rng.rand() < 0.5 else 0))
            for _ in range(n_l):
                ang += drift * float(rng.uniform(0.4, 1.1))
                nx = chain[-1][0] + math.cos(ang) * d
                ny = chain[-1][1] + math.sin(ang) * d
                if not on_land(nx, ny):
                    break               # the town cannot grow into the sea
                lobes.append((nx, ny, rad))
                chain.append((nx, ny))
                d *= 0.85
                rad *= 0.82
            arms.append(chain)
            # a long arm may fork: a side spur off its midpoint makes
            # the web read as grown, not drawn
            if len(chain) >= 3 and rng.rand() < 0.45:
                fx, fy = chain[len(chain) // 2]
                fang = ang + float(rng.choice([-1.0, 1.0])) * \
                    float(rng.uniform(0.7, 1.3))
                fd = d * 1.1
                frad = rad * 1.1
                fork = [(fx, fy)]
                for _ in range(1 + int(rng.rand() < 0.5)):
                    fx += math.cos(fang) * fd
                    fy += math.sin(fang) * fd
                    if not on_land(fx, fy):
                        break
                    lobes.append((fx, fy, frad))
                    fork.append((fx, fy))
                    fang += float(rng.uniform(-0.4, 0.4))
                    fd *= 0.85
                    frad *= 0.82
                if len(fork) >= 2:
                    arms.append(fork)

        def depth(x, y):
            """0 at a lobe centre, 1 at the built-up fringe, >1 outside."""
            best = 9.9
            for (lx, ly, lr) in lobes:
                q = math.hypot(x - lx, y - ly) / lr
                if q < best:
                    best = q
            return best

        def inside(x, y):
            return depth(x, y) <= 1.0

        # ---- streets: an arterial spine down each arm + downtown grid,
        # cross-linked into an irregular web (no ring roads) ----
        streets = []                    # (points, width_frac)
        spines = []
        for chain in arms:
            pts = [chain[0]]
            for k in range(len(chain) - 1):
                (x1, y1), (x2, y2) = chain[k], chain[k + 1]
                if k == len(chain) - 2:     # run past the last lobe centre
                    x2, y2 = x1 + (x2 - x1) * 1.55, y1 + (y2 - y1) * 1.55
                for t in (0.34, 0.67, 1.0):
                    wob = 0.035 * float(rng.uniform(-1, 1))
                    dx, dy = x2 - x1, y2 - y1
                    nrm = math.hypot(dx, dy) or 1e-6
                    pts.append((x1 + dx * t - dy / nrm * wob,
                                y1 + dy * t + dx / nrm * wob))
            if len(pts) >= 2:       # an arm drowned at its first lobe
                streets.append((pts, 0.036))
                spines.append(pts)

        # web: irregular cross-links between neighbouring arm spines
        order = sorted(range(len(spines)),
                       key=lambda i: math.atan2(spines[i][-1][1],
                                                spines[i][-1][0]))
        for f in (0.35, 0.62, 0.88) if len(spines) >= 2 else ():
            for oi in range(len(order)):
                if rng.rand() < 0.25:            # torn web = organic
                    continue
                a = spines[order[oi]]
                b = spines[order[(oi + 1) % len(order)]]
                pa = a[max(1, int(f * (len(a) - 1)))]
                pb = b[max(1, int(f * (len(b) - 1)))]
                if not (inside(pa[0], pa[1]) and inside(pb[0], pb[1])):
                    continue
                mx = (pa[0] + pb[0]) * 0.5 + float(rng.uniform(-.04, .04))
                my = (pa[1] + pb[1]) * 0.5 + float(rng.uniform(-.04, .04))
                streets.append(([pa, (mx, my), pb], 0.022))

        # rooftops keep a roughly constant PHYSICAL size, so the building
        # count grows with the built-up area -- i.e. with population
        pitch = min(0.13, max(0.032, 0.011 / radius_deg))

        # downtown grid inside the core (block size follows the rooftops:
        # wide enough for a few rows of houses per block)
        theta = float(rng.uniform(0, math.pi / 2))
        gs = min(0.30, max(0.14, pitch * 4.2))
        for direc in (theta, theta + math.pi / 2):
            ux, uy = math.cos(direc), math.sin(direc)
            px_, py_ = -uy, ux
            k = 1
            while k * gs < core_r:
                for sgn in (-1, 1):
                    o = sgn * k * gs
                    half = math.sqrt(core_r ** 2 - o ** 2)
                    streets.append((
                        [(px_ * o - ux * half, py_ * o - uy * half),
                         (px_ * o + ux * half, py_ * o + uy * half)], 0.013))
                k += 1
            streets.append(([(-ux * core_r, -uy * core_r),
                             (ux * core_r, uy * core_r)], 0.013))

        # ---- clip every street at the waterline: walk each polyline at
        # a fine step and keep only the on-land runs ----
        clipped = []
        for pts, wf in streets:
            run = []
            for k in range(len(pts) - 1):
                (x1, y1), (x2, y2) = pts[k], pts[k + 1]
                seglen = math.hypot(x2 - x1, y2 - y1)
                steps = max(1, int(seglen / 0.05))
                for t in range(0 if k == 0 else 1, steps + 1):
                    f = t / steps
                    px_ = x1 + (x2 - x1) * f
                    py_ = y1 + (y2 - y1) * f
                    if on_land(px_, py_):
                        run.append((px_, py_))
                    else:
                        if len(run) >= 2:
                            clipped.append((run, wf))
                        run = []
            if len(run) >= 2:
                clipped.append((run, wf))
        streets = clipped

        # ---- rooftops: dense jittered plots, footprint-reserved ----
        # grid resolution follows the rooftop size so the footprint test
        # stays accurate however dense the city is
        ext = 1.75
        G = int(min(768, max(192, 2 * ext / (pitch * 0.15))))
        cell = 2 * ext / G
        occ = np.zeros((G, G), dtype=bool)
        centers = -ext + (np.arange(G) + 0.5) * cell

        def disc_mark(x, y, rad):
            """Reserve a true disc (not a square -- squares over-reserve
            street corridors by up to the cell diagonal)."""
            i0 = max(0, int((x - rad + ext) / cell))
            i1 = min(G, int((x + rad + ext) / cell) + 1)
            j0 = max(0, int((y - rad + ext) / cell))
            j1 = min(G, int((y + rad + ext) / cell) + 1)
            if i0 >= i1 or j0 >= j1:
                return
            wx = centers[i0:i1][:, None] - x
            wy = centers[j0:j1][None, :] - y
            occ[i0:i1, j0:j1] |= (wx * wx + wy * wy) <= rad * rad

        alley = 0.006
        for pts, wf in streets:
            half = wf * 0.5 + alley
            for k in range(len(pts) - 1):
                (x1, y1), (x2, y2) = pts[k], pts[k + 1]
                seglen = math.hypot(x2 - x1, y2 - y1)
                for t in range(int(seglen / cell) + 2):
                    f = min(1.0, t * cell / max(seglen, 1e-9))
                    disc_mark(x1 + (x2 - x1) * f, y1 + (y2 - y1) * f, half)
        disc_mark(0.0, 0.0, 0.085 if capital else 0.055)

        def rect_cells(bx, by, w2, h2, rot, pad):
            rr = math.hypot(w2, h2) + pad + cell
            i0 = max(0, int((bx - rr + ext) / cell))
            i1 = min(G, int((bx + rr + ext) / cell) + 1)
            j0 = max(0, int((by - rr + ext) / cell))
            j1 = min(G, int((by + rr + ext) / cell) + 1)
            if i0 >= i1 or j0 >= j1:
                return None
            wx = centers[i0:i1][:, None] - bx
            wy = centers[j0:j1][None, :] - by
            c, s = math.cos(-rot), math.sin(-rot)
            lx = wx * c - wy * s
            ly = wx * s + wy * c
            m = (np.abs(lx) <= w2 + pad) & (np.abs(ly) <= h2 + pad)
            return i0, i1, j0, j1, m

        buildings = []                  # (x, y, w2, h2, rot, shade)

        def try_place(bx, by, sz, rot, pad, squat=1.15):
            w2 = sz * float(rng.uniform(0.85, squat))
            h2 = sz * float(rng.uniform(0.85, squat))
            for shrink in (1.0, 0.68):   # retry smaller in tight blocks
                win = rect_cells(bx, by, w2 * shrink, h2 * shrink,
                                 rot, pad)
                if win is None:
                    continue
                i0, i1, j0, j1, m = win
                if (occ[i0:i1, j0:j1] & m).any():
                    continue
                w2, h2 = w2 * shrink, h2 * shrink
                w2b = rect_cells(bx, by, w2, h2, rot, 0.0)
                occ[w2b[0]:w2b[1], w2b[2]:w2b[3]] |= w2b[4]
                shade = 0 if rng.rand() < 0.55 else (1 if rng.rand() < 0.78
                                                     else 2)
                buildings.append((bx, by, w2, h2, rot, shade))
                return True
            return False

        # pass 1: the downtown core, packed TIGHT -- the plot lattice is
        # rotated to the street grid, so the terraces sit in true rows
        # between the blocks, split only by narrow alleys
        cp = pitch * 0.72
        jit = cp * 0.08
        ngc = int(core_r / cp) + 1
        ct, st = math.cos(theta), math.sin(theta)
        for gi in range(-ngc, ngc + 1):
            for gj in range(-ngc, ngc + 1):
                lx = gi * cp + float(rng.uniform(-jit, jit))
                ly = gj * cp + float(rng.uniform(-jit, jit))
                bx = lx * ct - ly * st
                by = lx * st + ly * ct
                if math.hypot(bx, by) >= core_r or rng.rand() < 0.03:
                    continue
                if not on_land(bx, by):
                    continue
                rot = theta + float(rng.uniform(-0.03, 0.03))
                try_place(bx, by, cp * 0.38 * float(rng.uniform(0.85, 1.05)),
                          rot, 0.0035, squat=1.1)

        # pass 2: arms and fringe -- density and building size FALL OFF
        # sharply toward the edge, so the town visibly thins outward
        jit = pitch * 0.16
        ng = int(ext / pitch)
        for gi in range(-ng, ng + 1):
            for gj in range(-ng, ng + 1):
                bx = gi * pitch + float(rng.uniform(-jit, jit))
                by = gj * pitch + float(rng.uniform(-jit, jit))
                if math.hypot(bx, by) < core_r:      # core already packed
                    continue
                q = depth(bx, by)
                if q > 1.0:
                    continue
                keep = 1.0 - max(0.0, q - 0.35) * 1.5
                if rng.rand() > keep:
                    continue
                if not on_land(bx, by):
                    continue
                sz = pitch * 0.40 * float(rng.uniform(0.78, 1.05))
                sz *= 1.0 - 0.35 * max(0.0, q - 0.4)
                rot = math.atan2(by, bx) + math.pi / 2 + \
                    float(rng.uniform(-0.3, 0.3))
                try_place(bx, by, sz, rot, alley)

        return {'radius_deg': radius_deg, 'coslat': coslat,
                'streets': streets, 'buildings': buildings,
                'capital': capital}

    def _draw_city_sketch(self, draw, cx, cy, sx, sy, name,
                          capital, pop_k=120):
        """Render the city's stored plan at this scale. The plan is fixed
        -- zooming only changes the transform, never the layout. Plan x
        maps to longitude and plan y to latitude COMPRESSED by the city's
        coslat, exactly the frame the plan's waterline gating used, so
        buildings and streets land where they were tested regardless of
        the render window's aspect."""
        plan = self.city_plans.get(name)
        if plan is None:
            return
        rx = plan['radius_deg'] * sx
        ry = plan['radius_deg'] * plan['coslat'] * sy
        r = rx
        if r < 2.2:
            draw.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=CITY_DOT)
            return
        street = (96, 83, 63)
        roofs = ((176, 161, 127), (156, 141, 108), (132, 117, 90))
        lw = max(1, int(r * 0.018))
        cm = max(2, int(r * 0.045))

        def T(p):
            return (cx + p[0] * rx, cy + p[1] * ry)

        if r < 12:
            # too small for rooftops: main arterials + dot
            for pts, wf in plan['streets']:
                if wf >= 0.03:
                    draw.line([T(p) for p in pts], fill=street,
                              width=lw, joint='curve')
            draw.ellipse([cx - cm, cy - cm, cx + cm, cy + cm],
                         fill=(88, 74, 55))
            return

        for (bx, by, w2, h2, rot, shade) in plan['buildings']:
            c, s = math.cos(rot), math.sin(rot)
            corners = [(cx + (bx + ux * c - uy * s) * rx,
                        cy + (by + ux * s + uy * c) * ry)
                       for (ux, uy) in ((-w2, -h2), (w2, -h2),
                                        (w2, h2), (-w2, h2))]
            draw.polygon(corners, fill=roofs[shade],
                         outline=street if w2 * r > 2.2 else None)

        for pts, wf in plan['streets']:
            draw.line([T(p) for p in pts], fill=street,
                      width=max(1, int(wf * r)), joint='curve')

        draw.ellipse([cx - cm, cy - cm, cx + cm, cy + cm], fill=(88, 74, 55))
        if plan['capital']:
            draw.ellipse([cx - cm * 1.9, cy - cm * 1.9,
                          cx + cm * 1.9, cy + cm * 1.9],
                         outline=(70, 58, 42), width=lw)
