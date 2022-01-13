import os
import logging
from ebbs import Builder


# Class name is what is used at cli, so we defy convention here in favor of ease-of-use.
class docker(Builder):
    def __init__(self, name="Docker"):
        super().__init__(name)

        self.supportedProjectTypes.append("img")
        self.supportedProjectTypes.append("srv")

        self.optionalKWArgs["docker_username"] = None
        self.optionalKWArgs["docker_password"] = None
        self.optionalKWArgs["base_image"] = None
        self.optionalKWArgs["install"] = []
        self.optionalKWArgs["image_os"] = None
        self.optionalKWArgs["image_name"] = None
        self.optionalKWArgs["env"] = [
            "TZ=\"America/Los_Angeles\""
        ]
        self.optionalKWArgs["entrypoint"] = None
        self.optionalKWArgs["cmd"] = None
        self.optionalKWArgs["also"] = []

        # We use the rootPath, not the buildPath.
        self.clearBuildPath = False

        self.supportedImageOperatingSystems = [
            "debian",
            "alpine"
        ]

    # Required Builder method. See that class for details.
    def Build(self):
        os.chdir(self.rootPath)  # docker must be built from root.

        self.shouldLogin = False
        if (self.docker_username is not None and self.docker_password is not None):
            self.shouldLogin = True

        if (self.image_name is None):
            if (self.docker_username is not None):
                self.image_name = f"{self.docker_username}/{self.projectName}"
            else:
                self.image_name = self.projectName

        if (len(self.install) and self.image_os is None):
            raise OtherBuildError(f'You must specify the "os" if you wish to install packages')

        if (self.image_os is not None and self.image_os not in self.supportedImageOperatingSystems):
            raise OtherBuildError(
                f'"os" {self.image_os} is not supported at this time. Please use one of {self.supportedImageOperatingSystems}')

        if (self.shouldLogin):
            self.LoginToDockerhub()

        self.WriteDockerfile()
        self.BuildDockerImage()

        if (self.shouldLogin):
            self.PushDockerImage()

    def LoginToDockerhub(self):
        self.RunCommand(f"docker login -u=\"{self.docker_username}\" -p=\"{self.docker_password}\"")

    def BuildDockerImage(self):
        self.RunCommand(f"docker build -t {self.image_name} .")

    def PushDockerImage(self):
        self.RunCommand(f"docker push {self.image_name}")

    def CopyToImage(self, externalPath, imagePath):
        # This nonsense is required because we need `cp incPath/* buildpath/` behavior instead of `cp incPath buildpath/`
        # TODO: is there a better way?
        for thing in os.listdir(externalPath):
            thingPath = os.path.relpath(os.path.join(externalPath, thing))
            thingName = os.path.basename(thing)
            if os.path.isfile(thingPath):
                self.dockerfile.write(f"COPY {thingPath} {imagePath}\n")
            elif os.path.isdir(thingPath):
                self.dockerfile.write(f"COPY {thingPath} {imagePath}{thingName}\n")

    def PrepForInstallation(self):
        if (self.image_os == "debian"):
            self.dockerfile.write("ENV DEBIAN_FRONTEND=\"noninteractive\"\n")
            self.dockerfile.write("RUN apt update\n")
        elif (self.image_os == "alpine"):
            self.dockerfile.write("RUN apk update\n")

    def InstallPackage(self, packageName):
        if (self.image_os == "debian"):
            self.dockerfile.write(f"RUN apt install -y --no-install-recommends {packageName}\n")
        elif (self.image_os == "alpine"):
            self.dockerfile.write(f"RUN apk add --no-cache {packageName}\n")

    def CleanInstallation(self):
        if (self.image_os == "debian"):
            self.dockerfile.write("RUN rm -rf /var/lib/apt/lists/*\n")
        elif (self.image_os == "alpine"):
            pass  # no cleanup necessary for alpine at this time.

    def WriteDockerfile(self):
        self.dockerfile = open("Dockerfile", "w")

        if (self.base_image is not None):
            self.dockerfile.write(f"FROM {self.base_image}\n")

        if (self.incPath is not None):
            self.CopyToImage(self.incPath, "/usr/local/include/")

        if (self.libPath is not None):
            self.CopyToImage(self.libPath, "/usr/local/lib/")

        if (self.srcPath is not None):
            self.CopyToImage(self.srcPath, "/usr/local/bin/")
            self.dockerfile.write("RUN chmod +x /usr/local/bin/*\n")

        for env in self.env:
            self.dockerfile.write(f"ENV {env}\n")

        if (len(self.install)):
            self.PrepForInstallation()
            for pkg in self.install:
                self.InstallPackage(pkg)
            self.CleanInstallation()

        for add in self.also:
            self.dockerfile.write(f"{add}\n");

        if (self.entrypoint is not None):
            self.dockerfile.write(f"ENTRYPOINT [\"{self.entrypoint}\"]\n")

        if (self.cmd is not None):
            self.dockerfile.write(f"CMD [\"{self.cmd}\"]\n")

        self.dockerfile.close()
