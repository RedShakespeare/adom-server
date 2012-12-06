import irclib
import signal
import sys
import time
from pyinotify import WatchManager, ThreadedNotifier, ProcessEvent, IN_CLOSE_WRITE
import os
from tweepy import OAuthHandler, API, TweepError, debug
from configobj import ConfigObj
import re
import random

#irclib.DEBUG = True

MIN_IRC_ANC = 200
MIN_TWIT_ANC = 8000

FILE111 = "/var/lib/adom/public_html/adom_hiscore/hiscore_v111.txt"
FILE100 = "/var/lib/adom/public_html/adom_hiscore/hiscore_v100.txt"
FILEETR = "/var/lib/adom/public_html/adom_hiscore/hiscore_vetr.txt"

LOCDIR = "/var/lib/adom/tmp/player_locations"

config = ConfigObj('/var/lib/adom/etc/config')

CONSUMER_KEY = config.get("CONSUMER_KEY")
CONSUMER_SECRET = config.get("CONSUMER_SECRET")
ACCESS_KEY = config.get("ACCESS_KEY")
ACCESS_SECRET = config.get("ACCESS_SECRET")

#try to set up twitter
try:
    auth = OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(ACCESS_KEY, ACCESS_SECRET)
    api = API(auth)
except TweepError as e:
    print "Error: could not set up OAuth. {0}".format(e)

def signal_handler(signal, frame):
    print "Received signal {0}".format(signal)
    notifier.stop()
    notifierloc.stop()
    s.quit("Augh!")
    sys.exit(1)

signal.signal(signal.SIGTERM, signal_handler) 
signal.signal(signal.SIGINT, signal_handler)

def tweet(version, text):
    m = re.match('(.*?)\. (L\d{0,1}.*?) \((M|F)\)\. \d+ xps\. \d+ turns?\. (.*?)\. (Rank: #\d{0,3}), score (\d+)',text)

    raceclass = m.group(2)
    score = int(m.group(6))
    if score <= MIN_TWIT_ANC:
        return

    mapping = [ ('drakish ', 'Dr'), ('dwarven ','Dw'), ('dark elven ', 'De'), ('gray elven ', 'Ge'), ('high elven ', 'He'), ('gnomish ','Gn'), ('human ','Hm'), ('hurthling ', 'Hr'), ('orcish ','Or'), ('trollish ','Tr'), ('archer','Ar'), ('assassin','As'), ('barbarian','Bb'), ('bard','Br'), ('beastfighter','Bf'), ('druid','Dr'), ('elementalist','El'), ('farmer','Fa'), ('fighter','Fi'), ('healer','He'), ('merchant','Me'), ('mindcrafter','Mi'), ('monk','Mo'), ('necromancer','Ne'), ('paladin','Pa'), ('priest','Pr'), ('ranger','Ra'), ('thief','Th'), ('weaponsmith','We'), ('wizard','Wz') ]

    for k, v in mapping:
        raceclass = raceclass.replace(k, v)

    reason =  m.group(4)

    if " while saving h" in reason:
        reason = reason[0:reason.find(" while saving h")]
    elif " without even stopping to save h" in reason:
        reason = reason[0:reason.find(" without even stopping to save h")]

    if "He was " in reason:
        reason = reason[7:]
    elif "She was " in reason:
        reason = reason[8:]
    elif "He " in reason:
        reason = reason[2:]
    elif "She " in reason:
        reason = reason[3:]


    newtext = "#ADOM {0} score: {1}, {2}, {3}. {4}".format(version, m.group(1), raceclass, reason, m.group(5))
    if newtext.__len__() > 140:
        makeup = newtext.__len__() - 140
        rdiff = reason.__len__() - makeup - 2
        if rdiff < 1:
            return
        reason = reason[0:rdiff] + ".."

    newtext = "#ADOM {0} score: {1}, {2}, {3}. {4}".format(version, m.group(1), raceclass, reason, m.group(5))
    print newtext
    try:
        api.update_status(newtext)
    except TweepError as e:
        print "Error sending tweet. {0}".format(e)



def poll_hiscore():
    global hiscore_100
    global hiscore_111
    global hiscore_etr

    new_100 = import_hiscore(FILE100)
    new_111 = import_hiscore(FILE111)
    new_etr = import_hiscore(FILEETR)

    diff_100 = set(new_100.keys()).difference(hiscore_100.keys())
    diff_111 = set(new_111.keys()).difference(hiscore_111.keys())
    diff_etr = set(new_etr.keys()).difference(hiscore_etr.keys())

    hiscore_100 = new_100
    hiscore_111 = new_111
    hiscore_etr = new_etr

    if c.is_connected() == True:
        for key in diff_100:
            print hiscore_100[key] + " Version 1.0.0."
            c.privmsg(target, "\x02New high score\x02: " + hiscore_100[key] + " Version 1.0.0.")
            tweet("1.0.0", hiscore_100[key]);
            
        for key in diff_111:
            print hiscore_111[key] + " Version 1.1.1."
            c.privmsg(target, "\x02New high score\x02: " + hiscore_111[key] + " Version 1.1.1.")
            tweet("1.1.1", hiscore_111[key]);

        for key in diff_etr:
            print hiscore_etr[key] + " Played The Eternium Man challenge."
            c.privmsg(target, "\x02New high score\x02: " + hiscore_etr[key] + " Played The Eternium Man challenge.")

