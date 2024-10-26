import clip
import numpy as np
import torch
from PIL import Image


# Tensor to PIL
def tensor2pil(image):
    return Image.fromarray(np.clip(255. * image.cpu().numpy().squeeze(), 0, 255).astype(np.uint8))


# PIL to Tensor
def pil2tensor(image):
    return torch.from_numpy(np.array(image).astype(np.float32) / 255.0).unsqueeze(0)


# https://github.com/tgxs002/align_sd?tab=readme-ov-file
class aesthetics:
    def __init__(self):
        pass

    def load(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model, self.preprocess = clip.load("ViT-L/14", device=self.device)
        self.params = torch.load(r"P:\python\notebooks\Eagle_Scripts\align_sd\hpc.pt")['state_dict']
        self.model.load_state_dict(self.params)

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image": ("IMAGE",),
                "text": ("STRING", {"multiline": True, "dynamicPrompts": False}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("best",)
    FUNCTION = "main"
    CATEGORY = "🐍 Snek Nodes"

    # OUTPUT_IS_LIST = (True, )

    def main(self, image, text):
        self.load()
        print("input", image)
        # print("image",image.shape)#batch of 2 torch.Size([2, 703, 539, 3])
        images = []
        batch = []
        for img in image:
            batch.append(tensor2pil(img))
            images.append(self.preprocess(tensor2pil(img)).unsqueeze(0).to(self.device))

        img = torch.cat(images, dim=0)
        text = clip.tokenize([text]).to(self.device)

        with torch.no_grad():
            image_features = self.model.encode_image(img)
            text_features = self.model.encode_text(text)
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)
            hps = image_features @ text_features.T
        _, best_index = torch.max(hps, dim=0)

        # tensor_images = [pil2tensor(image) for image in batch] #LIST
        tensor_images = image[int(best_index.item())].unsqueeze(0)

        print(tensor_images.shape)

        # print("best index ",best_index.item(),type(tensor_images[0]))

        print("run")
        return (tensor_images,)


from ..install import do_install

try:
    import hpsv2
    import turtle
except:
    print("### ComfyUI-snek: Reinstall dependencies (several dependencies are missing.)")
    do_install()
import hpsv2


# https://github.com/tgxs002/HPSv2/tree/master
class aesthetics_v2:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image": ("IMAGE",),
                "text": ("STRING", {"multiline": True, "dynamicPrompts": False}),
            }
        }

    RETURN_TYPES = ("IMAGE", "FLOAT")
    RETURN_NAMES = ("best", "best_score")
    FUNCTION = "main"
    CATEGORY = "🐍 Snek Nodes"
    # OUTPUT_IS_LIST = (True, )

    def main(self, image, text):
        #print("input", image)

        batch = []
        for img in image:
            batch.append(tensor2pil(img))

        result = hpsv2.score(batch, text, hps_version="v2.1")
        result_tensor = torch.tensor(result)
        _, best_index = torch.max(result_tensor, dim=0)

        # tensor_images = [pil2tensor(image) for image in batch] #LIST
        tensor_images = image[int(best_index.item())].unsqueeze(0)

        print("run")
        return (tensor_images, result_tensor[int(best_index.item())])


NODE_CLASS_MAPPINGS = {

    "Aesthetics": aesthetics,
    "Aesthetics V2": aesthetics_v2,
}
