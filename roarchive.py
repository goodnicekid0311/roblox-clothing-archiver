import requests
import xml.etree.ElementTree as ET
import re
import json
import time
import argparse
import os
import sys

GET_CATALOG_URL = "https://catalog.roblox.com/v1/search/items/details?Category=3&CreatorType={}&Subcategory={}&IncludeNotForSale=true&Limit=30&SortType=3&CreatorTargetId="
GROUP_CREATOR_TYPE = 2
USER_CREATOR_TYPE = 1
SHIRT_SUBCATEGORY = 56
PANTS_SUBCATEGORY = 57
SUBCATEGORY_ENUM = {
    SHIRT_SUBCATEGORY: "shirts",
    PANTS_SUBCATEGORY: "pants"
}

GROUP_INFO_URL = "https://groups.roblox.com/v1/groups/"
USER_INFO_URL = "https://users.roblox.com/v1/users/"
URL_CURSOR = "&cursor="
JSON_CURSOR = "nextPageCursor"
ASSET_GET_URL = "https://economy.roblox.com/v2/assets/{}/details"
ROPROXY_URL = "https://assetdelivery.roproxy.com/v1/asset?id=" # gets texture id
PNG_URL = "https://assetdelivery.roblox.com/v1/asset/?id=" # returns png
XML_ELEMENT_PATH = "./Item/Properties/Content/url"
ROBLOSECURITY_PREFIX = ".ROBLOSECURITY="
ROBLOSECURITY_VALID_PREFIX = "_|WARNING:-DO-NOT-SHARE-THIS"
windows_names = {'CON', 'PRN', 'AUX', 'NUL'} | {f'COM{i}' for i in range(1, 10)} | {f'LPT{i}' for i in range(1, 10)}

verbose = False

def safename(name):
    safe_name = re.sub(r'[^\w\s.-]', '_', name)
    safe_name = safe_name.strip(' ')
    name_root, *ext = safe_name.split('.', 1)
    if name_root.upper() in windows_names:
        safe_name = f"_{safe_name}"
    return safe_name[:255]

def fastreq(url, callback, errorMsg, delay=None):
    if delay:
        if delay > 64:
            print("request timed out waiting for rate limit")
            return False
        time.sleep(delay)

    req = requests.get(
        url,
        headers={
            "Cookie": auth
        }
    )

    match req.status_code:
        case 200 | 201:
            if callback:
                callback(req)
            return req
        case 429:
            s = delay * 2 if delay else 1
            print("getting rate limited, waiting {}s".format(s))
            return fastreq(url, callback, errorMsg, s)
        case _:
            print(errorMsg)
            if verbose:
                print(req.status_code)
                print(req.text)
            return False

def get_shirt_xml(shirt_id):
    def callback(req):
        print("got xml for "+str(shirt_id))

    xml_get = fastreq(
        ROPROXY_URL+str(shirt_id),
        callback,
        "error getting xml for "+str(shirt_id))
    
    if xml_get:
        return ET.fromstring(xml_get.text)

def save_shirt(shirt_id, filepath):
    """it append .png to filepath"""

    shirt_xml = get_shirt_xml(shirt_id)

    if shirt_xml is not None:
        url = shirt_xml.find(XML_ELEMENT_PATH)
        if url is not None:
            text = url.text
            # strip it for numbers
            tex_id = "".join([char for char in text if char.isdigit()])

            def callback(req):
                with open(filepath+".png", "wb") as file:
                    file.write(req.content)
                    print("Saved "+str(shirt_id))

            return fastreq(PNG_URL+str(tex_id), callback, "error saving shirt")
    else:
        return False

def group_query(id, delay, creator_type, pages=None, cursor=None, subcategory=None):
    if not pages:
        pages = []

    if not subcategory:
        subcategory = SHIRT_SUBCATEGORY

    if cursor:
        url = GET_CATALOG_URL.format(creator_type, subcategory)+id+URL_CURSOR+cursor
    else:
        url = GET_CATALOG_URL.format(creator_type, subcategory)+id

    def callback(req):
        print("got group page "+str(len(pages)+1)+" for "+id+" for "+SUBCATEGORY_ENUM[subcategory])
        group_data = json.loads(req.text)

        if "data" in group_data:
            pages.append(group_data["data"])

        if JSON_CURSOR in group_data:
            time.sleep(delay)
            if group_data[JSON_CURSOR] is not None:
                group_query(id, delay, creator_type, pages, group_data[JSON_CURSOR], subcategory)
            elif subcategory == SHIRT_SUBCATEGORY:
                # switch to checking pants
                group_query(id, delay, creator_type, pages, subcategory=PANTS_SUBCATEGORY)

    fastreq(url, callback, "error getting group page "+str(id))

    return pages

