import requests
import os
from zipfile import ZipFile
from urllib.parse import urlparse

class DownGitService:
    def __init__(self):
        self.repo_info = {}

    def parse_info(self, parameters):
        repo_path = urlparse(parameters['url']).path
        split_path = repo_path.split("/")
        info = {}

        info['author'] = split_path[1]
        info['repository'] = split_path[2]
        
        if len(split_path) > 4:
            info['branch'] = split_path[4]
        else:
            info['branch'] = "master"

        info['root_name'] = split_path[-1]
        if len(split_path) > 4:
            info['res_path'] = repo_path[repo_path.index(split_path[4]) + len(split_path[4]) + 1:]
        else:
            info['res_path'] = ""

        info['url_prefix'] = f"https://api.github.com/repos/{info['author']}/{info['repository']}/contents/"
        info['url_postfix'] = f"?ref={info['branch']}"

        info['download_file_name'] = info['branch']  # Use the name of the branch or directory

        if parameters['rootDirectory'] == "false":
            info['root_directory_name'] = ""
        elif not parameters['rootDirectory'] or parameters['rootDirectory'] == "" or parameters['rootDirectory'] == "true":
            info['root_directory_name'] = info['root_name'] + "/"
        else:
            info['root_directory_name'] = parameters['rootDirectory'] + "/"

        return info

    def download_dir(self, progress):
        progress['isProcessing']['val'] = True

        dir_paths = []
        files = []
        requested_promises = []

        dir_paths.append(self.repo_info['res_path'])
        self.map_file_and_directory(dir_paths, files, requested_promises, progress)

    def map_file_and_directory(self, dir_paths, files, requested_promises, progress):
        response = requests.get(self.repo_info['url_prefix'] + dir_paths.pop() + self.repo_info['url_postfix']).json()
        for item in response:
            if item['type'] == "dir":
                dir_paths.append(item['path'])
            else:
                if 'download_url' in item:
                    self.get_file(item['path'], item['download_url'], files, requested_promises, progress)
                else:
                    print(item)

        if not dir_paths:
            self.download_files(files, requested_promises, progress)
        else:
            self.map_file_and_directory(dir_paths, files, requested_promises, progress)

    def download_files(self, files, requested_promises, progress):
        zip_file_path = f"{self.repo_info['download_file_name']}.zip"
        with ZipFile(zip_file_path, 'w') as zf:
            for file in files:
                zf.writestr(
                    self.repo_info['root_directory_name'] + file['path'][len(self.repo_info['res_path']) + 1:],
                    file['data']
                )

        progress['isProcessing']['val'] = False

    def get_file(self, path, url, files, requested_promises, progress):
        response = requests.get(url)
        if response.status_code == 200:
            files.append({'path': path, 'data': response.content})
            progress['downloadedFiles']['val'] = len(files)

        requested_promises.append(response)
        progress['totalFiles']['val'] = len(requested_promises)

    def download_zipped_files(self, parameters, progress):
        self.repo_info = self.parse_info(parameters)

        if not self.repo_info['res_path']:
            download_url = f"https://github.com/{self.repo_info['author']}/{self.repo_info['repository']}/archive/{self.repo_info['branch']}.zip"
            response = requests.get(download_url)
            with open(f"{self.repo_info['branch']}.zip", "wb") as f:
                f.write(response.content)
        else:
            response = requests.get(self.repo_info['url_prefix'] + self.repo_info['res_path'] + self.repo_info['url_postfix'])
            if isinstance(response.json(), list):
                self.download_dir(progress)
            else:
                self.download_file(response.json()['download_url'], progress)

if __name__ == "__main__":
    user_url = input("Enter the GitHub repository URL: ")
    parameters = {
        'url': user_url,
        'fileName': "",  # Leave this empty
        'rootDirectory': "true"
    }

    progress = {
        'isProcessing': {'val': False},
        'downloadedFiles': {'val': 0},
        'totalFiles': {'val': 0}
    }

    service = DownGitService()
    service.download_zipped_files(parameters, progress)

