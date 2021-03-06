import sys
import passwd
import os

print "Enter the file you desire to play in the format username - ttyrec name"
print "(EXACTLY as is shown by the listing options):"

raw_ttyrec = raw_input("> ");

os.environ["PATH"] += os.pathsep + "/usr/local/bin"

player = "termplay"

if len(raw_ttyrec.split(" - ")) != 2:
    print "Invalid input!"
    sys.exit(1)

username = raw_ttyrec.split(" - ")[0]
ttyrecname = raw_ttyrec.split(" - ")[1]

passwddir = passwd.loadpw()

if username not in passwddir:
    print "Username not found!"
    sys.exit(1)

ttyrecdir = passwddir[username].home + "/ttyrecs"
found = False;

for root, dirs, files in os.walk(ttyrecdir):
    if root != ttyrecdir:
        continue
    
    for file in files:
        if file == ttyrecname:
            found = True
            break

    if found:
        break
    
if not found:
    print "TTY recording not found!"
    sys.exit(1)

os.system("termplay " + ttyrecdir + "/" + ttyrecname)
