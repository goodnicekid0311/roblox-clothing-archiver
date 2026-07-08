import requests
import xml.etree.ElementTree as ET
import re
import json
import time
import argparse
import os
import sys

GET_CATALOG_URL = "https://catalog.roblox.com/v1/search/items/details?Category=3&CreatorType={}&IncludeNotForSale=true&Limit=30&CreatorTargetId="
GROUP_CREATOR_TYPE = 2
USER_CREATOR_TYPE = 1
GROUP_INFO_URL = "https://groups.roblox.com/v1/groups/"
USER_INFO_URL = "https://users.roblox.com/v1/users/"
URL_CURSOR = "&cursor="
JSON_CURSOR = "nextPageCursor"
ASSET_GET_URL = "https://economy.roblox.com/v2/assets/{}/details"
ROPROXY_URL = "https://assetdelivery.roproxy.com/v1/asset?id=" # gets texture id
PNG_URL = "https://assetdelivery.roblox.com/v1/asset/?id=" # returns png
XML_ELEMENT_PATH = "./Item/Properties/Content/url"
ROBLOSECURITY_PREFIX = ".ROBLOSECURITY="

windows_names = {'CON', 'PRN', 'AUX', 'NUL'} | {f'COM{i}' for i in range(1, 10)} | {f'LPT{i}' for i in range(1, 10)}

def safename(name):
    safe_name = re.sub(r'[^\w\s.-]', '_', name)
    safe_name = safe_name.strip(' ')
    name_root, *ext = safe_name.split('.', 1)
    if name_root.upper() in windows_names:
        safe_name = f"_{safe_name}"
    return safe_name[:255]

def validate_request(req, callback, errorMsg):
    match req.status_code:
        case 200 | 201:
            if callback:
                callback()
            return True
        case _:
            print(errorMsg)
    return False

def fastreq(url, suffix):
    return requests.get(
        url+str(suffix),
        headers={
            "Cookie": auth
        }
    )

def get_shirt_xml(shirt_id):
    xml_get = fastreq(ROPROXY_URL, shirt_id)

    def callback():
        print("got xml for "+str(shirt_id))

    valid = validate_request(
        xml_get,
        callback,
        "error getting xml for "+str(shirt_id))
    
    if valid:
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
            res = fastreq(PNG_URL, tex_id)

            def callback():
                with open(filepath+".png", "wb") as file:
                    file.write(res.content)
                    print("Saved "+str(shirt_id))

            return validate_request(res, callback, "error saving shirt")
    else:
        return False

def group_query(id, delay, creator_type, pages=None, cursor=None):
    if not pages:
        pages = []

    if cursor:
        res = fastreq(GET_CATALOG_URL.format(creator_type)+id+URL_CURSOR, cursor)
    else:
        res = fastreq(GET_CATALOG_URL.format(creator_type), id)

    def callback():
        print("got group page "+str(len(pages)+1)+" for "+id)
        group_data = json.loads(res.text)

        if "data" in group_data:
            pages.append(group_data["data"])

        if JSON_CURSOR in group_data:
            if group_data[JSON_CURSOR] is not None:
                time.sleep(delay)
                group_query(id, delay, creator_type, pages, group_data[JSON_CURSOR])

    validate_request(res, callback, "error getting group page "+str(id))

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
    parser.add_argument("-pd", "--pagedelay", type=float, default=0.55,
                        help="delay in seconds between group clothing page queries")
    parser.add_argument("-d", "--delay", type=float, default=0.55,
                    help="delay in seconds between clothing texture downloads")
    parser.add_argument("--norun", action="store_true",
                help="(debug) dont make any network requests")
    args = parser.parse_args()

    # Validate and create file paths before making requests

    validate_path(args.auth, True)

    with open(args.auth, "r") as file:
        global auth
        auth = file.read()
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
        group_info_req = fastreq(GROUP_INFO_URL, args.id)

        json_data = None

        def json_callback(text):
            global json_data, output_folder
            json_data = json.loads(text)
            
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

        def callback():
            json_callback(group_info_req.text)

        valid = validate_request(group_info_req, callback, "couldnt get group info for "+args.id)

        is_user = False

        if not valid:
            print("trying to get user info for "+args.id)
            user_info_req = fastreq(USER_INFO_URL, args.id)

            def callback():
                json_callback(user_info_req.text)

            valid = validate_request(user_info_req, callback, "couldnt get user info for "+args.id)
            if valid:
                is_user = True

        if not json_data:
            print("!!! couldnt get any info for "+args.id+", exiting !!!")
            sys.exit(0)

        pages = group_query(args.id, args.pagedelay, USER_CREATOR_TYPE if is_user else GROUP_CREATOR_TYPE)
        
        if args.metadata == 1:
            with open(os.path.join(output_folder, "info.json"), "w") as file:
                json.dump(json_data, file, indent=2)
            with open(os.path.join(output_folder, "info_clothing.json"), "w") as file:
                json.dump(pages, file, indent=2)

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
        req = fastreq(ASSET_GET_URL.format(args.id), "")
        valid = validate_request(req, None, "couldnt get asset details for "+args.id)

        itemname = args.id

        if valid:
            json_data = json.loads(req.text)
            itemname = json_data["Name"]+"_"+args.id

            if args.metadata == 1:
                with open(os.path.join(output_folder, "info_"+args.id+".json"), "w") as file:
                    json.dump(json_data, file, indent=2)

        filename = safename(itemname)
        filepath = os.path.join(output_folder, filename)
        save_shirt(args.id, filepath)

    print("Finished!!!")
