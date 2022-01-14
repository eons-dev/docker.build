import os
import logging
from ebbs import Builder


# Class name is what is used at cli, so we defy convention here in favor of ease-of-use.
class docker(Builder):
    def __init__(this, name="Docker"):
        super().__init__(name)

        this.supportedProjectTypes.append("img")
        this.supportedProjectTypes.append("srv")

        this.optionalKWArgs["docker_username"] = None
        this.optionalKWArgs["docker_password"] = None
        this.optionalKWArgs["base_image"] = None
        this.optionalKWArgs["install"] = []
        this.optionalKWArgs["image_os"] = None
        this.optionalKWArgs["entrypoint"] = None
        this.optionalKWArgs["cmd"] = None
        this.optionalKWArgs["also"] = []

        #We use the rootPath, not the buildPath.
        this.clearBuildPath = False

        this.supportedImageOperatingSystems = [
            "debian",
            "alpine"
        ]
        
        
    # Required Builder method. See that class for details.
    def Build(this):
        os.chdir(this.rootPath) # docker must be built from root.
        
        this.shouldLogin = False
        if (this.docker_username is not None and this.docker_password is not None):
            this.shouldLogin = True

        if (this.name == "Docker"):
            if (this.docker_username is not None):
                this.name = f"{this.docker_username}/{this.projectName}"
            else:
                this.name = this.projectName
        
        if (len(this.install) and this.image_os is None):
            raise OtherBuildError(f'You must specify the "os" if you wish to install packages')

        if (this.image_os is not None and this.image_os not in this.supportedImageOperatingSystems):
            raise OtherBuildError(f'"os" {this.image_os} is not supported at this time. Please use one of {this.supportedImageOperatingSystems}')

        if (this.shouldLogin):
            this.LoginToDockerhub()

        this.WriteDockerfile()
        this.BuildDockerImage()
        
        if (this.shouldLogin):
            this.PushDockerImage()


    def LoginToDockerhub(this):
        this.RunCommand(f"docker login -u=\"{this.docker_username}\" -p=\"{this.docker_password}\"")

    def BuildDockerImage(this):
        this.RunCommand(f"docker build -t {this.name} .")

    def PushDockerImage(this):
        this.RunCommand(f"docker push {this.name}")

    def CopyToImage(this, externalPath, imagePath):
        #This nonsense is required because we need `cp incPath/* buildpath/` behavior instead of `cp incPath buildpath/`
        #TODO: is there a better way?
        for thing in os.listdir(externalPath):
            thingPath = os.path.relpath(os.path.join(externalPath, thing))
            thingName = os.path.basename(thing)
            if os.path.isfile(thingPath):
                this.dockerfile.write(f"COPY {thingPath} {imagePath}\n")
            elif os.path.isdir(thingPath):
                this.dockerfile.write(f"COPY {thingPath} {imagePath}{thingName}\n")
    
    def PrepForInstallation(this):
        if (this.image_os == "debian"):
            this.dockerfile.write("RUN apt update\n")
        elif (this.image_os == "alpine"):
            this.dockerfile.write("RUN apk update\n")

    def InstallPackage(this, packageName):
        if (this.image_os == "debian"):
            this.dockerfile.write(f"RUN apt install -y --no-install-recommends {packageName}\n")
        elif (this.image_os == "alpine"):
            this.dockerfile.write(f"RUN apk add --no-cache {packageName}\n")

    def CleanInstallation(this):
        if (this.image_os == "debian"):
            this.dockerfile.write("RUN rm -rf /var/lib/apt/lists/*\n")
        elif (this.image_os == "alpine"):
            pass #no cleanup necessary for alpine at this time.

    def WriteDockerfile(this):
        this.dockerfile = open("Dockerfile", "w")

        if (this.base_image is not None):
            this.dockerfile.write(f"FROM {this.base_image}\n")

        if (this.incPath is not None):
            this.CopyToImage(this.incPath, "/usr/local/include/")
        
        if (this.libPath is not None):
            this.CopyToImage(this.libPath, "/usr/local/lib/")

        if (this.srcPath is not None):
            this.CopyToImage(this.srcPath, "/usr/local/bin/")
            this.dockerfile.write("RUN chmod +x /usr/local/bin/*\n")

        if (len(this.install)):
            this.PrepForInstallation()
            for pkg in this.install:
                this.InstallPackage(pkg)
            this.CleanInstallation()

        if (len(this.also)):
            for add in this.also:
                this.dockerfile.write(add);

        if (this.entrypoint is not None):
            this.dockerfile.write(f"ENTRYPOINT [\"{this.entrypoint}\"]\n")
        
        if (this.cmd is not None):
            this.dockerfile.write(f"CMD [\"{this.cmd}\"]\n")

        this.dockerfile.close()
