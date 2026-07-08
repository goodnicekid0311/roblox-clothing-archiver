![](https://files.catbox.moe/jzpr11.jpg)
# Important!!!
### You must create a file named 'auth.txt' in the python directory, and put your .ROBLOSECURITY cookie in it!!! (Or specify the location of your cookie file with --auth FILE !!)
**This is because roblox requires you to have an account in order to use some of their APIs**

Tutorial here >>> https://www.youtube.com/watch?v=S3y1GTPMNBE

# Roblox Clothing Archiver
Simple python command line tool to archive clothing templates from groups/users before Roblox nukes 2D clothing.

**Requires 'requests' package**
```
pip install requests
```

Tested on Python 3.14, on Ubuntu 26.04

Works reliably with default settings, I've downloaded >5000 clothes without getting rate limited

Report bugs/issues if you can please!  
Contact @gvrlslvt on Discord for any help

## How to Use
On Windows, you can click the "run.bat" if you dont know how to use a command line. Otherwise,
```
$ python3 roarchive.py 6139847 --auth ../auth.txt
getting group info for 6139847
got group page 1 for 6139847
got xml for 4972758662
Saved 4972758662
...
```

```yaml
usage: roarchive.py [-h] [-s] [-a FILE] [-p FOLDER] [-dp FOLDER] [-m {0,1}] [-nm {1,2}] [-pd PAGEDELAY] [-d DELAY] [--norun] id

Roblox Clothing Archiver

positional arguments:
  id                    ID of the group/user to download from (or asset if using -s)

options:
  -h, --help            show this help message and exit
  -s, --single          download a single asset with 'id' instead of a group/user
  -a, --auth FILE       custom path for auth/roblosecurity file
  -p, --path FOLDER     overwrite group output folder path (overwrites --downloadpath)
  -dp, --downloadpath FOLDER
                        overwrite default downloads folder path
  -m, --metadata {0,1}  enable/disable saving metadata
  -nm, --namemethod {1,2}
                        method used for naming group folder
                          1: only name
                          2: use name and id
  -pd, --pagedelay PAGEDELAY
                        delay in seconds between group clothing page queries
  -d, --delay DELAY     delay in seconds between clothing texture downloads
  --norun               (debug) dont make any network requests
```
# Why
Made in response to several decisions by roblox attempting to phase out 2D clothing, #SaveRoblox

![](https://files.catbox.moe/i9qolv.png)
