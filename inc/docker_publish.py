import os
import logging
from ebbs import Builder
from eot import EOT

# Class name is what is used at cli, so we defy convention here in favor of ease-of-use.
class docker(Builder):
    def __init__(this, name="Docker"):
        super().__init__(name)

        this.clearBuildPath = False
        this.supportedProjectTypes = []
        
        this.requiredKWArgs.append("image_name")
        this.requiredKWArgs.append("docker_username")
        this.requiredKWArgs.append("docker_password")

    # Required Builder method. See that class for details.
    def Build(this):
        this.RunCommand(f"docker login -u=\"{this.docker_username}\" -p=\"{this.docker_password}\"")
        this.RunCommand(f"docker push -a {this.image_name}")

    def DidBuildSucceed(this):
        return True #TODO: check that image is available.