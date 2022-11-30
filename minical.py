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
from argparse import ArgumentParser

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
    if img.size[1] > reso[1]:
        crop += img.size[1] - reso[1]
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

def setwall(path, multi=False):
    # if mac
    if sys.platform == 'darwin':
        if multi:
            raise NotImplementedError('Multi-monitor not implemented for mac')
# tell application "System Events"
#     set desktopCount to count of desktops
#     repeat with desktopNumber from 1 to desktopCount
#         tell desktop desktopNumber
#             set picture to "/Library/Desktop Pictures/Beach.jpg"
#         end tell
#     end repeat
# end tell
        else:    
            setwall = 'osascript -e \'tell application "Finder" to set desktop picture to POSIX file "{}"\''.format(path)
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


if __name__ == '__main__':
    curpath = os.path.dirname(os.path.realpath(__file__))
    parser = ArgumentParser(description='Download and set wallpaper from miniature-calendar.com')
    parser.add_argument('-d', '--date', type=str, help='Date in YYMMDD format', default=None)
    parser.add_argument('-t', '--today', action='store_true', help='Set today\'s wallpaper', default=False)
    parser.add_argument('-rnd', '--random', action='store_true' ,help='Set random wallpaper', default=False)
    parser.add_argument('-f', '--folder', type=str, help='Folder to save images', default=os.join(curpath, 'data'))
    parser.add_argument('-res', '--resolution', type=str, help='Resolution of the wallpaper', default='1920x1080')
    parser.add_argument('-c', '--crop', type=int, help='Crop the image by this amount', default=100)
    parser.add_argument('-i', '--invert', action='store_true', help='Invert the colors')
    parser.add_argument('-fw', '--framewidth', type=int, help='Width of the frame', default=10)
    parser.add_argument('-m', '--multiscreen', action='store_true', help='Set wallpaper for all screens', default=False)
    parser.add_argument('-sf', '--set-first', action='store_true', help='Set the first of today, else random', default=False)
    args = parser.parse_args()

    # exactly one of date, today, random can be set
    if sum([args.date is not None, args.today, args.random]) != 1:
        raise Exception('Exactly one of date, today, random must be set')
    # assert resolution is valid
    if not re.match(r'\d+x\d+', args.resolution):
        raise Exception('Resolution must be in the format WxH')
    
    day = args.date if args.date is not None else 'today' if args.today else 'random'
    fu = download_day(day=day, folder=args.folder)
    if args.set_first:
        chosen_fu = fu[0]
    else:
        chosen_fu = random.choice(fu)
    reso = tuple([int(x) for x in args.resolution.split('x')])
    img = compile_image(chosen_fu, reso=reso, crop=args.crop, inv_cols=args.invert, framewidth=args.framewidth)
    setwall(img)
