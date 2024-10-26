
import folder_paths
import os
import safetensors

class Load_ai_toolkit_latent_flux:
    @classmethod
    def INPUT_TYPES(s):
        input_dir = folder_paths.get_input_directory()
        files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f)) and f.endswith(".safetensors")]
        return {"required": {"latent_file": [sorted(files), ]}, }
    CATEGORY = "🐍 Snek Nodes"
    RETURN_TYPES = ("LATENT",)
    FUNCTION = "load"

    def load(self, latent_file):
        latent_path = folder_paths.get_annotated_filepath(latent_file)
        try:
            with safetensors.safe_open(latent_path, framework="pt", device="cpu") as f:
                latent = f.get_tensor('latent')
            
            # Ensure the latent is a 4D tensor (batch, channels, height, width)
            if latent.dim() == 3:
                latent = latent.unsqueeze(0)
            
            # Convert to the expected format for LATENT output
            latent_dict = {"samples": latent}
            
            return (latent_dict,)
        except Exception as e:
            print(f"Error loading latent from {latent_path}: {str(e)}")
            return (None,)
NODE_CLASS_MAPPINGS = {
    "Load AI Toolkit Latent Flux": Load_ai_toolkit_latent_flux,
}
