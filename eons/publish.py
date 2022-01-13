import os
import logging
import shutil
import requests
import jsonpickle
import base64
from ebbs import Builder
from ebbs import OtherBuildError

class publish(Builder):
    def __init__(self, name="Publisher"):
        super().__init__(name)

        #Build path is what we use to publish. We definitely don't want to clear it.
        self.clearBuildPath = False

        self.requiredKWArgs.append("version")
        
        self.optionalKWArgs["visibility"] = "private"
        self.optionalKWArgs["package_type"] = ""
        self.optionalKWArgs["description"] = ""

        self.supportedProjectTypes = [] #all

    def PreBuild(self, **kwargs):
        if (not self.executor.args.repo_username or not self.executor.args.repo_password):
            raise OtherBuildError(f'Repo credentials required to publish package')

        nameComponents = [self.projectType, self.projectName]
        if (self.package_type):
            nameComponents.append(self.package_type)

        self.packageName = '_'.join(nameComponents)

        self.targetFileName = f'{self.packageName}.zip'
        self.targetFile = os.path.join(self.executor.args.repo_store, self.targetFileName)

        self.requestData = {
            'package_name': self.packageName,
            'version': self.version,
            'visibility': self.visibility
        }
        if (self.package_type):
            self.requestData['package_type'] = self.package_type
        if (self.description):
            self.requestData['description'] = self.description

    # Required Builder method. See that class for details.
    def Build(self):
        os.chdir(self.rootPath)
        logging.debug(f"Creating archive {self.targetFile}")
        if (os.path.exists(self.targetFile)):
            os.remove(self.targetFile)

        shutil.make_archive(self.targetFile[:-4], 'zip', self.buildPath)
        logging.debug("Archive created")

        logging.debug("Uploading archive to repository")
        #NOTE: jsonpickle can b64 encode binary data but we want to do it first to avoid an extraneous {"py/b64":...} object being added to the request body.
        self.requestData['package'] = str(base64.b64encode(open(self.targetFile, 'rb').read()).decode('ascii'))
        requestData = jsonpickle.encode(self.requestData)
        logging.debug(f'Request data: {requestData}')
        packageQuery = requests.post(f"{self.executor.args.repo_url}/publish", auth=requests.auth.HTTPBasicAuth(self.executor.args.repo_username, self.executor.args.repo_password), data=requestData)

        logging.debug(f'''Request sent...
----------------------------------------        
Response: {packageQuery.status_code}
URL: {packageQuery.request.url}
Headers: {packageQuery.request.headers}
Content: {packageQuery.content}
----------------------------------------
''')

        if (packageQuery.status_code != 200):
            logging.error(f'Failed to publish {self.projectName}')
            raise OtherBuildError(f'Failed to publish {self.projectName}')

        logging.info(f'Successfully published {self.projectName}')