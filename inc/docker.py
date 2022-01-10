import os
import logging
from ebbs import Builder


# Class name is what is used at cli, so we defy convention here in favor of ease-of-use.
class docker(Builder):
    def __init__(self, name="Docker"):
        super().__init__(name)

        self.supportedProjectTypes.append("img")
        self.supportedProjectTypes.append("srv")

        #We use the rootPath, not the buildPath.
        self.clearBuildPath = False

        self.supportedImageOperatingSystems = [
            "debian",
            "alpine"
        ]
        
        
    # Required Builder method. See that class for details.
    def Build(self):
        os.chdir(self.rootPath) # docker must be built from root.
        self.imageName = f"{self.projectName}"
        
        self.shouldLogin = False
        if (len(self.repo) and "username" in self.repo and "password" in self.repo):
            self.shouldLogin = True

        if ("name" in self.config):
            self.imageName = self.config["name"]
        elif (len(self.repo) and "username" in self.repo):
            self.imageName = f"{self.repo['username']}/{self.projectName}"
        
        if ("install" in self.config and "os" not in self.config):
            raise OtherBuildError(f'You must specify "os" in config.json if you wish to install packages')

        if ("os" in self.config and self.config["os"] not in self.supportedImageOperatingSystems):
            raise OtherBuildError(f'"os" {self.config["os"]} is not supported at this time. Please use one of {self.supportedImageOperatingSystems}')


        if (self.shouldLogin):
            self.LoginToDockerhub()

        self.WriteDockerfile()
        self.BuildDockerImage()
        
        if (self.shouldLogin):
            self.PushDockerImage()


    def LoginToDockerhub(self):
        self.RunCommand(f"docker login -u=\"{self.repo['username']}\" -p=\"{self.repo['password']}\"")

    def BuildDockerImage(self):
        self.RunCommand(f"docker build -t {self.imageName} .")

    def PushDockerImage(self):
        self.RunCommand(f"docker push {self.imageName}")

    def CopyToImage(self, externalPath, imagePath):
        #This nonsense is required because we need `cp incPath/* buildpath/` behavior instead of `cp incPath buildpath/`
        #TODO: is there a better way?
        for thing in os.listdir(externalPath):
            thingPath = os.path.relpath(os.path.join(externalPath, thing))
            thingName = os.path.basename(thing)
            if os.path.isfile(thingPath):
                self.dockerfile.write(f"COPY {thingPath} {imagePath}\n")
            elif os.path.isdir(thingPath):
                self.dockerfile.write(f"COPY {thingPath} {imagePath}{thingName}\n")
    
    def PrepForInstallation(self):
        if (self.config["os"] == "debian"):
            self.dockerfile.write("RUN apt update\n")
        elif (self.config["os"] == "alpine"):
            self.dockerfile.write("RUN apk update\n")

    def InstallPackage(self, packageName):
        if (self.config["os"] == "debian"):
            self.dockerfile.write(f"RUN apt install -y --no-install-recommends {packageName}\n")
        elif (self.config["os"] == "alpine"):
            self.dockerfile.write(f"RUN apk add --no-cache {packageName}\n")

    def CleanInstallation(self):
        if (self.config["os"] == "debian"):
            self.dockerfile.write("RUN rm -rf /var/lib/apt/lists/*\n")
        elif (self.config["os"] == "alpine"):
            pass #no cleanup necessary for alpine at this time.

    def WriteDockerfile(self):
        self.dockerfile = open("Dockerfile", "w")

        if ("from" in self.config):
            self.dockerfile.write(f"FROM {self.config['from']}\n")

        if (self.incPath is not None):
            self.CopyToImage(self.incPath, "/usr/local/include/")
        
        if (self.libPath is not None):
            self.CopyToImage(self.libPath, "/usr/local/lib/")

        if (self.srcPath is not None):
            self.CopyToImage(self.srcPath, "/usr/local/bin/")
            self.dockerfile.write("RUN chmod +x /usr/local/bin/*\n")

        if ("install" in self.config):
            self.PrepForInstallation()
            for pkg in self.config["install"]:
                self.InstallPackage(pkg)
            self.CleanInstallation()

        if ("also" in self.config):
            for add in self.config.also:
                self.dockerfile.write(add);

        if ("entrypoint" in self.config):
            self.dockerfile.write(f"ENTRYPOINT [\"{self.config['entrypoint']}\"]\n")
        
        if ("cmd" in self.config):
            self.dockerfile.write(f"CMD [\"{self.config['cmd']}\"]\n")

        self.dockerfile.close()
