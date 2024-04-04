import os
import subprocess
import sys

current_file_directory = os.path.dirname(os.path.abspath(__file__))

import folder_paths

comfy_path = os.path.dirname(folder_paths.__file__)
sys.path.append(comfy_path)


# Function to check if running in an embedded Python environment
def is_embedded_python():
    return "embedded" in sys.executable.lower()

# Determine the appropriate pip command based on the environment
def get_pip_install_command():
    if is_embedded_python():
        # Adjust these paths as necessary for your specific environment
        target_directory = os.path.join(os.path.dirname(sys.executable), 'Lib', 'site-packages')
        return [sys.executable, '-m', 'pip', 'install', '--target', target_directory]
    else:
        return [sys.executable, '-m', 'pip', 'install']

# Function to clone and install a package from a git repository
def do_install():
    print("Installing")
    repo_url = "https://github.com/tgxs002/HPSv2.git"
    repo_name = repo_url.split('/')[-1].rstrip('.git')
    
    # Check if the repository directory already exists
    if not os.path.exists(repo_name):
        # Clone the Git repository if it doesn't exist
        clone_command = f"git clone {repo_url}"
        subprocess.run(clone_command, check=True, shell=True)
        
        # Change directory to the cloned repository
        os.chdir(repo_name)

        replace_string_in_files(repo_name, "from clint.textui import progress")
        path=os.path.join(current_file_directory,repo_name)
        replace_string_in_files(path,"'clint'")
        replace_string_in_files(path,"from turtle import forward")
        
        # Install the package in editable mode using the appropriate pip command
        pip_install_command = get_pip_install_command()
        install_command = pip_install_command + ["-e", "."]

        subprocess.run(install_command, check=True)

    else:
        print(f"The directory '{repo_name}' already exists. Skipping clone.")

def replace_string_in_files(root_dir, target_string, replacement_string=" ", file_extension='.py'):
    """
    Replace a specific string with another string in all files with a given extension 
    within a directory and its subdirectories.

    Parameters:
    - root_dir (str): The root directory to search for files.
    - target_string (str): The string to be replaced.
    - replacement_string (str): The string to replace with. Defaults to a single space.
    - file_extension (str): The file extension to filter files by. Defaults to '.py'.
    """
    for root, dirs, files in os.walk(root_dir):
        for file_name in files:
            if file_name.endswith(file_extension):
                file_path = os.path.join(root, file_name)
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                
                # Replace the target string with the replacement string
                modified_content = content.replace(target_string, replacement_string)
                
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(modified_content)

    print(f"Completed replacing '{target_string}' with '{replacement_string}' in files under '{root_dir}'.")


