import json
import os
import base64
import io
import re
import time

import folder_paths as comfy_paths
import numpy as np
import requests
import torch
from PIL import Image
from PIL.PngImagePlugin import PngInfo


class EagleAPI:
    def __init__(self, base_url="http://localhost:41595", token=None):
        # Remove any existing token from base_url
        if "?token=" in base_url:
            parts = base_url.split("?token=")
            self.base_url = parts[0]
            self.token = parts[1]
        elif "&token=" in base_url:
            parts = base_url.split("&token=")
            self.base_url = parts[0]
            self.token = parts[1]
        else:
            self.base_url = base_url
            self.token = token

        # Headers based on Eagle API documentation
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "ComfyUI-Eagle-Node",
            # Remove CORS headers as they should be handled by the server
            # and might cause issues
        }
        self.session = requests.Session()
        self.session.timeout = (30, 60)  # Longer timeout for remote connections

    def add_item_from_path(self, data, folder_id=None):
        if folder_id:
            data["folderId"] = folder_id
        return self._send_request("/api/item/addFromPath", method="POST", data=data)
    
    def add_item_from_base64(self, name, base64_data, folder_id=None, annotation=None, tags=None):
        """Add an item to Eagle directly using base64 encoded image data."""
        data = {
            "base64": base64_data,
            "name": name,
            "ext": "png"
        }
        
        if folder_id:
            data["folderId"] = folder_id
        if annotation:
            data["annotation"] = annotation
        if tags:
            data["tags"] = tags
            
        return self._send_request("/api/item/addFromBase64", method="POST", data=data)

    def add_item_from_url(self, url, name=None, folder_id=None, annotation=None, tags=None):
        """Add an item to Eagle directly from a URL."""
        data = {
            "url": url
        }
        
        if name:
            data["name"] = name
        if folder_id:
            data["folderId"] = folder_id
        if annotation:
            data["annotation"] = annotation
        if tags:
            data["tags"] = tags
            
        return self._send_request("/api/item/addFromURL", method="POST", data=data)

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
        # Add token to URL as per documentation
        url = self.base_url + endpoint
        token_separator = "&" if "?" in url else "?"
        url = f"{url}{token_separator}token={self.token}"
        
        print(f"\nDebug: Making {method} request to Eagle API")
        print(f"URL: {url}")
        print(f"Headers: {json.dumps(self.headers, indent=2)}")
        if data:
            print(f"Data: {json.dumps(data, indent=2)}")
        
        try:
            if method == "GET":
                response = self.session.get(url, headers=self.headers, verify=False)
            elif method == "POST":
                response = self.session.post(url, headers=self.headers, json=data, verify=False)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            # Print response for debugging
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {dict(response.headers)}")
            print(f"Response content: {response.text[:500]}...")  # First 500 chars

            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"\nRequest failed with error: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Error response: {e.response.text}")
            raise


class TextTokens:
    def __init__(self):
        self.pattern = r'\[time\((.*?)\)\]'
        
    def parseTokens(self, text):
        def replace_time(match):
            time_format = match.group(1)
            try:
                return time.strftime(time_format)
            except Exception as e:
                print(f"Error parsing time format: {str(e)}")
                return match.group(0)
        
        if text is None:
            return ""
            
        # Replace time patterns
        text = re.sub(self.pattern, replace_time, text)
        return text


