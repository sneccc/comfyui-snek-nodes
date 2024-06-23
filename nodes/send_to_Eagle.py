import json
import os

import folder_paths as comfy_paths
import numpy as np
import requests
import torch
from PIL import Image
from PIL.PngImagePlugin import PngInfo


class EagleAPI:
    def __init__(self, base_url="http://localhost:41595", token=None):
        self.base_url = base_url
        self.session = requests.Session()  # Create a Session object

        self.headers = {"Content-Type": "application/json"}
        if token:
            # self.base_url = f"{base_url}/?token={token}"
            self.headers["Authorization"] = "Bearer " + token

    def add_item_from_path(self, data, folder_id=None):
        if folder_id:
            data["folderId"] = folder_id
        return self._send_request("/api/item/addFromPath", method="POST", data=data)

    def get_id_from_folder_name(self, folder_name, parent_id=None):
        folders_json = self._send_request("/api/folder/list", method="GET")
        return self._find_folder_id(folders_json["data"], folder_name, parent_id)

    def _find_folder_id(self, folders, folder_name, parent_id, current_parent_id=None):
        for folder in folders:
            if folder['name'] == folder_name and (parent_id is None or parent_id == current_parent_id):
                return folder['id']
            if 'children' in folder:
                found_id = self._find_folder_id(folder['children'], folder_name, parent_id, folder['id'])
                if found_id:
                    return found_id
        return None

    def add_items_from_paths(self, data):
        return self._send_request("/api/item/addFromPaths", method="POST", data=data)

    def create_new_folder(self, folder_name, ID_parent=None):
        # parent ID of the parent folder
        data = {"folderName": folder_name}

        if ID_parent:
            data["parent"] = ID_parent

        return self._send_request("/api/folder/create", method="POST", data=data)

    # Private method for sending requests
    def _send_request(self, endpoint, method="GET", data=None):
        url = self.base_url + endpoint

        if method == "GET":
            response = self.session.get(url, headers=self.headers)
        elif method == "POST":
            response = self.session.post(url, headers=self.headers, json=data)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        response.raise_for_status()
        return response.json()


class Send_to_Eagle:
    def __init__(self):
        self.output_dir = comfy_paths.output_directory

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
#                "token": ("STRING", {"default": "Your token here"}),
                "folder_name": ("STRING", {"default": "Folder Name on Eagle"}),
                "description": ("STRING", {"default": "Your description here"}),
                # "overwrite": ("BOOLEAN", {"default": True})  # New overwrite toggle
            },
            "hidden": {
                "prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"
            },
        }

    RETURN_TYPES = ("STRING", "STRING",)
    RETURN_NAMES = ("api_log","folder_id")
    FUNCTION = "main"
    CATEGORY = "🐍 Snek Nodes"

    # Function to create and get folder ID
    def get_or_create_folder(self, parent_folder, subfolder_name):
        folder_id = self.eagle_api.get_id_from_folder_name(subfolder_name)
        if folder_id is None:
            # Create new folder and extract its ID from the response
            response = self.eagle_api.create_new_folder(subfolder_name, ID_parent=parent_folder)

            folder_id = response.get('data', {}).get('id')
        return folder_id

    def main(self, images: torch.Tensor, folder_name, description, prompt=None, extra_pnginfo=None):
        self.eagle_api = EagleAPI()
        output_file = os.path.abspath(os.path.join(self.output_dir, "temp.png"))
        log = []
        for image in images:
            i = 255. * image.cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))

            metadata = PngInfo()
            if prompt is not None:
                metadata.add_text("prompt", json.dumps(prompt))
            if extra_pnginfo is not None:
                for x in extra_pnginfo:
                    metadata.add_text(x, json.dumps(extra_pnginfo[x]))
            exif_data = metadata

            img.save(output_file, optimize=False, pnginfo=exif_data)

            folder_id = self.get_or_create_folder(None, folder_name)

            item = {
                "path": output_file,
                "name": "Comfy",
                "annotation": description,
                "tags": None
            }
            response = self.eagle_api.add_item_from_path(data=item, folder_id=folder_id)
            log.append(f"Status: {response['status']}, Data: {response['data']}")

        log_str = "\n".join(log)
        return (log_str, response['data'],)


NODE_CLASS_MAPPINGS = {

    "Send_to_Eagle": Send_to_Eagle,

}
