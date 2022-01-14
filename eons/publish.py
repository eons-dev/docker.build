import os
import logging
import shutil
import requests
import jsonpickle
import base64
from ebbs import Builder
from ebbs import OtherBuildError

class publish(Builder):
    def __init__(this, name="Publisher"):
        super().__init__(name)

        #Build path is what we use to publish. We definitely don't want to clear it.
        this.clearBuildPath = False

        this.requiredKWArgs.append("version")
        
        this.optionalKWArgs["visibility"] = "private"
        this.optionalKWArgs["package_type"] = ""
        this.optionalKWArgs["description"] = ""

        this.supportedProjectTypes = [] #all

    def PreBuild(this, **kwargs):
        if (not this.executor.args.repo_username or not this.executor.args.repo_password):
            raise OtherBuildError(f'Repo credentials required to publish package')

        nameComponents = [this.projectType, this.projectName]
        if (this.package_type):
            nameComponents.append(this.package_type)

        this.packageName = '_'.join(nameComponents)

        this.targetFileName = f'{this.packageName}.zip'
        this.targetFile = os.path.join(this.executor.args.repo_store, this.targetFileName)

        this.requestData = {
            'package_name': this.packageName,
            'version': this.version,
            'visibility': this.visibility
        }
        if (this.package_type):
            this.requestData['package_type'] = this.package_type
        if (this.description):
            this.requestData['description'] = this.description

    # Required Builder method. See that class for details.
    def Build(this):
        os.chdir(this.rootPath)
        logging.debug(f"Creating archive {this.targetFile}")
        if (os.path.exists(this.targetFile)):
            os.remove(this.targetFile)

        shutil.make_archive(this.targetFile[:-4], 'zip', this.buildPath)
        logging.debug("Archive created")

        logging.debug("Uploading archive to repository")
        #NOTE: jsonpickle can b64 encode binary data but we want to do it first to avoid an extraneous {"py/b64":...} object being added to the request body.
        this.requestData['package'] = str(base64.b64encode(open(this.targetFile, 'rb').read()).decode('ascii'))
        requestData = jsonpickle.encode(this.requestData)
        logging.debug(f'Request data: {requestData}')
        packageQuery = requests.post(f"{this.executor.args.repo_url}/publish", auth=requests.auth.HTTPBasicAuth(this.executor.args.repo_username, this.executor.args.repo_password), data=requestData)

        logging.debug(f'''Request sent...
----------------------------------------        
Response: {packageQuery.status_code}
URL: {packageQuery.request.url}
Headers: {packageQuery.request.headers}
Content: {packageQuery.content}
----------------------------------------
''')

        if (packageQuery.status_code != 200):
            logging.error(f'Failed to publish {this.projectName}')
            raise OtherBuildError(f'Failed to publish {this.projectName}')

        logging.info(f'Successfully published {this.projectName}')