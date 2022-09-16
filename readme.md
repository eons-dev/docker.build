# EBBS Docker Builder

This script is meant to be used by [ebbs](https://github.com/eons-dev/bin_ebbs)

Use `docker` to automatically generate a Dockerfile, build a docker image.  
Use `docker_publish` to push that image to Dockerhub.

## Optimization and Layers

Dockerfile optimization has some tricks to it but those are unnecessary when using this script (e.g. you can have as many `RUN` directives as you want; no need to combine them). We attempt to optimize as best we can using the information we are given and will always prefer functionality to maintainability to optimization. Thus, we recommend using as many directives (and creating as many layers) as is necessary for your code to work.

The `docker` script will automatically flatten your layers as the last build step. This removes the history but also removes all the overhead created by extra layers.

## Combining Multiple Images

Some people say you can't combine the contents of multiple docker images. That is a lie.

To combine the full contents of any number of images, simply add the name (and tag) to the `combine` list in the configuration (see below).

## Config

* `docker_username`: username for dockerhub (i.e. hub.docker.com).
* `docker_password`: password for dockerhub.
* `base_image`: image to use for the [FROM directive](https://docs.docker.com/engine/reference/builder/#format).
* `combine`: images you want to combine (e.g. `["me/onecoolimage:latest", "someoneelese/anothercoolimage:latest"]`).
* `emi`: run the [Eons Modular Installer](https://github.com/eons-dev/bin_emi); takes a dictionary of lists where the format is `{"merx": ["tomes"]}`; See the [emi docs](https://github.com/eons-dev/bin_emi) for more info; requires emi be installed in the `base_image` (true if you use `eons/img_base` or a child thereof).
* `install`: list of packages to install (names only).
* `image_os`: base operating system the `base_image` derives from (e.g. debian); this controls how packages are installed.
* `entrypoint`: an [entrypoint](https://docs.docker.com/engine/reference/builder/#entrypoint) script; DO NOT USE THIS if you are using `launch`.
* `cmd`: a [command](https://docs.docker.com/engine/reference/builder/#cmd); DO NOT USE THIS if you are using `launch`.
* `launch`: an array of launch scripts; these are identical to `entrypoint`, except that there can be more than 1.
* `also`: any other dockerfile directives you'd like (you can create an entire dockerfile just in `also`).
* `tags`: list of [tags](https://docs.docker.com/engine/reference/commandline/tag/) to add to the built image.


For example, this is the docker config portion of the build json for the eons webserver image.
```json
"config":
{
    "base_image": "eons/img_base",
    "image_name": "eons/img_webserver",
    "image_os": "debian",
    "install":
    [
        "gcc",
        "openssl"
    ],
    "emi":
    {
      "install":
      [
        "all",
        "my",
        "tomes"
      ]
    },
    "tags" : [
        "latest"
    ]
}
```

This is only mildly less work than writing an actual Dockerfile. However, where this comes in especially handy, is with nested build steps.
Here's how the infrastructure.tech web server builds a C++ executable in a containerized environment then adds that executable to a docker image.

```json
{
  "name" : "infrastructure",
  "type" : "srv",
  "clear_build_path" : true,
  "build_in" : "github",
  "next": [
    {
      "build" : "in_container",
      "config" : {
        "image" : "eons/img_dev-webserver",
        "copy_env" : [
          "docker_username",
          "docker_password"
        ],
        "next" : [
          {
            "clear_build_path" : false,
            "build" : "cpp",
            "build_in" : "build",
            "copy" : [
              {"../../../inc/" : "inc/"},
              {"../../../src/" : "src/"}
            ],
            "config" : {
              "file_name" : "api_v1",
              "cpp_version" : 17,
              "libs_shared": [
                "restbed",
                "cpr"
              ],
              "next" : [
                {
                  "build": "docker",
                  "run_when_any" : [
                    "release"
                  ],
                  "path" : "srv_infrastructure",
                  "copy" : [
                    {"out/" : "src/"}
                  ],
                  "config" : {
                    "base_image" : "eons/img_webserver",
                    "image_name" : "eons/srv_infrastructure",
                    "image_os" : "debian",
                    "launch" : {
                      "api_v1" : "/usr/local/bin/api_v1"
                    },
                    "also" : [
                      "EXPOSE 80"
                    ],
                    "tags" : [
                      "latest"
                    ]
                  }
                }
              ]
            }
          }
        ]
      }
    }
  ]
}
```
Using this single config file, we can perform a cmake build process and a Dockerfile containerization & publication all in one go.
Of course, if you'd like to publish your image, you must specify `docker_username` and `docker_password` in the environment variables (unless you want to put them in the json but please don't do that).

### Latest Tag

Please include the "latest" tag in your config. We don't add this automatically because it is not always desired. The only tag we automatically add is the current [stardate](https://github.com/eons-dev/bin_eot).

Here's the code to add:
```json
"tags" : [
    "latest"
]
```

### Use With img_guest

If your image derives from infrastructure-tech/img_guest (or compatible), there are the following additional configuration values available to you:

* `networks`: a list of networks to connect to
* `filesystems`: a list of filesystems to mount.


