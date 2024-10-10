import urllib.request
import uuid, os, shutil, json
import zipfile

class PackageManager:
    def __init__(self, window, packagesDir) -> None:
        self.window = window
        self.packagesDir = packagesDir
        self.tempDir = os.getenv("TEMP")

    def tempname(self, n):
        return "vt-" + str(uuid.uuid4())[:n+1] + "-install"
    
    def install(self, url, site="github"):
        tempDirName = self.tempname(8)
        path = os.path.join(self.tempDir or os.path.dirname(__file__), tempDirName)
        os.makedirs(path)

        filePath = os.path.join(path, "package.zip")
        if site == "github":
            urllib.request.urlretrieve(url + "/zipball/master", filePath)
        else:
            urllib.request.urlretrieve(url, filePath)

        with zipfile.ZipFile(filePath, 'r') as f:
            f.extractall(path)
        os.remove(filePath)

        extracted_dir = next(
            os.path.join(path, d) for d in os.listdir(path) 
            if os.path.isdir(os.path.join(path, d))
        )

        finalPackageDir = os.path.join(self.packagesDir, url.split("/")[-1])
        if not os.path.exists(self.packagesDir):
            os.makedirs(self.packagesDir)
        
        shutil.move(extracted_dir, finalPackageDir)
        shutil.rmtree(path)

        self.checkReqs(finalPackageDir)

    def checkReqs(self, d):
        req_file = os.path.join(d, "requirement.vt-plugins")
        print(req_file)
        if os.path.isfile(req_file):
            with open(req_file, "r+") as f:
                data = json.load(f)
                for url in data:
                    print(url)
                    if not os.path.isdir(os.path.join(self.packagesDir, url.split("/")[-1])):
                        self.install(url)

    def uninstall(self, name):
        if os.path.isdir(os.path.join(self.packagesDir, name)):
            shutil.rmtree(os.path.join(self.packagesDir, name))

    def search(self, name):
        return os.path.join(self.packagesDir, name) if os.path.isdir(os.path.join(self.packagesDir, name))

p = PackageManager("", "temp")
p.install("https://github.com/cherry220-v/PythonIDE")
