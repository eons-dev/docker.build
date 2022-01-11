# EBBS Docker Builder

This script is meant to be used by [ebbs](https://github.com/eons-dev/bin_ebbs)

This script will automatically generate a Dockerfile, build a docker image, and, if you specify credentials, push that image to dockerhub.
You can specify:
```json
"docker_username"
"docker_password"
"base_image"
"install"
"image_os"
"entrypoint"
"cmd"
"also"
```

For example, this is the config.json for the eons web server base image.
```json
{
    "name": "eons/img_webserver",
    "base_image": "ubuntu:latest",
    "image_os": "debian",
    "install": [
        "gcc",
        "openssl"
    ]
}
```

This is only mildly less work than writing an actual Dockerfile. However, where this comes in especially handy, is with nested build steps.
Here's how the infrastructure.tech web server builds a C++ executable and adds it on top of the eons web server.

```json
{
  "name" : "entrypoint",
  "cpp_version" : 17,
  "libs_shared": [
    "restbed",
    "cpr"
  ],
  "ebbs_next": [
    {
      "language": "docker",
      "type" : "srv",
      "name" : "infrastructure",
      "buildPath" : "tmp",
      "copy" : [
        {"out/" : "src/"}
      ],
      "config" : {
        "name" : "eons/srv_infrastructure",
        "base_image" : "eons/img_webserver",
        "image_os" : "debian",
        "entrypoint" : "/usr/local/bin/entrypoint",
        "also" : [
          "EXPOSE 80"
        ]
      }
    }
  ]
}
```
Using this single config file, we can perform a cmake build process and a Dockerfile containerization & publication all in one go.
Of course, if you'd like to publish your image, you must specify `docker_username` and `docker_password` in the environment variables (unless you want to put them in the json but please don't do that) (you can't set them via the cli when using multi-step builds at this time).