def validate_path(path, isFile=None):
    if not os.path.exists(path):
        if isFile:
            if args.auth == "./auth.txt":
                print("You must create a file named 'auth.txt' in this directory, and put your .ROBLOSECURITY cookie in it!!! (Or specify the location of your cookie file with --auth FILE !!)")
            else:
                print("File not found: "+path)
            sys.exit(0)
        else:
            os.makedirs(path, exist_ok=True)

    return path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Roblox Clothing Archiver",
        formatter_class=argparse.RawTextHelpFormatter)
    
    # TODO: add error csv as input
    # TODO: detect if group thing exists and then add option to skip already downloaded
    parser.add_argument("id", type=str, help="ID of the group/user to download from (or asset if using -s)")
    parser.add_argument("-s", "--single", action="store_true",
                        help="download a single asset with 'id' instead of a group/user")
    parser.add_argument("-a", "--auth", metavar="FILE", default="./auth.txt",
                        help="custom path for auth/roblosecurity file")
    parser.add_argument("-p", "--path", metavar="FOLDER",
                        help="overwrite group output folder path (overwrites --downloadpath)")
    parser.add_argument("-dp", "--downloadpath", default="./downloads", metavar="FOLDER",
                        help="overwrite default downloads folder path")
    parser.add_argument("-m", "--metadata", type=int, choices=[0, 1], default=1,
                        help="enable/disable saving metadata")
    parser.add_argument("-nm", "--namemethod", type=int, choices=[1, 2], default=1,
                        help="method used for naming group folder\n  1: only name\n 2: use name and id")
    parser.add_argument("-pd", "--pagedelay", type=float, default=0.75,
                        help="delay in seconds between group clothing page queries")
    parser.add_argument("-d", "--delay", type=float, default=0.55,
                    help="delay in seconds between clothing texture downloads")
    parser.add_argument("--norun", action="store_true",
                help="(debug) dont make any network requests")
    parser.add_argument("--nodownload", action="store_true",
                help="(debug) dont download any clothes")
    parser.add_argument("--verbose", action="store_true",
                help="(debug) print more")
    args = parser.parse_args()

    verbose = args.verbose

    # Validate and create file paths before making requests

    validate_path(args.auth, True)

    with open(args.auth, "r") as file:
        global auth
        auth = file.read()

        if not ROBLOSECURITY_VALID_PREFIX in auth:
            print("!! Auth format may be invalid !!")

        if not auth.startswith(ROBLOSECURITY_PREFIX):
            auth = ROBLOSECURITY_PREFIX+auth

    if args.path:
        output_folder = validate_path(args.path)
    else:
        # id is used as fallback if name req doesnt work
        if args.single:
            output_folder = validate_path(args.downloadpath)
        else:
            output_folder = validate_path(os.path.join(args.downloadpath, args.id))

    # Now make requests
    if args.norun:
        sys.exit(0)

    if not args.single:
        print("getting group info for "+args.id)

        json_data = None

        def callback(req):
            global json_data, output_folder
            json_data = json.loads(req.text)
            
            if not args.path:
                group_name = safename(json_data["name"])

                match args.namemethod:
                    case 1:
                        folder_name = group_name
                    case 2:
                        folder_name = group_name+args.id

                new_dest = os.path.join(os.path.dirname(output_folder), folder_name)

                # fix error if folder name already exists (from a previous run)
                if not os.path.exists(new_dest):
                    os.rename(output_folder, new_dest)
                else:
                    os.rmdir(output_folder)
                output_folder = new_dest

        valid = fastreq(GROUP_INFO_URL+args.id, callback, "couldnt get group info for "+args.id)

        is_user = False

        if not valid:
            print("trying to get user info for "+args.id)

            valid = fastreq(USER_INFO_URL+args.id, callback, "couldnt get user info for "+args.id)
            if valid:
                is_user = True

        if not json_data:
            print("!!! couldnt get any info for "+args.id+", exiting !!!")
            sys.exit(0)

        pages = group_query(args.id, args.pagedelay, USER_CREATOR_TYPE if is_user else GROUP_CREATOR_TYPE)
        ct = 0
        for page in pages:
            ct += len(page)
        print("got "+str(ct)+" clothes")

        if args.metadata == 1:
            with open(os.path.join(output_folder, "info.json"), "w") as file:
                json.dump(json_data, file, indent=2)
            with open(os.path.join(output_folder, "info_clothing.json"), "w") as file:
                json.dump(pages, file, indent=2)

        if args.nodownload:
            sys.exit(0)

        errors = []
        for page in pages:
            for item in page:
                item_id = item["id"]
                filename = safename(item["name"]+"_"+str(item_id))

                filepath = os.path.join(output_folder, filename)

                success = save_shirt(item_id, filepath)
                if not success:
                    print("error archiving "+str(item_id))
                    errors.append(item_id)

                time.sleep(args.delay)

        num_errors = len(errors)
        if num_errors > 0:
            error_file = os.path.join(output_folder, "errors_{}_{}.csv".format(args.id, str(time.time())[-4:]))

            with open(error_file, "w") as file:
                file.write(",".join(str(e) for e in errors))

            print("there were {} errors saving assets. failed IDs saved to {}".format(num_errors, error_file))
    else:
        req = fastreq(ASSET_GET_URL.format(args.id), None, "couldnt get asset details for "+args.id)

        itemname = args.id

        if req:
            json_data = json.loads(req.text)
            itemname = json_data["Name"]+"_"+args.id

            if args.metadata == 1:
                with open(os.path.join(output_folder, "info_"+args.id+".json"), "w") as file:
                    json.dump(json_data, file, indent=2)

        filename = safename(itemname)
        filepath = os.path.join(output_folder, filename)
        save_shirt(args.id, filepath)

    print("Finished!!!")