class Send_to_Eagle:
    def __init__(self):
        self.output_dir = comfy_paths.output_directory

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "folder_name": ("STRING", {"default": "Folder Name on Eagle"}),
                "description": ("STRING", {"default": "Your description here"}),
                "tags": ("STRING", {"default": ""}),
                "eagle_api_url": ("STRING", {"default": "http://localhost:41595"}),
                "eagle_token": ("STRING", {"default": ""})
            },
            "optional": {
                "images": ("IMAGE",),
                "image_url": ("STRING", {"default": ""}),
                "use_direct_upload": ("BOOLEAN", {"default": True})
            },
            "hidden": {
                "prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"
            },
        }

    RETURN_TYPES = ("STRING", "STRING",)
    RETURN_NAMES = ("api_log", "folder_id")
    FUNCTION = "main"
    CATEGORY = "🐍 Snek Nodes"

    def get_or_create_folder(self, parent_folder, subfolder_name, eagle_api_url, eagle_token):
        eagle_api = EagleAPI(base_url=eagle_api_url, token=eagle_token)
        
        try:
            folder_id = eagle_api.get_id_from_folder_name(subfolder_name)
            if folder_id is None:
                response = eagle_api.create_new_folder(subfolder_name, ID_parent=parent_folder)
                folder_id = response.get('data', {}).get('id')
            return folder_id, eagle_api
        except Exception as e:
            raise Exception(f"Error connecting to Eagle API at {eagle_api_url}: {str(e)}")

    def main(self, folder_name: str, description: str, eagle_api_url: str, eagle_token: str,
             images: torch.Tensor = None, image_url: str = "", 
             use_direct_upload: bool = True, tags: str = None, 
             prompt: dict = None, extra_pnginfo: dict = None):
        log = []
        
        try:
            log.append(f"Connecting to Eagle API at: {eagle_api_url}")
            print(f"\nAttempting to connect to Eagle API at: {eagle_api_url}")
            print(f"Using token: {eagle_token[:8]}...{eagle_token[-8:] if eagle_token else 'None'}")
            
            folder_id, eagle_api = self.get_or_create_folder(None, folder_name, eagle_api_url, eagle_token)
            log.append(f"Successfully connected to Eagle API")
            log.append(f"Found/created folder with ID: {folder_id}")

            tags_array = tags.split(",") if tags and tags.strip() else None
            
            # Process URL if provided
            if image_url and image_url.strip():
                log.append(f"Original image path/URL: {image_url}")
                try:
                    # Convert local ComfyUI path to proper URL if needed
                    if image_url.startswith(('data/', '/', '.')) or ':\\' in image_url:
                        print(f"\nConverting local path to URL: {image_url}")
                        # Extract filename from path
                        filename = os.path.basename(image_url)
                        # Get subfolder if exists (everything after output/ and before filename)
                        path_parts = image_url.split('output/')
                        subfolder = path_parts[1].replace(filename, '').strip('/') if len(path_parts) > 1 else ''
                        
                        # Construct proper localhost URL
                        image_url = f"http://127.0.0.1:8188/view?filename={filename}&subfolder={subfolder}&type=output"
                        print(f"Converted to URL: {image_url}")
                    
                    log.append(f"Attempting to send to Eagle with URL: {image_url}")
                    print(f"\nPreparing to send image to Eagle")
                    
                    data = {
                        "url": image_url,
                        "name": "Comfy_URL",
                        "folderId": folder_id,
                        "annotation": description,
                    }
                    if tags_array:
                        data["tags"] = tags_array
                        
                    log.append(f"Sending data to Eagle: {json.dumps(data, indent=2)}")
                    print(f"Sending data: {json.dumps(data, indent=2)}")
                    
                    response = eagle_api.add_item_from_url(**data)
                    log.append(f"Image added to Eagle. Status: {response['status']}")
                except Exception as e:
                    error_msg = f"Failed to add image: {str(e)}"
                    print(f"\nERROR: {error_msg}")
                    log.append(error_msg)
                    raise  # Re-raise to stop processing
            
            # Process tensor images if provided
            if images is not None:
                for idx, image in enumerate(images):
                    try:
                        log.append(f"Processing image {idx+1}/{len(images)}")
                        img_array = (255. * image.cpu().numpy()).astype(np.uint8)
                        img = Image.fromarray(np.clip(img_array, 0, 255))

                        metadata = PngInfo()
                        if prompt:
                            metadata.add_text("prompt", json.dumps(prompt))
                        if extra_pnginfo:
                            for key, value in extra_pnginfo.items():
                                metadata.add_text(key, json.dumps(value))

                        # Save to temp file and use path method
                        output_file = os.path.abspath(os.path.join(self.output_dir, f"temp_{idx}.png"))
                        img.save(output_file, optimize=False, pnginfo=metadata)
                        log.append(f"Saved temp image to: {output_file}")

                        item = {
                            "path": output_file,
                            "name": f"Comfy_{idx}",
                            "annotation": description,
                            "tags": tags_array
                        }
                        
                        log.append(f"Sending image path to Eagle...")
                        response = eagle_api.add_item_from_path(data=item, folder_id=folder_id)
                        log.append(f"Image path sent. Status: {response['status']}")
                        
                    except Exception as e:
                        log.append(f"Failed to process image {idx}: {str(e)}")
            
            if not image_url and images is None:
                log.append("Warning: No images or URLs provided to send to Eagle")

            log_str = "\n".join(log)
            return log_str, folder_id
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            log.append(error_msg)
            log_str = "\n".join(log)
            return log_str, ""


