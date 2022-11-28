import datetime
import re
import requests
import sys
from bs4 import BeautifulSoup
import os
from PIL import Image, ImageDraw

from collections import namedtuple
from math import sqrt
import numpy as np
import random

Point = namedtuple('Point', ('coords', 'n', 'ct'))
Cluster = namedtuple('Cluster', ('points', 'center', 'n'))

def get_points(img):
    points = []
    w, h = img.size
    for count, color in img.getcolors(w * h):
        points.append(Point(color, 3, count))
    return points

rtoh = lambda rgb: '#%s' % ''.join(('%02x' % p for p in rgb))

def colorz(filename, n=3):
    img = Image.open(filename)
    img.thumbnail((200, 200))
    w, h = img.size

    points = get_points(img)
    clusters = kmeans(points, n, 1)
    rgbs = [tuple(list(map(int, c.center.coords))) for c in clusters]
    return sorted(rgbs, key=lambda rgb: np.mean(rgb))

def euclidean(p1, p2):
    return sqrt(sum([
        (p1.coords[i] - p2.coords[i]) ** 2 for i in range(p1.n)
    ]))

def calculate_center(points, n):
    vals = [0.0 for i in range(n)]
    plen = 0
    for p in points:
        plen += p.ct
        for i in range(n):
            vals[i] += (p.coords[i] * p.ct)
    return Point([(v / plen) for v in vals], n, 1)

def kmeans(points, k, min_diff):
    clusters = [Cluster([p], p, p.n) for p in random.sample(points, k)]

    while 1:
        plists = [[] for i in range(k)]

        for p in points:
            smallest_distance = float('Inf')
            for i in range(k):
                distance = euclidean(p, clusters[i].center)
                if distance < smallest_distance:
                    smallest_distance = distance
                    idx = i
            plists[idx].append(p)

        diff = 0
        for i in range(k):
            old = clusters[i]
            center = calculate_center(plists[i], old.n)
            new = Cluster(plists[i], center, old.n)
            clusters[i] = new
            diff = max(diff, euclidean(old.center, new.center))

        if diff < min_diff:
            break

    return clusters

def download_day(day='221117', folder='data'):
    if day == 'today':
        day = datetime.datetime.now().strftime('%y%m%d')
    if day == 'random':
        current_year = datetime.datetime.now().year
        current_month = datetime.datetime.now().month
        current_day = datetime.datetime.now().day
        found = False
        
        year = random.randint(2013, current_year) # 2011
        month = random.randint(1 if year != 2011 else 4, 12 if year != current_year else current_month)
        days_in_month = 31 if month in [1, 3, 5, 7, 8, 10, 12] else 30 if month != 2 else 29 if year % 4 == 0 else 28
        day = random.randint(1 if year != 2011 or month != 4 else 20, 
             days_in_month if year != current_year or month != current_month else current_day)
        day = f'{year-2000:02d}{month:02d}{day:02d}'

    print(day)
    site = f'https://miniature-calendar.com/{day}'
    response = requests.get(site)
    soup = BeautifulSoup(response.text, 'html.parser')
    image_tags = soup.find_all('img')
    urls = [img['src'] for img in image_tags]
    # only full-size calendar images
    urls = [u for u in urls if u.endswith('.jpg') and not '250x250.jpg' in u]
    foldurls = []
    for url in urls:
        filename = re.search(r'/([\w_-]+[.](jpg|gif|png))$', url)
        if not filename:
            print("Regular expression didn't match with the url: {}".format(url), file=sys.stderr)
            continue
        
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
        if os.path.exists(os.path.join(folder, filename.group(1))):
            print("File {} already exists".format(filename.group(1)))
            foldurls.append(os.path.abspath(os.path.join(folder, filename.group(1))))
            continue
        with open(os.path.join(folder, filename.group(1)), 'wb') as f:
            if 'http' not in url:
                url = '{}{}'.format(site, url)
            response = requests.get(url)
            f.write(response.content)
            foldurls.append(os.path.abspath(os.path.join(folder, filename.group(1))))
    print("Download complete!", file=sys.stderr)
    return foldurls

def compile_image(path, framewidth=10, reso=(2560, 1440), crop=0, inv_cols=False):
    # load image
    img = Image.open(path)
    # crop image
    if img.size[1] > 1080:
        crop += img.size[1] - 1080
    img = img.crop((crop//2, crop//2, img.size[0]-crop//2, img.size[1]-crop//2))
    base_img = Image.new('RGB', reso, (255, 255, 255))
    # paste image at 740, 180
    colors = colorz(path, 2)
    if inv_cols:
        colors = colors[::-1]
    # draw color boxes
    draw = ImageDraw.Draw(base_img)
    w, h = base_img.size
    draw.rectangle([0, 0, w, h], fill=tuple(colors[1]))
    st_x = (w - img.size[0] - framewidth*2) // 2
    st_y = (h - img.size[1] - framewidth*2) // 2
    draw.rectangle([st_x, st_y, st_x+img.size[0] + framewidth*2, st_y+img.size[0] + framewidth*2], fill=tuple(colors[0]))
    base_img.paste(img, (st_x + framewidth, st_y + framewidth))
    # save image
    base_img.save('compiled_{}.png'.format(path.split('/')[-1]))
    return os.path.abspath('compiled_{}.png'.format(path.split('/')[-1]))

def setwall(path):
    # if mac
    if sys.platform == 'darwin':
        setwall = 'osascript -e \'tell application "Finder" to set desktop picture to POSIX file "{}"\''
    # if linux
    elif sys.platform.startswith('linux'):
        # if gnome
        if os.environ.get('XDG_CURRENT_DESKTOP') == 'GNOME' or os.environ.get('GNOME_DESKTOP_SESSION_ID'):
            setwall = f'gsettings set org.gnome.desktop.background picture-uri "file://{path}"'
            setwall += f';gsettings set org.gnome.desktop.background picture-uri-dark "file://{path}"'
            setwall += f';gsettings set org.gnome.desktop.background picture-options "zoom"'
        # if kde
        elif os.environ.get('XDG_CURRENT_DESKTOP') == 'KDE':
            setwall = 'qdbus org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript \'var Desktops = desktops(); for (i=0;i<Desktops.length;i++) {{ d = Desktops[i]; d.wallpaperPlugin = "org.kde.image"; d.currentConfigGroup = Array("Wallpaper", "org.kde.image", "General"); d.writeConfig("Image", "file://{}") }}\''.format(path)
        # if xfce
        elif os.environ.get('DESKTOP_SESSION') == 'xfce':
            setwall = 'xfconf-query -c xfce4-desktop -p /backdrop/screen0/monitor0/image-path -s {}'.format(path)
        # if mate
        elif os.environ.get('DESKTOP_SESSION') == 'mate':
            setwall = 'gsettings set org.mate.background picture-filename {}'.format(path)
        else:
            raise Exception(f'Unsupported desktop environment {os.environ.get("DESKTOP_SESSION")}')
    elif sys.platform == 'win32':
        setwall = 'reg add "HKEY_CURRENT_USER\Control Panel\Desktop" /v Wallpaper /t REG_SZ /d "{}" /f'.format(path)
    else:
        raise Exception(f'Unsupported platform {sys.platform}')
    os.system(setwall)


fu = download_day(day='180626')
chosen_fu = fu[0]#random.choice(fu)
img = compile_image(chosen_fu, reso=(1920, 1080), crop=100, inv_cols=False)
setwall(img)