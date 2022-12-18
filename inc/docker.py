import os
import logging
from ebbs import Builder, OtherBuildError
from eot import EOT

# Class name is what is used at cli, so we defy convention here in favor of ease-of-use.
class docker(Builder):
    def __init__(this, name="Docker"):
        super().__init__(name)

        this.supportedProjectTypes.append("img")
        this.supportedProjectTypes.append("srv")

        this.optionalKWArgs["docker_username"] = None
        this.optionalKWArgs["docker_password"] = None
        this.optionalKWArgs["base_image"] = "scratch"
        this.optionalKWArgs["combine"] = []
        this.optionalKWArgs["emi"] = None
        this.optionalKWArgs["install"] = []
        this.optionalKWArgs["image_os"] = None
        this.optionalKWArgs["image_name"] = None
        this.optionalKWArgs["env"] = [
            "TZ=\"America/Los_Angeles\""
        ]
        this.optionalKWArgs["entrypoint"] = None
        this.optionalKWArgs["cmd"] = None
        this.optionalKWArgs["launch"] = {}
        this.optionalKWArgs["also"] = []
        this.optionalKWArgs["tags"] = []
        this.optionalKWArgs["filesystems"] = []
        this.optionalKWArgs["networks"] = []


        # We use the rootPath, not the buildPath.
        this.clearBuildPath = False

        this.supportedImageOperatingSystems = [
            "debian",
            "alpine"
        ]

    def DidBuildSucceed(this):
        return True #TODO: Make sure that image was created.

    # Required Builder method. See that class for details.
    def Build(this):
        os.chdir(this.rootPath)  # docker must be built from root.

        this.shouldLogin = False
        if (this.docker_username is not None and this.docker_password is not None and len(this.docker_username) and len(this.docker_password)):
            this.shouldLogin = True

        if (this.image_name is None):
            if (this.docker_username is not None):
                this.image_name = f"{this.docker_username}/{this.projectName}"
            else:
                this.image_name = this.projectName

        if (len(this.install) and this.image_os is None):
            raise OtherBuildError(f'You must specify the "os" if you wish to install packages')

        if (this.image_os is not None and this.image_os not in this.supportedImageOperatingSystems):
            raise OtherBuildError(
                f'"os" {this.image_os} is not supported at this time. Please use one of {this.supportedImageOperatingSystems}')

        if (this.shouldLogin):
            this.LoginToDockerhub()

        this.WriteDockerfile()
        this.BuildDockerImage()

    def LoginToDockerhub(this):
        this.RunCommand(f"docker login -u=\"{this.docker_username}\" -p=\"{this.docker_password}\"")

    def BuildDockerImage(this):
        imageTags = f"-t {this.image_name}:{EOT.GetStardate()}"
        for tag in this.tags:
            imageTags += f" -t {this.image_name}:{tag}"
        this.RunCommand(f"docker build {imageTags} .")

    def CopyToImage(this, externalPath, imagePath):
        # This nonsense is required because we need `cp incPath/* buildpath/` behavior instead of `cp incPath buildpath/`
        # TODO: is there a better way?
        for thing in os.listdir(externalPath):
            thingPath = os.path.relpath(os.path.join(externalPath, thing))
            thingName = os.path.basename(thing)
            if os.path.isfile(thingPath):
                this.dockerfile.write(f"COPY {thingPath} {imagePath}\n")
            elif os.path.isdir(thingPath):
                this.dockerfile.write(f"COPY {thingPath} {imagePath}{thingName}\n")

    def PrepForInstallation(this):
        if (this.image_os == "debian"):
            this.dockerfile.write("ENV DEBIAN_FRONTEND=\"noninteractive\"\n")
            this.dockerfile.write("RUN apt update\n")
        elif (this.image_os == "alpine"):
            this.dockerfile.write("RUN apk update\n")

    def InstallPackage(this, packageName):
        if (this.image_os == "debian"):
            this.dockerfile.write(f"RUN apt install -y --no-install-recommends {packageName}\n")
        elif (this.image_os == "alpine"):
            this.dockerfile.write(f"RUN apk add {packageName}\n")

    def CleanInstallation(this):
        if (this.image_os == "debian"):
            this.dockerfile.write("RUN rm -rf /var/lib/apt/lists/*\n")
        elif (this.image_os == "alpine"):
            this.dockerfile.write("RUN rm -rf /var/cache/apk/*\n")

    def CreateNetwork(this, network, order=0):
        if (order):
            order = f"{order}_"

        this.dockerfile.write(f"RUN echo \"tinc -n {network} start\" > \"/launch.d/{order}network_{network}\"\n")

    def CreateFilesystem(this, filesystem, mount, options={}, order=0):
        if (order):
            order = f"{order}_"

        launchFileName = f"{order}filesystem_{filesystem}"

        launchFile = this.CreateFile(launchFileName)

        defaultOptions = {}
        defaultOptions['buffer-size'] = "64M"
        defaultOptions['config'] = "/root/.config/rclone/rclone.conf"
        defaultOptions['dir-cache-time'] = "168h"
        defaultOptions['drive-chunk-size'] = "64M"
        defaultOptions['fast-list'] = True
        defaultOptions['syslog'] = True
        defaultOptions['allow-other'] = False
        defaultOptions['vfs-read-chunk-size-limit'] = "1024M"
        defaultOptions['vfs-read-chunk-size'] = "64M"

        for opt, val in defaultOptions.items():
            if (opt in options.keys()):
                del defaultOptions[opt]

        options = options | defaultOptions

        launchFile.write("rclone mount ")
        for opt, val in options.items():
            if (isinstance(val, bool)):
                if (val):
                    launchFile.write(f"--{opt} ")
            else:
                launchFile.write(f"--{opt}={val} ")
        launchFile.write(f"{filesystem} {mount}")
        launchFile.close
        
        this.dockerfile.write(f"COPY {launchFileName} /launch.d/{launchFileName}\n")

    def WriteDockerfile(this):
        this.dockerfile = this.CreateFile("Dockerfile")


        #### SETUP BASE ####

        for i, img in enumerate(this.combine):
            this.dockerfile.write(f"FROM {img} as combo{i}\n")

        this.dockerfile.write(f"FROM {this.base_image} as build\n")

        for i, img in enumerate(this.combine):
            this.dockerfile.write(f"COPY --from=combo{i} / /\n")


        #### IMPLICIT CONFIG ####

        if (this.incPath is not None):
            this.CopyToImage(this.incPath, "/usr/local/include/")

        if (this.libPath is not None):
            this.CopyToImage(this.libPath, "/usr/local/lib/")

        if (this.binPath is not None):
            this.CopyToImage(this.binPath, "/usr/local/bin/")
            this.dockerfile.write("RUN chmod +x /usr/local/bin/*\n")

        for env in this.env:
            this.dockerfile.write(f"ENV {env}\n")


        #### EXPLICIT CONFIG ####

        if (len(this.install)):
            this.PrepForInstallation()
            for pkg in this.install:
                this.InstallPackage(pkg)
            this.CleanInstallation()

        if this.emi is not None:
            # logging.warning(f"ASSUMING: EMI is installed. If not, please install python3, python3-pip, and run 'pip install emi' (other packages may be required depending on your os)")

            for merx, tomes in this.emi.items():
                this.dockerfile.write(f"RUN emi -v {merx} {' '.join(tomes)}\n")

            this.dockerfile.write(f"RUN rm -rf ~/.eons/tmp; rm -rf ~/.eons/merx\n")

        for net in this.networks:
            order = 0
            if ('order' in net):
                order = int(net['order'])
            
            this.CreateNetwork(net['name'], order)

        for fs in this.filesystems:
            order = 0
            if ('order' in fs):
                order = int(net['order'])

            options = {}
            if ('options' in fs):
                options = fs['options']

            this.CreateFilesystem(fs['name'], fs['mount'], options, order)

        
        #### LAUNCH ####

        for key, value in this.launch.items():
            this.dockerfile.write(f"RUN echo \"{value}\" > \"/launch.d/{key}\"\n")

        
        #### EXTRA ####

        for add in this.also:
            this.dockerfile.write(f"{add}\n");


        #### FINALIZE IMAGE ####

        this.dockerfile.write(f'''
FROM scratch
COPY --from=build / /
''')

        if (this.entrypoint is not None):
            this.dockerfile.write(f"ENTRYPOINT [\"{this.entrypoint}\"]\n")

        if (this.cmd is not None):
            this.dockerfile.write(f"CMD [\"{this.cmd}\"]\n")

        this.dockerfile.close()
