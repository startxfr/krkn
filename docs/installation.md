## Installation

The following ways are supported to run Kraken:

- Standalone python program through Git.
- Containerized version using either Podman or Docker as the runtime.
- Kubernetes or OpenShift deployment.

**NOTE**: It is recommended to run Kraken external to the cluster ( Standalone or Containerized ) hitting the Kubernetes/OpenShift API as running it internal to the cluster might be disruptive to itself and also might not report back the results if the chaos leads to cluster's API server instability.

**NOTE**: To run Kraken on Power (ppc64le) architecture, build and run a containerized version by following the
 instructions given [here](https://github.com/redhat-chaos/krkn/blob/main/containers/build_own_image-README.md).

### Git

#### Clone the repository
Pick the latest stable release to install [here](https://github.com/redhat-chaos/krkn/releases).
```
$ git clone https://github.com/redhat-chaos/krkn.git --branch <release version>
$ cd kraken
```

#### Install the dependencies
```
$ python3.9 -m venv chaos
$ source chaos/bin/activate
$ pip3.9 install -r requirements.txt
```

**NOTE**: Make sure python3-devel and latest pip versions are installed on the system. The dependencies install has been tested with pip >= 21.1.3 versions.

#### Run
```
$ python3.9 run_kraken.py --config <config_file_location>
```

### Run containerized version
Assuming that the latest docker ( 17.05 or greater with multi-build support ) is installed on the host, run:
```
$ docker pull quay.io/chaos-kubox/krkn:latest
$ docker run --name=kraken --net=host -v <path_to_kubeconfig>:/root/.kube/config:Z -v <path_to_kraken_config>:/root/kraken/config/config.yaml:Z -d quay.io/chaos-kubox/krkn:latest
$ docker run --name=kraken --net=host -v <path_to_kubeconfig>:/root/.kube/config:Z -v <path_to_kraken_config>:/root/kraken/config/config.yaml:Z -v <path_to_scenarios_directory>:/root/kraken/scenarios:Z -d quay.io/chaos-kubox/krkn:latest #custom or tweaked scenario configs
$ docker logs -f kraken
```

Similarly, podman can be used to achieve the same:
```
$ podman pull quay.io/chaos-kubox/krkn
$ podman run --name=kraken --net=host -v <path_to_kubeconfig>:/root/.kube/config:Z -v <path_to_kraken_config>:/root/kraken/config/config.yaml:Z -d quay.io/chaos-kubox/krkn:latest
$ podman run --name=kraken --net=host -v <path_to_kubeconfig>:/root/.kube/config:Z -v <path_to_kraken_config>:/root/kraken/config/config.yaml:Z -v <path_to_scenarios_directory>:/root/kraken/scenarios:Z -d quay.io/chaos-kubox/krkn:latest #custom or tweaked scenario configs
$ podman logs -f kraken
```

If you want to build your own kraken image see [here](https://github.com/redhat-chaos/krkn/blob/main/containers/build_own_image-README.md)


### Run Kraken as a Kubernetes deployment
Refer [Instructions](https://github.com/redhat-chaos/krkn/blob/main/containers/README.md) on how to deploy and run Kraken as a Kubernetes/OpenShift deployment.
