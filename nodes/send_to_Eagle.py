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
        self.eagle_api = EagleAPI()
        self.output_dir = comfy_paths.output_directory

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "folder_name": ("STRING", {"default": "Folder Name on Eagle"}),
                "description": ("STRING", {"default": "Your description here"}),
                "tags": ("STRING", {"default": ""})  # New field for tags
            },
            "hidden": {
                "prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"
            },
        }

    RETURN_TYPES = ("STRING", "STRING",)
    RETURN_NAMES = ("api_log", "folder_id")
    FUNCTION = "main"
    CATEGORY = "🐍 Snek Nodes"

    def get_or_create_folder(self, parent_folder, subfolder_name):
        folder_id = self.eagle_api.get_id_from_folder_name(subfolder_name)
        if folder_id is None:
            response = self.eagle_api.create_new_folder(subfolder_name, ID_parent=parent_folder)
            folder_id = response.get('data', {}).get('id')
        return folder_id

    def main(self, images: torch.Tensor, folder_name: str, description: str, tags: str = None, prompt: dict = None, extra_pnginfo: dict = None):
        log = []
        folder_id = self.get_or_create_folder(None, folder_name)

        # Split the tags string into an array if tags exist
        tags_array = tags.split(",") if tags else None

        for idx, image in enumerate(images):
            try:
                img_array = (255. * image.cpu().numpy()).astype(np.uint8)
                img = Image.fromarray(np.clip(img_array, 0, 255))

                metadata = PngInfo()
                if prompt:
                    metadata.add_text("prompt", json.dumps(prompt))
                if extra_pnginfo:
                    for key, value in extra_pnginfo.items():
                        metadata.add_text(key, json.dumps(value))

                output_file = os.path.abspath(os.path.join(self.output_dir, f"temp_{idx}.png"))
                img.save(output_file, optimize=False, pnginfo=metadata)

                item = {
                    "path": output_file,
                    "name": f"Comfy_{idx}",
                    "annotation": description,
                    "tags": tags_array  # Include the tags array
                }
                response = self.eagle_api.add_item_from_path(data=item, folder_id=folder_id)
                log.append(f"Status: {response['status']}, Data: {response['data']}")
            except Exception as e:
                log.append(f"Failed to process image {idx}: {str(e)}")

        log_str = "\n".join(log)
        return log_str, response['data']


NODE_CLASS_MAPPINGS = {

    "Send_to_Eagle": Send_to_Eagle,

}