class Save_Image_And_Caption:
    def __init__(self):
        self.output_dir = comfy_paths.output_directory
        self.type = "output"
        self.prefix_append = ""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "caption": ("STRING", {"default": ""}),
                "output_path": ("STRING", {"default": "[time(%Y-%m-%d)]", "multiline": False}),
                "filename_prefix": ("STRING", {"default": "ComfyUI"}),
                "filename_delimiter": ("STRING", {"default": "_"}),
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
        }

    RETURN_TYPES = ("STRING", "STRING",)
    RETURN_NAMES = ("file_path", "folder_path",)
    FUNCTION = "save_with_caption"
    CATEGORY = "🐍 Snek Nodes"

    def save_with_caption(self, images, caption, output_path="[time(%Y-%m-%d)]", filename_prefix="ComfyUI", 
                         filename_delimiter="_", prompt=None, extra_pnginfo=None):
        try:
            # Parse tokens for dynamic paths
            tokens = TextTokens()
            output_path = tokens.parseTokens(output_path)
            filename_prefix = tokens.parseTokens(filename_prefix)
            
            # Setup output path
            if output_path in [None, '', "none", "."]:
                full_output_folder = self.output_dir
            else:
                if not os.path.isabs(output_path):
                    full_output_folder = os.path.join(self.output_dir, output_path)
                else:
                    full_output_folder = output_path
                    
            # Create output directory if it doesn't exist
            if not os.path.exists(full_output_folder):
                print(f"Creating directory: {full_output_folder}")
                os.makedirs(full_output_folder, exist_ok=True)
            
            # Find existing counter values for the prefix in this directory
            pattern = f"{re.escape(filename_prefix)}{re.escape(filename_delimiter)}(\\d+)"
            existing_counters = [
                int(re.search(pattern, filename).group(1))
                for filename in os.listdir(full_output_folder)
                if os.path.isfile(os.path.join(full_output_folder, filename)) 
                and re.match(pattern, filename)
            ]
            
            # Set initial counter value
            counter = max(existing_counters, default=0) + 1
            
            # Store the path of the first image to return
            first_image_path = ""
            
            # Process all images in the batch
            for idx, image in enumerate(images):
                img_array = (255. * image.cpu().numpy()).astype(np.uint8)
                img = Image.fromarray(np.clip(img_array, 0, 255).astype(np.uint8))
                
                # Create filenames with counter
                base_filename = f"{filename_prefix}{filename_delimiter}{counter:05}"
                image_filename = base_filename + ".png"
                caption_filename = base_filename + ".txt"
                
                # Full paths
                image_path = os.path.join(full_output_folder, image_filename)
                caption_path = os.path.join(full_output_folder, caption_filename)

                # Save first image path to return
                if idx == 0:
                    first_image_path = image_path

                # Save image with metadata
                metadata = PngInfo()
                if prompt is not None:
                    metadata.add_text("prompt", json.dumps(prompt))
                if extra_pnginfo is not None:
                    for x in extra_pnginfo:
                        metadata.add_text(x, json.dumps(extra_pnginfo[x]))
                metadata.add_text("caption", caption)

                # Save image
                img.save(image_path, pnginfo=metadata, optimize=False)

                # Save caption
                with open(caption_path, 'w', encoding='utf-8') as f:
                    f.write(caption)

                print(f"Saved image {idx+1}/{len(images)} to: {image_path}")
                print(f"Saved caption {idx+1}/{len(images)} to: {caption_path}")
                
                # Increment counter for next image
                counter += 1

            return (first_image_path, full_output_folder)

        except Exception as e:
            print(f"Error saving image and caption: {str(e)}")
            return ("", "")


NODE_CLASS_MAPPINGS = {
    "Send_to_Eagle": Send_to_Eagle,
    "Save_Image_And_Caption": Save_Image_And_Caption,
}