def loc_changed(filename):
   player = filename.split("/")[-1]

   if not player:
      return
   
   location = ""
   with open(filename) as f:
      location = f.readlines()[0].strip()

   starters = [ "Attention! ", "Caution! ", "Alert! ", "Breaking news! ", "Newsflash! ", "Look! ", "Citizens! ", "", "", "", ]
   enders = [ "Spectate today!", "Spectate now!", "Care to watch?", "This could be good....", "", "", "", ]
   c.privmsg(target,random.choice(starters) + player + " has just entered the " + location + "! " + random.choice(enders))

def import_hiscore(file):
    f = open(file, "r")
    lines = f.readlines()

    if (len(lines) <= 0):
	return {}

    for i in range(4):
        lines.pop(0)

    hiscore = {}
    hiscore_line = lines.pop(0)

    for line in lines:
        if "Died on " in line:
            line = line[0:line.find("Died on ")]
            
        elif "Won on " in line:
            line = line[0:line.find("Won on ")]

        elif "Ascended on " in line:
            line = line[0:line.find("Ascended on ")]

        if "(M)" in line or "(F)" in line:
            key = " ".join((hiscore_line.split())[1:])
            parsed = " ".join((hiscore_line.split())[2:])
            parsed += " Rank: #" + hiscore_line.split()[0].strip() + ", score " + hiscore_line.split()[1].strip() + "."

            if int(hiscore_line.split()[1].strip()) >= MIN_IRC_ANC:
                hiscore[key] = parsed

            hiscore_line = line
            
        else:
            hiscore_line += line

    key= " ".join((hiscore_line.split())[1:])
    parsed = " ".join((hiscore_line.split())[2:])
    parsed += " Rank: #" + hiscore_line.split()[0].strip() + ", score " + hiscore_line.split()[1].strip() + "."

    if int(hiscore_line.split()[1].strip()) >= MIN_IRC_ANC:
        hiscore[key] = parsed

    return hiscore

def on_connect(connection, event):
    connection.join(target)

if len(sys.argv) < 4:
    print "Usage: adombot <server[:port]> <nickname> <target> [realname] [ssl]"
    sys.exit(1)

def on_disconnect(connection, event):
    time.sleep(60)
    connection.connect(server, port, nickname, ircname=ircname, ssl=dossl)

s = sys.argv[1].split(":", 1)
server = s[0]
if len(s) == 2:
    try:
        port = int(s[1])
    except ValueError:
        print "Error: Erroneous port."
        sys.exit(1)
else:
    port = 6667
nickname = sys.argv[2]
target = sys.argv[3]

if len(sys.argv) >= 5:
        ircname = sys.argv[4]
else:
        ircname = nickname

if len(sys.argv) >= 6:
        dossl = bool(sys.argv[5])
else:
        dossl = False

if (dossl != False) and (dossl != True):
        print "Invalid value for SSL: must be True or False"
        exit(1) 

hiscore_111 = import_hiscore(FILE111)
hiscore_100 = import_hiscore(FILE100)
hiscore_etr = import_hiscore(FILEETR)

print "Connecting announce bot...\n"
irc = irclib.IRC()
try:
    s = irc.server();
    c = s.connect(server, port, nickname, ircname=ircname, ssl=dossl)
except irclib.ServerConnectionError, x:
    print x
    sys.exit(1)

c.add_global_handler("welcome", on_connect)
c.add_global_handler("disconnect", on_disconnect)

wm = WatchManager()
wmloc = WatchManager()

class ScoreHandler(ProcessEvent):
    def process_IN_CLOSE_WRITE(self, evt):
        poll_hiscore()

class LocHandler(ProcessEvent):
    def process_IN_CLOSE_WRITE(self, evt):
        loc_changed(evt.pathname)

handler = ScoreHandler()
handlerloc = LocHandler()

notifier = ThreadedNotifier(wm, handler)
notifierloc = ThreadedNotifier(wmloc, handlerloc)

wm.add_watch(FILE100, IN_CLOSE_WRITE)
wm.add_watch(FILE111, IN_CLOSE_WRITE)
wm.add_watch(FILEETR, IN_CLOSE_WRITE)

wmloc.add_watch(LOCDIR, IN_CLOSE_WRITE)

notifier.start()
notifierloc.start()

irc.process_forever()
